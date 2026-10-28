# -*- coding: utf-8 -*-
"""
Voz de J.A.R.V.I.S.
- Jorge (Microsoft, edge-tts): gratis e ilimitada, la voz por defecto.
- ElevenLabs (opcional): voces británicas tipo mayordomo con la cuenta gratis; si se acaban los créditos, vuelve a Jorge.
- Sin internet: la voz de Windows más parecida.
Las frases cortas que repite mucho ("Enseguida, señor.") se guardan para decirlas al instante.
"""
import os, re, time, glob, queue, shutil, asyncio, hashlib, tempfile, threading
import numpy as np
import requests
from config import log, DATOS

CACHE = os.path.join(DATOS, "cache_voz")
CACHE_MAX_CARACTERES = 140
CACHE_MAX_ARCHIVOS = 600
ELEVEN = "https://api.elevenlabs.io/v1"

_EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿️]")


def dividir(texto, minimo=45):
    """Parte la respuesta en frases para empezar a hablar antes (las muy cortas se juntan)."""
    partes = [p.strip() for p in re.split(r"(?<=[.!?…;:])\s+", texto) if p.strip()]
    frases, actual = [], ""
    for p in partes:
        actual = (actual + " " + p).strip()
        if len(actual) >= minimo:
            frases.append(actual)
            actual = ""
    if actual:
        if frases and len(actual) < 18:
            frases[-1] += " " + actual
        else:
            frases.append(actual)
    return frases or [texto]


def limpiar(texto):
    t = _EMOJI.sub("", str(texto))
    t = re.sub(r"[*_#`>|]", "", t)
    t = re.sub(r"https?://\S+", "el enlace", t)
    return " ".join(t.split())


class Voz:
    def __init__(self, cfg, oido=None, al_nivel=None):
        self.cfg = cfg
        self.eleven_pausa = 0.0          # hasta cuándo no se usa ElevenLabs (créditos agotados o clave rechazada)
        self.al_cambiar_voz = None       # aviso cuando ElevenLabs se agota y vuelve Jorge
        self.oido = oido
        self.al_nivel = al_nivel or (lambda n: None)
        self.lock = threading.Lock()
        self.callar = threading.Event()
        self.hablando = False
        import pygame
        self.pg = pygame
        self.abrir_salida(cfg.get("parlantes", ""))

    def abrir_salida(self, nombre=""):
        """Abre los parlantes elegidos (o los predeterminados de Windows si no están conectados)."""
        pg = self.pg
        with self.lock:
            if pg.mixer.get_init():
                pg.mixer.quit()
            try:
                if nombre:
                    pg.mixer.init(24000, -16, 1, 1024, devicename=nombre)
                    log.info("Parlantes: %s", nombre)
                    return True
            except Exception as e:
                log.warning("No pude abrir los parlantes '%s' (%s); uso los predeterminados", nombre, e)
            pg.mixer.init(24000, -16, 1, 1024)
            return not nombre

    # ------------------------------------------------------------ API
    def decir(self, texto):
        texto = limpiar(texto)
        if not texto:
            return
        log.info("JARVIS: %s", texto)
        with self.lock:
            self.callar.clear()
            self.hablando = True
            if self.oido:
                self.oido.ignorar.set()
            try:
                self._hablar_por_frases(dividir(texto))
            except Exception as e:
                log.error("Error de voz: %s", e)
            finally:
                self.al_nivel(0.0)
                self.hablando = False
                time.sleep(0.25)  # que no se escuche a sí mismo
                if self.oido:
                    self.oido.vaciar()
                    self.oido.ignorar.clear()

    def _hablar_por_frases(self, frases):
        """Sintetiza la frase siguiente mientras suena la actual: la primera respuesta llega mucho antes."""
        listas = queue.Queue()

        def producir():
            for frase in frases:
                if self.callar.is_set():
                    break
                listas.put((frase, self._sintetizar(frase)))
            listas.put(None)
        threading.Thread(target=producir, daemon=True).start()
        while True:
            elemento = listas.get()
            if elemento is None:
                break
            frase, archivo = elemento
            if self.callar.is_set():
                if archivo:
                    try:
                        os.remove(archivo)
                    except OSError:
                        pass
                continue
            if archivo:
                self._reproducir(archivo)
            else:
                self._voz_windows(frase)

    def sintetizar_bytes(self, texto):
        """Audio MP3 con la voz de JARVIS (lo usa el celular para sonar igual que la PC)."""
        archivo = self._sintetizar(limpiar(texto))
        if not archivo:
            return None
        try:
            with open(archivo, "rb") as f:
                return f.read()
        finally:
            try:
                os.remove(archivo)
            except OSError:
                pass

    def decir_en_paralelo(self, texto):
        h = threading.Thread(target=self.decir, args=(texto,), daemon=True)
        h.start()
        return h

    def detener(self):
        self.callar.set()
        try:
            self.pg.mixer.stop(); self.pg.mixer.music.stop()
        except Exception:
            pass

    # ------------------------------------------------------------ proveedores
    def usa_elevenlabs(self):
        return (self.cfg.get("voz_proveedor") == "elevenlabs" and bool(self.cfg.get("elevenlabs_api_key"))
                and time.time() >= self.eleven_pausa)

    def _firma(self, texto):
        if self.usa_elevenlabs():
            partes = ("eleven", self.cfg.get("elevenlabs_voz"), self.cfg.get("elevenlabs_modelo"),
                      self.cfg.get("elevenlabs_velocidad", 1.0), texto)
        else:
            partes = ("edge", self.cfg.get("voz"), self.cfg.get("velocidad_voz"), self.cfg.get("tono_voz"), texto)
        return hashlib.sha1("|".join(map(str, partes)).encode("utf-8")).hexdigest()

    def _sintetizar(self, texto):
        """Devuelve un MP3 temporal con la frase (o None si no hay voz neural: se usará la de Windows)."""
        archivo = os.path.join(tempfile.gettempdir(), f"jarvis_{time.time_ns()}.mp3")
        corta = len(texto) <= CACHE_MAX_CARACTERES
        guardado = os.path.join(CACHE, self._firma(texto) + ".mp3") if corta else None
        if guardado and os.path.exists(guardado):
            try:
                shutil.copyfile(guardado, archivo)
                return archivo
            except OSError:
                pass
        hecho = False
        if self.usa_elevenlabs():
            hecho = self._elevenlabs(texto, archivo)
        if not hecho:
            hecho = self._edge(texto, archivo)
        if not hecho:
            return None
        if guardado:
            self._guardar_en_cache(archivo, guardado)
        return archivo

    def _guardar_en_cache(self, archivo, destino):
        try:
            os.makedirs(CACHE, exist_ok=True)
            shutil.copyfile(archivo, destino)
            todos = glob.glob(os.path.join(CACHE, "*.mp3"))
            if len(todos) > CACHE_MAX_ARCHIVOS:
                for viejo in sorted(todos, key=os.path.getmtime)[: len(todos) - CACHE_MAX_ARCHIVOS]:
                    os.remove(viejo)
        except OSError as e:
            log.info("No pude guardar la frase en caché: %s", e)

    def _edge(self, texto, archivo):
        try:
            import edge_tts

            async def _gen():
                com = edge_tts.Communicate(texto, self.cfg.get("voz", "es-MX-JorgeNeural"),
                                           rate=self.cfg.get("velocidad_voz", "+8%"),
                                           pitch=self.cfg.get("tono_voz", "-6Hz"))
                await asyncio.wait_for(com.save(archivo), timeout=20)

            asyncio.run(_gen())
            return os.path.getsize(archivo) > 0
        except Exception as e:
            log.warning("Voz neural no disponible (%s), uso la voz de Windows", e)
        return False

    def _elevenlabs(self, texto, archivo):
        cfg = self.cfg
        cuerpo = {"text": texto, "model_id": cfg.get("elevenlabs_modelo", "eleven_flash_v2_5"), "language_code": "es",
                  "voice_settings": {"stability": 0.55, "similarity_boost": 0.8, "style": 0.0, "use_speaker_boost": True,
                                     "speed": max(0.7, min(1.2, float(cfg.get("elevenlabs_velocidad", 1.0))))}}
        url = f"{ELEVEN}/text-to-speech/{cfg.get('elevenlabs_voz', 'onwK4e9ZLuTAKqWW03F9')}?output_format=mp3_44100_64"
        cabeceras = {"xi-api-key": cfg["elevenlabs_api_key"], "Accept": "audio/mpeg"}
        try:
            for intento in range(3):
                r = requests.post(url, json=cuerpo, headers=cabeceras, timeout=15)
                if r.status_code == 200 and r.content:
                    with open(archivo, "wb") as f:
                        f.write(r.content)
                    return True
                detalle = r.text[:300].lower()
                if r.status_code in (400, 422) and "language" in detalle and "language_code" in cuerpo:
                    cuerpo.pop("language_code")          # modelos que no aceptan elegir idioma
                    continue
                if r.status_code == 429 and "quota" not in detalle and intento < 2:
                    time.sleep(1.0)                      # demasiadas a la vez: reintento
                    continue
                if "quota" in detalle or "credits" in detalle:
                    self._pausar_elevenlabs(6 * 3600, "Se acabaron los créditos gratis de ElevenLabs de este mes; "
                                                      "mientras tanto hablo con la voz de Jorge.")
                elif r.status_code == 401:
                    self._pausar_elevenlabs(24 * 3600, "ElevenLabs rechazó la clave; hablo con la voz de Jorge. "
                                                       "Revísela en el Centro de control.")
                else:
                    log.warning("ElevenLabs respondió %s: %s", r.status_code, detalle)
                return False
        except requests.RequestException as e:
            log.warning("ElevenLabs no responde (%s); uso a Jorge", e)
        return False

    def _pausar_elevenlabs(self, segundos, aviso):
        self.eleven_pausa = time.time() + segundos
        log.warning(aviso)
        if self.al_cambiar_voz:
            try:
                self.al_cambiar_voz(aviso)
            except Exception:
                pass

    def _reproducir(self, archivo):
        pg = self.pg
        try:
            sonido = pg.mixer.Sound(archivo)
            muestras = pg.sndarray.array(sonido).astype(np.float32)
            if muestras.ndim > 1:
                muestras = muestras.mean(axis=1)
            freq = pg.mixer.get_init()[0]
            paso = max(1, int(freq * 0.04))
            n = len(muestras) // paso
            env = np.abs(muestras[: n * paso]).reshape(n, paso).mean(axis=1) if n else np.zeros(1)
            env = env / (env.max() + 1e-6)
            canal = sonido.play()
            t0 = time.time()
            while canal and canal.get_busy():
                if self.callar.is_set():
                    canal.stop(); break
                i = int((time.time() - t0) / 0.04)
                self.al_nivel(float(env[i]) if i < len(env) else 0.0)
                time.sleep(0.02)
        except Exception as e:
            log.info("Reproducción alternativa (%s)", e)
            pg.mixer.music.load(archivo)
            pg.mixer.music.play()
            while pg.mixer.music.get_busy():
                if self.callar.is_set():
                    pg.mixer.music.stop(); break
                self.al_nivel(0.35 + 0.35 * np.random.rand())
                time.sleep(0.05)
            try:
                pg.mixer.music.unload()
            except Exception:
                pass
        finally:
            try:
                time.sleep(0.05)
                os.remove(archivo)
            except Exception:
                pass

    def _voz_windows(self, texto):
        try:
            import pyttsx3
            motor = pyttsx3.init()
            # sin internet: la voz masculina en español más parecida a Jorge (Jorge > Raúl > Pablo > Álvaro > cualquiera)
            voces = motor.getProperty("voices")
            elegida = None
            for preferida in ("jorge", "raul", "pablo", "alvaro", "jorge", "spanish", "español", "es-"):
                elegida = next((v for v in voces if preferida in (v.name + str(v.languages)).lower()), None)
                if elegida:
                    break
            if elegida:
                motor.setProperty("voice", elegida.id)
            motor.setProperty("rate", 185)
            self.al_nivel(0.6)
            motor.say(texto)
            motor.runAndWait()
            motor.stop()
        except Exception as e:
            log.error("Tampoco funcionó la voz de Windows: %s", e)
