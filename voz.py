# -*- coding: utf-8 -*-
"""Voz de J.A.R.V.I.S.: voz neural (edge-tts) con respaldo sin internet (voz de Windows)."""
import os, re, time, asyncio, tempfile, threading
import numpy as np
from config import log

_EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿️]")


def limpiar(texto):
    t = _EMOJI.sub("", str(texto))
    t = re.sub(r"[*_#`>|]", "", t)
    t = re.sub(r"https?://\S+", "el enlace", t)
    return " ".join(t.split())


class Voz:
    def __init__(self, cfg, oido=None, al_nivel=None):
        self.cfg = cfg
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
                archivo = self._sintetizar(texto)
                if archivo:
                    self._reproducir(archivo)
                else:
                    self._voz_windows(texto)
            except Exception as e:
                log.error("Error de voz: %s", e)
            finally:
                self.al_nivel(0.0)
                self.hablando = False
                time.sleep(0.25)  # que no se escuche a sí mismo
                if self.oido:
                    self.oido.vaciar()
                    self.oido.ignorar.clear()

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

    # ------------------------------------------------------------ interno
    def _sintetizar(self, texto):
        try:
            import edge_tts
            archivo = os.path.join(tempfile.gettempdir(), f"jarvis_{time.time_ns()}.mp3")

            async def _gen():
                com = edge_tts.Communicate(texto, self.cfg.get("voz", "es-MX-JorgeNeural"),
                                           rate=self.cfg.get("velocidad_voz", "+8%"),
                                           pitch=self.cfg.get("tono_voz", "-6Hz"))
                await asyncio.wait_for(com.save(archivo), timeout=20)

            asyncio.run(_gen())
            if os.path.getsize(archivo) > 0:
                return archivo
        except Exception as e:
            log.warning("Voz neural no disponible (%s), uso la voz de Windows", e)
        return None

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
            for v in motor.getProperty("voices"):
                if any(k in (v.name + str(v.languages)).lower() for k in ("spanish", "español", "es-", "sabina", "helena", "pablo", "raul")):
                    motor.setProperty("voice", v.id)
                    break
            motor.setProperty("rate", 185)
            self.al_nivel(0.6)
            motor.say(texto)
            motor.runAndWait()
            motor.stop()
        except Exception as e:
            log.error("Tampoco funcionó la voz de Windows: %s", e)
