# -*- coding: utf-8 -*-
"""
Oído de J.A.R.V.I.S.
Un solo flujo de micrófono para todo: detectar voz, reconocerla, medir el nivel
(para que el HUD reaccione) y detectar dobles aplausos.
"""
import time, queue, threading, collections
import numpy as np
from config import log

TASA = 16000
BLOQUE = 480  # 30 ms


class Oido:
    def __init__(self, cfg, al_aplaudir=None, al_nivel=None):
        self.cfg = cfg
        self.al_aplaudir = al_aplaudir or (lambda: None)
        self.al_nivel = al_nivel or (lambda n: None)
        self.cola = queue.Queue(maxsize=2000)
        self.ignorar = threading.Event()   # activo mientras Jarvis habla
        self.piso = 0.006                  # ruido ambiente (se adapta solo)
        self.activo = False
        self.error = None
        # aplausos
        self._rms_prev = 0.0
        self._candidato = None             # (tiempo, pico, frames_vistos, energia)
        self._aplausos = []
        self._enfriar = 0.0
        self._bloques = 0                  # reloj de audio: cada bloque = 30 ms
        self._stream = None
        import speech_recognition as sr
        self.sr = sr
        self.rec = sr.Recognizer()

    # ------------------------------------------------------------ micrófono
    def iniciar(self):
        import sounddevice as sd
        from audio import indice_microfono
        dispositivo = indice_microfono(self.cfg.get("microfono", ""))
        for intento in (dispositivo, None) if dispositivo is not None else (None,):
            try:
                self._stream = sd.InputStream(samplerate=TASA, channels=1, dtype="int16", device=intento,
                                              blocksize=BLOQUE, callback=self._callback)
                self._stream.start()
                self.activo, self.error = True, None
                info = sd.query_devices(intento if intento is not None else sd.default.device[0])
                log.info("Micrófono activo: %s", info["name"])
                return
            except Exception as e:
                self.error = str(e)
                log.error("No pude abrir el micrófono %s: %s", intento, e)
        raise RuntimeError(self.error)

    def reiniciar(self):
        """Cambia de micrófono en caliente (después de elegir otro en los ajustes)."""
        self.detener()
        self.activo = False
        self.iniciar()

    def detener(self):
        try:
            if self._stream:
                self._stream.stop(); self._stream.close()
        except Exception:
            pass

    def vaciar(self):
        try:
            while True:
                self.cola.get_nowait()
        except queue.Empty:
            pass

    def _callback(self, indata, frames, t, status):
        self._bloques += 1
        x = indata[:, 0].astype(np.float32) / 32768.0
        rms = float(np.sqrt(np.mean(x * x)) + 1e-9)
        pico = float(np.max(np.abs(x)))
        try:
            self.al_nivel(min(1.0, rms * 9))
        except Exception:
            pass
        if self.ignorar.is_set():
            self._rms_prev = rms
            return
        try:
            self.cola.put_nowait((indata[:, 0].tobytes(), rms))
        except queue.Full:
            pass
        if self.cfg.get("aplausos", True):
            self._detectar_aplauso(rms, pico)
        self._rms_prev = rms

    # ------------------------------------------------------------ aplausos
    def _detectar_aplauso(self, rms, pico):
        ahora = self._bloques * BLOQUE / TASA
        umbral = float(self.cfg.get("sensibilidad_aplauso", 0.35))
        if self._candidato:
            t0, p0, n, energia = self._candidato
            n += 1; energia += rms
            if n >= 4:  # 120 ms después: un aplauso decae rápido, la voz no
                self._candidato = None
                if energia / n < p0 * 0.22:
                    self._aplausos = [a for a in self._aplausos if ahora - a < 1.0] + [t0]
                    if len(self._aplausos) >= 2:
                        sep = self._aplausos[-1] - self._aplausos[-2]
                        if 0.12 < sep < 0.9 and ahora > self._enfriar:
                            self._aplausos.clear()
                            self._enfriar = ahora + 2.5
                            threading.Thread(target=self.al_aplaudir, daemon=True).start()
            else:
                self._candidato = (t0, p0, n, energia)
            return
        # inicio brusco: pico fuerte saliendo de algo silencioso
        if pico > umbral and self._rms_prev < pico * 0.25:
            self._candidato = (ahora, pico, 0, 0.0)

    # ------------------------------------------------------------ escuchar
    def escuchar(self, espera=None, limite=12.0, abortar=None, al_empezar=None):
        """
        Espera a que hables y devuelve el texto reconocido.
        espera: segundos máximos esperando a que empieces (None = infinito)
        Devuelve "" si no hubo voz / no se entendió, None si se abortó.
        """
        self.vaciar()
        inicio = time.time()
        previo = collections.deque(maxlen=12)  # 360 ms antes de que empieces
        tramos, hablando, voz_seguida, silencio, con_voz = [], False, 0, 0.0, 0
        while True:
            if abortar is not None and abortar.is_set():
                return None
            try:
                datos, rms = self.cola.get(timeout=0.1)
            except queue.Empty:
                if not hablando and espera and time.time() - inicio > espera:
                    return ""
                continue
            umbral = max(self.piso * 3.2, 0.010)
            if not hablando:
                previo.append(datos)
                if rms > umbral:
                    voz_seguida += 1
                else:
                    voz_seguida = 0
                    self.piso = 0.97 * self.piso + 0.03 * min(rms, 0.05)
                if voz_seguida >= 3:
                    hablando = True
                    tramos = list(previo)
                    con_voz = 3
                    if al_empezar:
                        al_empezar()
                elif espera and time.time() - inicio > espera:
                    return ""
            else:
                tramos.append(datos)
                if rms < umbral * 0.8:
                    silencio += 0.03
                else:
                    silencio = 0.0
                    con_voz += 1
                if silencio > 0.75 or len(tramos) * 0.03 > limite:
                    break
        if con_voz < 8:  # menos de ~0.25 s de voz real: ruido
            return ""
        return self.reconocer(b"".join(tramos))

    def reconocer(self, pcm):
        audio = self.sr.AudioData(pcm, TASA, 2)
        try:
            texto = self.rec.recognize_google(audio, language=self.cfg.get("idioma_reconocimiento", "es-PE"))
            return (texto or "").strip()
        except self.sr.UnknownValueError:
            return ""
        except self.sr.RequestError as e:
            log.warning("Reconocimiento sin conexión: %s", e)
            time.sleep(1)
            return ""
        except Exception as e:
            log.error("Error reconociendo voz: %s", e)
            return ""
