# -*- coding: utf-8 -*-
"""
 ╦╔═╗╦═╗╦  ╦╦╔═╗
 ║╠═╣╠╦╝╚╗╔╝║╚═╗   J.A.R.V.I.S. 2.0 — Asistente de voz para Windows
╚╝╩ ╩╩╚═ ╚╝ ╩╚═╝   Cerebro local y gratuito (Ollama) · Voz neural · HUD holográfico

Se activa diciendo "Jarvis ...", aplaudiendo dos veces, con Ctrl+Alt+J o haciendo clic en el reactor.
"""
import os, re, sys, time, random, socket, datetime, threading, webbrowser

from config import (VERSION, ICONO, DATOS, ES_WINDOWS, Almacen, cargar_config, ruta, normalizar, log)
from cerebro import Cerebro
from habilidades import Habilidades, DIAS, MESES, hora_hablada
from rapido import Reflejos
from hud import HUD
from bandeja import iniciar_bandeja, iniciar_atajos

PUERTO_UNICO = 47653
SALUDOS_ESCUCHA = ["¿Sí, {t}?", "A sus órdenes.", "Le escucho, {t}.", "Dígame, {t}.", "¿En qué le ayudo?"]
DESPEDIDAS = {"nada", "nada mas", "eso es todo", "es todo", "gracias", "muchas gracias", "ok gracias", "listo gracias",
              "no gracias", "ya esta", "olvidalo", "nada nada", "ninguna", "no nada"}
CALLAR = {"callate", "silencio", "para", "detente", "basta", "stop", "ya callate", "shh"}
SI = {"si", "claro", "dale", "hazlo", "confirmo", "adelante", "ok", "okay", "afirmativo", "por supuesto", "correcto",
      "envialo", "procede", "de acuerdo", "obvio", "ya"}


def ventana_activa():
    if not ES_WINDOWS:
        return ""
    try:
        import ctypes
        u = ctypes.windll.user32
        h = u.GetForegroundWindow()
        n = u.GetWindowTextLengthW(h)
        buf = ctypes.create_unicode_buffer(n + 1)
        u.GetWindowTextW(h, buf, n + 1)
        return buf.value
    except Exception:
        return ""


def extraer_orden(texto, palabras):
    """Si el texto contiene la palabra de activación devuelve la orden (puede ser ""); si no, None."""
    t = texto.strip()
    for p in sorted(palabras, key=len, reverse=True):
        m = re.search(r"(?<![a-záéíóúñ])" + re.escape(p) + r"(?![a-záéíóúñ])", t, re.I)
        if m:
            despues = t[m.end():].strip(" ,.:;!?¿¡")
            antes = t[:m.start()].strip(" ,.:;!?¿¡")
            if not despues and antes and antes.lower() not in ("hola", "oye", "ey", "hey", "oiga"):
                return antes
            return despues
    return None


class Jarvis:
    def __init__(self):
        self.cfg = cargar_config()
        self.alm_memoria = Almacen("memoria.json", [])
        self.alm_comandos = Almacen("comandos.json", {})
        self.alm_listas = Almacen("listas.json", {"notas": [], "tareas": [], "compras": []})
        self.alm_recordatorios = Almacen("recordatorios.json", [])
        self.activar_evt = threading.Event()
        self.silencio = False
        self.ejecutando = True
        self.cargando_cerebro = True
        self.en_conversacion = False
        self.oido = None
        self.voz = None
        self.bandeja = None
        opciones = [
            ("Hablar con JARVIS", self.activar),
            ("Callar", self.callar),
            (lambda: "Activar micrófono" if self.silencio else "Silenciar micrófono", self.alternar_silencio),
            (lambda: "Ocultar el reactor" if self.cfg.get("mostrar_orbe", True) else "Mostrar el reactor", self.alternar_orbe),
            ("-", None),
            ("Configuración", lambda: os.startfile(ruta("config.json"))),
            ("Entrenar (mis ejemplos)", lambda: os.startfile(ruta("mis_ejemplos.json"))),
            ("Recargar configuración", self.recargar),
            ("Carpeta de datos", lambda: os.startfile(DATOS)),
            ("-", None),
            ("Salir", self.apagar),
        ]
        self.opciones = opciones
        self.hud = HUD(self.cfg, ICONO, al_clic=self.clic_reactor, menu=opciones)
        self.cerebro = Cerebro(self.cfg, self.alm_memoria)
        self.hab = Habilidades(self.cfg, self)
        self.reflejos = Reflejos(self.cfg, self.alm_comandos, self.hab.apps)

    @property
    def trato(self):
        return self.cfg.get("trato", "señor")

    # ================================================================ arranque
    def arrancar(self):
        try:
            import pyautogui
            pyautogui.FAILSAFE = False
        except Exception:
            pass
        from voz import Voz
        try:
            from oido import Oido
            self.oido = Oido(self.cfg, al_aplaudir=self.activar,
                             al_nivel=lambda n: setattr(self.hud, "nivel_mic", n))
            self.oido.iniciar()
        except Exception as e:
            self.oido = None
            self.hud.estado("ERROR", "No encuentro un micrófono. Conéctalo y reinicia JARVIS.")
            log.error("Sin micrófono: %s", e)
        try:
            self.voz = Voz(self.cfg, self.oido, al_nivel=lambda n: setattr(self.hud, "nivel_voz", n))
        except Exception as e:
            log.error("Sin voz: %s", e)
        self.bandeja = iniciar_bandeja(ICONO, self.opciones)
        iniciar_atajos(self.cfg, self.activar, self.callar)
        threading.Thread(target=self._preparar_cerebro, daemon=True).start()
        threading.Thread(target=self._vigilar_clima, daemon=True).start()
        threading.Thread(target=self._servidor_unico, daemon=True).start()
        time.sleep(4.3)  # deja terminar la animación de arranque
        if self.cfg.get("saludo_al_iniciar", True):
            self.decir(self._saludo())
        self.hud.estado("EN ESPERA", "")
        self.bucle()

    def _preparar_cerebro(self):
        try:
            if not self.cerebro.encender():
                if not self.cerebro.ruta_ollama():
                    self.hud.alerta("Falta Ollama (el cerebro). Instálalo desde ollama.com y reinicia JARVIS.")
                    self.decir(f"{self.trato.capitalize()}, para pensar necesito Ollama. Le abro la página de descarga; "
                               "mientras tanto puedo abrir programas y controlar su música.")
                    webbrowser.open("https://ollama.com/download/windows")
                else:
                    self.hud.alerta("Ollama no responde. Ábrelo manualmente.")
                return
            antes = self.cerebro.modelo_ideal() in [m.split(":latest")[0] for m in self.cerebro.modelos_instalados()] or \
                self.cerebro.modelo_ideal() in self.cerebro.modelos_instalados()
            if not antes:
                self.decir(f"Descargando mi núcleo de inteligencia por primera vez, {self.trato}. "
                           "Tardará unos minutos; puede seguir dándome órdenes sencillas mientras tanto.")
            modelo = self.cerebro.preparar(progreso=self.hud.progreso)
            if modelo and not antes:
                self.decir(f"Núcleo de inteligencia en línea. Ahora puedo hacer cualquier cosa que me pida, {self.trato}.")
        except Exception as e:
            log.exception("Error preparando el cerebro: %s", e)
        finally:
            self.cargando_cerebro = False

    def _vigilar_clima(self):
        while self.ejecutando:
            try:
                largo, corto = self.hab.clima_texto()
                if corto:
                    m = re.search(r"máxima (-?\d+) °C, mínima (-?\d+) °C, lluvia (\d+) %", largo)
                    extra = f"\nMÁX {m.group(1)}°  MÍN {m.group(2)}°  LLUVIA {m.group(3)}%" if m else ""
                    self.hud.clima(corto + extra)
                    self.clima_largo = largo
            except Exception as e:
                log.info("Clima no disponible: %s", e)
            time.sleep(1800)

    def _saludo(self):
        ahora = datetime.datetime.now()
        h = ahora.hour
        momento = "Buenos días" if h < 12 else "Buenas tardes" if h < 19 else "Buenas noches"
        nombre = self.cfg.get("nombre_usuario") or self.trato
        partes = [f"{momento}, {nombre}.", f"Son {hora_hablada(ahora)}."]
        largo = getattr(self, "clima_largo", None)
        if largo:
            m = re.search(r"^(.+?): (-?\d+) °C, sensación -?\d+ °C, ([^,]+),", largo)
            if m:
                partes.append(f"En {m.group(1)} hay {m.group(2)} grados, {m.group(3)}.")
        hoy = [r for r in self.alm_recordatorios.datos if r["cuando"][:10] == ahora.date().isoformat()]
        if hoy:
            partes.append(f"Tiene {len(hoy)} recordatorio{'s' if len(hoy) > 1 else ''} para hoy.")
        partes.append("Todos los sistemas en línea.")
        return " ".join(partes)

    def _servidor_unico(self):
        """Si abres JARVIS otra vez, la segunda copia solo le avisa a esta que la llamaste."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.bind(("127.0.0.1", PUERTO_UNICO + 1))
            s.listen(2)
            while self.ejecutando:
                c, _ = s.accept()
                c.close()
                self.activar()
        except Exception:
            pass

    # ================================================================ conversación
    def bucle(self):
        while self.ejecutando:
            try:
                if self.activar_evt.is_set():
                    self.activar_evt.clear()
                    self.conversar(saludo=True)
                    continue
                if self.silencio or not self.oido:
                    self.activar_evt.wait(0.5)
                    continue
                texto = self.oido.escuchar(espera=None, limite=14, abortar=self.activar_evt)
                if not texto:
                    continue
                log.info("Oído (pasivo): %s", texto)
                orden = extraer_orden(texto, self.cfg.get("palabras_activacion", ["jarvis"]))
                if orden is None:
                    continue
                self.conversar(orden=orden or None, saludo=not orden)
            except Exception as e:
                log.exception("Error en el bucle principal: %s", e)
                time.sleep(1)

    def conversar(self, orden=None, saludo=False):
        self.en_conversacion = True
        try:
            self._conversar(orden, saludo)
        finally:
            self.en_conversacion = False
            self.activar_evt.clear()
            self.hud.estado("EN ESPERA", "")

    def _conversar(self, orden=None, saludo=False):
        if saludo:
            self.hud.estado("ESCUCHANDO", "Te escucho...")
            self.decir(random.choice(SALUDOS_ESCUCHA).format(t=self.trato), registrar=False)
        seguir = True
        while seguir and self.ejecutando:
            if orden is None:
                if not self.oido:
                    break
                self.hud.estado("ESCUCHANDO", "Te escucho...")
                orden = self.oido.escuchar(espera=8, limite=16,
                                           al_empezar=lambda: self.hud.estado("ESCUCHANDO", "· · ·"))
                if not orden:
                    break
                quitada = extraer_orden(orden, self.cfg.get("palabras_activacion", ["jarvis"]))
                orden = quitada or orden
            resultado = self.procesar(orden)
            if resultado == "salir":
                self.apagar(despedirse=False)
                return
            if resultado == "fin" or not self.oido:
                break
            # ventana de conversación: puedes seguir hablando sin decir "Jarvis"
            segundos = float(self.cfg.get("segundos_conversacion", 7))
            if segundos <= 0:
                break
            self.hud.estado("ESCUCHANDO", "¿Algo más? Puedes seguir hablando.")
            orden = self.oido.escuchar(espera=segundos, limite=16, abortar=self.activar_evt,
                                       al_empezar=lambda: self.hud.estado("ESCUCHANDO", "· · ·"))
            if not orden:
                break
            quitada = extraer_orden(orden, self.cfg.get("palabras_activacion", ["jarvis"]))
            orden = quitada or orden

    def procesar(self, orden):
        log.info("TÚ: %s", orden)
        self.hud.registrar("TÚ", orden)
        self.hud.estado("PROCESANDO", "> " + orden)
        n = normalizar(orden)
        if n in CALLAR:
            self.callar()
            return "fin"
        if n in DESPEDIDAS:
            self.decir(random.choice(["A su servicio, {t}.", "Un placer, {t}.", "Para eso estoy."]).format(t=self.trato))
            return "fin"
        plan = self.reflejos.interpretar(orden)
        if plan is None:
            if not self.cerebro.modelo:
                if self.cargando_cerebro:
                    self.decir(f"Mi núcleo de inteligencia aún se está cargando, {self.trato}. Mientras tanto puedo abrir "
                               "aplicaciones y páginas, controlar el volumen y la música.")
                else:
                    self.decir(f"Mi núcleo de inteligencia no está disponible, {self.trato}. Revise que Ollama esté instalado.")
                return
            plan = self.cerebro.pensar(orden, self.contexto())
        return self.ejecutar_plan(plan)

    def ejecutar_plan(self, plan, ronda=0):
        respuesta = (plan.get("respuesta") or "").strip()
        if ronda == 0 and not respuesta and not plan.get("acciones"):
            self.decir(f"Disculpe, {self.trato}, ¿podría repetirlo?")
            return
        hilo = None
        if respuesta:
            hilo = threading.Thread(target=self.decir, args=(respuesta,), daemon=True)
            hilo.start()
        infos, decires, salir = [], [], False
        for accion in plan.get("acciones", []):
            clase, texto = self.hab.ejecutar(accion)
            if clase == "salir":
                salir = True
            elif clase == "info" and texto:
                infos.append(texto)
            elif clase == "decir" and texto:
                decires.append(texto)
        if hilo:
            hilo.join()
        for d in decires:
            self.decir(d)
        if salir:
            return "salir"
        if infos:
            if self.cerebro.modelo and ronda < 2:
                self.hud.estado("PROCESANDO", "Analizando resultados...")
                return self.ejecutar_plan(self.cerebro.pensar("", resultados="\n\n".join(infos)), ronda + 1)
            self.decir(re.sub(r"^\[[^\]]+\]\s*", "", infos[0])[:300])

    def contexto(self):
        ahora = datetime.datetime.now()
        fecha = f"{DIAS[ahora.weekday()]} {ahora.day} de {MESES[ahora.month - 1]} de {ahora.year}, {ahora:%H:%M}"
        partes = [f"Contexto: hoy es {fecha}", f"ciudad del usuario: {self.cfg.get('ciudad', '')}"]
        if self.cfg.get("nombre_usuario"):
            partes.append(f"el usuario se llama {self.cfg['nombre_usuario']}")
        v = ventana_activa()
        if v:
            partes.append(f"ventana activa: {v[:80]}")
        mem = self.alm_memoria.datos[-25:]
        if mem:
            partes.append("memoria del usuario: " + "; ".join(mem))
        aprendidos = list(self.alm_comandos.datos)[:15]
        if aprendidos:
            partes.append("comandos aprendidos (usa la acción rutina con su nombre): " + ", ".join(aprendidos))
        return " | ".join(partes)

    # ================================================================ utilidades para las habilidades
    def decir(self, texto, registrar=True):
        if not texto:
            return
        if registrar:
            self.hud.registrar("JARVIS", texto)
        self.hud.estado("HABLANDO", texto[:90] + ("..." if len(texto) > 90 else ""))
        if self.voz:
            self.voz.decir(texto)
        else:
            time.sleep(min(6, len(texto) / 15))
        if not self.en_conversacion:
            self.hud.estado("EN ESPERA", "")

    def confirmar(self, pregunta):
        self.decir(pregunta)
        if not self.oido:
            return False
        self.hud.estado("ESCUCHANDO", "Responde sí o no")
        r = normalizar(self.oido.escuchar(espera=7, limite=5) or "")
        palabras = r.split()
        return bool(palabras) and palabras[0] != "no" and (any(p in SI for p in palabras) or r in SI)

    def sonar_recordatorio(self, texto):
        def _pitido():
            try:
                import winsound
                for f in (880, 1175, 880, 1175):
                    winsound.Beep(f, 140)
            except Exception:
                pass
        threading.Thread(target=_pitido, daemon=True).start()
        self.hud.alerta(texto)
        time.sleep(0.8)
        self.decir(f"{self.trato.capitalize()}, le recuerdo: {texto}", registrar=False)

    def poner_modo(self, modo):
        self.silencio = modo == "silencio"
        self.hud.silencio(self.silencio)

    # ================================================================ controles
    def activar(self):
        if self.voz and self.voz.hablando:
            self.voz.detener()
            return
        self.activar_evt.set()

    def clic_reactor(self):
        self.activar()

    def callar(self):
        if self.voz:
            self.voz.detener()

    def alternar_silencio(self):
        self.poner_modo("activo" if self.silencio else "silencio")

    def alternar_orbe(self):
        self.hud.mostrar_orbe(not self.cfg.get("mostrar_orbe", True))

    def recargar(self):
        nuevo = cargar_config()
        self.cfg.clear()
        self.cfg.update(nuevo)
        self.cerebro.recargar_entrenamiento()
        self.hud.registrar("JARVIS", "Configuración y entrenamiento recargados.")
        self.hud.estado("EN ESPERA", "Configuración recargada")

    def apagar(self, despedirse=True):
        if despedirse:
            self.decir(f"Desconectando sistemas. Hasta pronto, {self.trato}.")
        self.ejecutando = False
        try:
            if self.bandeja:
                self.bandeja.stop()
        except Exception:
            pass
        self.hud.cerrar()


# ==================================================================== inicio
def ya_esta_abierto():
    try:
        c = socket.create_connection(("127.0.0.1", PUERTO_UNICO + 1), timeout=0.5)
        c.close()
        return True
    except OSError:
        return False


def main():
    if ES_WINDOWS:
        try:
            import ctypes
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(2)
            except Exception:
                ctypes.windll.user32.SetProcessDPIAware()
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("StarkIndustries.JARVIS")
        except Exception:
            pass
    if ya_esta_abierto():
        return  # la otra copia ya recibió el aviso y se activa
    log.info("===== J.A.R.V.I.S. %s iniciando =====", VERSION)
    jarvis = Jarvis()
    threading.Thread(target=jarvis.arrancar, daemon=True).start()
    try:
        jarvis.hud.run()
    except KeyboardInterrupt:
        pass
    log.info("JARVIS apagado.")
    os._exit(0)


if __name__ == "__main__":
    main()
