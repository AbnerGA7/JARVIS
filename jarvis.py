# -*- coding: utf-8 -*-
"""
 ╦╔═╗╦═╗╦  ╦╦╔═╗
 ║╠═╣╠╦╝╚╗╔╝║╚═╗   J.A.R.V.I.S. 2.0 — Asistente de voz para Windows
╚╝╩ ╩╩╚═ ╚╝ ╩╚═╝   Cerebro en la nube (Groq, gratis) · Voz neural · HUD holográfico

Se activa diciendo "Jarvis ...", aplaudiendo dos veces, con Ctrl+Alt+J o haciendo clic en el reactor.
"""
import os, re, sys, time, random, socket, datetime, threading, webbrowser

from config import (VERSION, ICONO, DATOS, ES_WINDOWS, Almacen, cargar_config, guardar_config, ruta, normalizar, log)
from cerebro import Cerebro
from habilidades import Habilidades, DIAS, MESES, hora_hablada
from rapido import Reflejos
from hud import HUD
from bandeja import iniciar_bandeja, iniciar_atajos
import servidor
import arranque

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
            ("Conectar celular", self.conectar_celular),
            ("Desvincular celulares", self.desvincular_celulares),
            ("Micrófono y parlantes", self.abrir_ajustes_audio),
            (lambda: ("✓ " if self.cfg.get("iniciar_con_windows", True) else "    ") + "Iniciar con Windows",
             self.alternar_inicio_windows),
            ("Clave de Groq (cerebro en la nube)", self.cambiar_clave),
            ("Clave de Gemini (respaldo y visión)", self.cambiar_clave_gemini),
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
        self.enlace = servidor.Enlace(self)

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
            self.oido = Oido(self.cfg, al_aplaudir=self._doble_aplauso,
                             al_nivel=lambda n: setattr(self.hud, "nivel_mic", n))
            self.oido.al_aplauso_suelto = lambda: self.hud.aplauso("suelto")
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
        if self.cfg.get("iniciar_con_windows", True):
            arranque.activar()           # se renueva en cada inicio por si JARVIS cambió de carpeta
        if self.cfg.get("enlace_celular", True):
            self.enlace.iniciar()
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
            if self.cerebro.usar_nube():
                self._conectar_groq()
                self._conectar_gemini()
            else:
                self._preparar_ollama()
        except Exception as e:
            log.exception("Error preparando el cerebro: %s", e)
        finally:
            self.cargando_cerebro = False

    def _conectar_groq(self, forzar_dialogo=False):
        """Conecta el cerebro en la nube. Si no hay clave (o no sirve), muestra la ventana para pegarla."""
        ok, msg = (False, "") if forzar_dialogo else self.cerebro.preparar_nube()
        pidio = False
        primera = not self.cerebro.clave_groq()
        while not ok and self.ejecutando:
            if msg.startswith("Sin conexión"):
                self.hud.alerta("Sin internet: no puedo conectar mi cerebro en la nube. Reintentando...")
                time.sleep(15)
                ok, msg = self.cerebro.preparar_nube()
                continue
            error = None if (primera and not pidio) else (msg or None)
            if primera and not pidio:
                threading.Thread(target=self.decir, daemon=True, args=(
                    f"{self.trato.capitalize()}, para activar mi núcleo de inteligencia necesito su clave "
                    "gratuita de Groq. Le abrí una ventana para pegarla.",)).start()
            pidio = True
            clave = self.hud.pedir_clave(error)
            if clave is None:
                self.hud.alerta("Sin clave de Groq: solo puedo hacer órdenes simples. "
                                "Clic derecho en el reactor → Clave de Groq.")
                return False
            ok, msg = self.cerebro.probar_groq(clave)
            if ok:
                self.cfg["groq_api_key"] = clave.strip()
                guardar_config(self.cfg)
                ok, msg = self.cerebro.preparar_nube()
        if ok and pidio:
            self.hud.registrar("JARVIS", "Núcleo en la nube conectado.")
            self.decir(f"Núcleo de inteligencia en la nube conectado. Ahora puedo hacer cualquier cosa que me pida, {self.trato}.")
        return ok

    def _conectar_gemini(self, forzar_dialogo=False):
        """Gemini es opcional: respaldo automático de Groq y visión de pantalla. Se ofrece una sola vez."""
        ok, msg = (False, "") if forzar_dialogo else self.cerebro.preparar_gemini()
        if ok:
            return True
        tiene_clave = bool(self.cerebro.clave_gemini())
        if not forzar_dialogo:
            if msg.startswith("Sin conexión"):
                return False
            if not tiene_clave and self.cfg.get("gemini_preguntado"):
                return False
        self.cfg["gemini_preguntado"] = True
        guardar_config(self.cfg)
        error = msg if (tiene_clave and not forzar_dialogo) else None
        while self.ejecutando:
            clave = self.hud.pedir_clave(error, servicio="gemini")
            if clave is None:
                return False
            ok, error, modelo = self.cerebro.probar_gemini(clave)
            if ok:
                self.cfg["gemini_api_key"] = clave.strip()
                guardar_config(self.cfg)
                self.cerebro.preparar_gemini()
                self.hud.registrar("JARVIS", f"Gemini conectado ({modelo}).")
                self.decir(f"Núcleo de respaldo conectado, {self.trato}. Ahora también puedo ver su pantalla.")
                return True
        return False

    # ================================================================ celular
    def conectar_celular(self, decirlo=False):
        if not self.enlace.activo:
            self.hud.alerta("El enlace con el celular está desactivado en la configuración.")
            return
        pin = self.enlace.nuevo_pin()
        self.hud.mostrar_pin(pin, servidor.ip_local(), servidor.PUERTO, servidor.PIN_MINUTOS, self.enlace.url_remota)
        if decirlo:
            self.decir(f"Abra la app JARVIS en su celular y escriba el código que aparece en pantalla.")

    def desvincular_celulares(self):
        self.enlace.desvincular_todos()
        self.hud.registrar("JARVIS", "Todos los celulares fueron desvinculados.")

    # ================================================================ micrófono y parlantes
    def abrir_ajustes_audio(self):
        from audio import listar_microfonos, listar_parlantes
        self._sensibilidad_antes = self.cfg.get("sensibilidad_aplauso", 0.35)
        self.hud.ajustes_audio(listar_microfonos(), listar_parlantes(), self.cfg.get("microfono", ""),
                               self.cfg.get("parlantes", ""), self._probar_microfono, self._probar_parlantes,
                               self._guardar_audio, self._sensibilidad_antes,
                               lambda u: self.cfg.__setitem__("sensibilidad_aplauso", u))

    def _probar_microfono(self, nombre):
        """Cambia de micrófono en vivo para que la barra de la ventana muestre si te escucha."""
        if not self.oido:
            return
        self.cfg["microfono"] = nombre
        try:
            self.oido.reiniciar()
        except Exception:
            self.hud.alerta("No pude abrir ese micrófono. Prueba con otro.")

    def _probar_parlantes(self, nombre):
        if not self.voz:
            return
        if not self.voz.abrir_salida(nombre):
            self.hud.alerta("No pude usar esa salida de audio. Uso la predeterminada.")
        self.decir(f"Así sueno por estos parlantes, {self.trato}.", registrar=False)

    def _guardar_audio(self, microfono, parlantes, guardar=True):
        cambio_mic = microfono != self.cfg.get("microfono", "") or not guardar
        self.cfg["microfono"], self.cfg["parlantes"] = microfono, parlantes
        if self.oido and cambio_mic:
            try:
                self.oido.reiniciar()
            except Exception:
                pass
        if self.voz:
            self.voz.abrir_salida(parlantes)
        if guardar:
            guardar_config(self.cfg)
            self.hud.registrar("JARVIS", "Ajustes de audio guardados.")
        else:
            self.cfg["sensibilidad_aplauso"] = getattr(self, "_sensibilidad_antes", self.cfg.get("sensibilidad_aplauso", 0.35))

    def alternar_inicio_windows(self):
        activo = not self.cfg.get("iniciar_con_windows", True)
        self.cfg["iniciar_con_windows"] = activo
        guardar_config(self.cfg)
        arranque.activar() if activo else arranque.desactivar()
        self.hud.registrar("JARVIS", "Me iniciaré al encender la PC." if activo else "Ya no me iniciaré con Windows.")

    def cambiar_clave_gemini(self):
        threading.Thread(target=self._conectar_gemini, kwargs={"forzar_dialogo": True}, daemon=True).start()

    def cambiar_clave(self):
        threading.Thread(target=self._conectar_groq, kwargs={"forzar_dialogo": True}, daemon=True).start()

    def _preparar_ollama(self):
        if not self.cerebro.encender():
            if not self.cerebro.ruta_ollama():
                self.hud.alerta("Falta Ollama (el cerebro local). Instálalo desde ollama.com o usa Groq.")
                webbrowser.open("https://ollama.com/download/windows")
            else:
                self.hud.alerta("Ollama no responde. Ábrelo manualmente.")
            return
        antes = self.cerebro.modelo_ideal() in [m.split(":latest")[0] for m in self.cerebro.modelos_instalados()] or \
            self.cerebro.modelo_ideal() in self.cerebro.modelos_instalados()
        if not antes:
            self.decir(f"Descargando mi núcleo de inteligencia por primera vez, {self.trato}. "
                       "Tardará unos minutos; puede seguir dándome órdenes sencillas mientras tanto.")
        self.cerebro.motor = "ollama"
        modelo = self.cerebro.preparar(progreso=self.hud.progreso)
        if modelo and not antes:
            self.decir(f"Núcleo de inteligencia en línea. Ahora puedo hacer cualquier cosa que me pida, {self.trato}.")

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

    def procesar(self, orden, origen=None):
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
                    self.decir(f"Mi núcleo de inteligencia no está conectado, {self.trato}. Haga clic derecho en el reactor "
                               "y elija Clave de Groq o Clave de Gemini.")
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
            if servidor.es_remoto():
                self.decir(respuesta)          # pedido del celular: la respuesta se devuelve en orden
            else:
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
        c = self.cerebro
        if c.motor == "groq":
            nucleo = f"tu núcleo de IA: Groq {c.groq_principal} (respaldo {c.groq_respaldo})"
        elif c.motor:
            nucleo = f"tu núcleo de IA: {c.motor} {c.modelo}"
        else:
            nucleo = "tu núcleo de IA: desconectado"
        if c.modelo_gemini:
            nucleo += f", Gemini {c.modelo_gemini} como respaldo y visión"
        partes.append(nucleo)
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
        remoto = servidor.capturar(texto)
        if registrar:
            self.hud.registrar("JARVIS", texto)
        if remoto and not servidor.hablar_en_pc():
            return                              # lo dirá el celular con su propia voz
        self.hud.estado("HABLANDO", texto[:90] + ("..." if len(texto) > 90 else ""))
        if self.voz:
            self.voz.decir(texto)
        else:
            time.sleep(min(6, len(texto) / 15))
        if not self.en_conversacion:
            self.hud.estado("EN ESPERA", "")

    def confirmar(self, pregunta):
        if servidor.es_remoto():
            return servidor.confirmar_remoto(pregunta)
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
    def _doble_aplauso(self):
        self.hud.aplauso("doble")
        if not self.hud.probando_aplausos:      # en la prueba de aplausos solo se muestra, no se activa
            self.activar()

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


def autoprueba(archivo):
    """JARVIS.exe --autotest salida.txt : comprueba que el .exe tenga todas sus piezas (lo usa la compilación)."""
    import importlib, traceback
    informe, fallos = [], 0
    modulos = ["config", "cerebro", "habilidades", "rapido", "hud", "bandeja", "oido", "voz", "audio",
               "numpy", "requests", "sounddevice", "speech_recognition", "pygame", "edge_tts", "pyttsx3", "pyautogui",
               "pyperclip", "psutil", "pycaw.pycaw", "comtypes", "screen_brightness_control", "pystray", "PIL.Image",
               "keyboard", "ddgs", "certifi", "tkinter", "cryptography.hazmat.primitives.ciphers.aead", "servidor", "tunel", "arranque"]
    for m in modulos:
        try:
            importlib.import_module(m)
            informe.append(f"OK    {m}")
        except Exception as e:
            fallos += 1
            informe.append(f"FALLA {m}: {e!r}")
    from config import BASE, cargar_config, cargar_entrenamiento
    for nombre, prueba in [("icono", lambda: os.path.exists(ICONO)),
                           ("config por defecto", lambda: bool(cargar_config().get("palabras_activacion"))),
                           ("entrenamiento", lambda: len(cargar_entrenamiento()) > 10),
                           ("certificados https", lambda: os.path.exists(__import__("certifi").where())),
                           ("cifrado", lambda: __import__("tunel").descifrar(__import__("tunel").cifrar({"a": 1}, b"k" * 32), b"k" * 32) == {"a": 1}),
                           ("cloudflared incluido", lambda: os.path.exists(os.path.join(BASE, "cloudflared.exe")) or not getattr(sys, "frozen", False)),
                           ("ventana tk", lambda: (lambda r: (r.update(), r.destroy(), True)[-1])(__import__("tkinter").Tk())),
                           ("reflejos", lambda: __import__("rapido").Reflejos(cargar_config(), Almacen("prueba_cmd.json", {}),
                                                                            None).interpretar("qué hora es") is not None)]:
        try:
            ok = prueba()
        except Exception:
            ok = False
            informe.append(traceback.format_exc(limit=2))
        fallos += 0 if ok else 1
        informe.append(f"{'OK   ' if ok else 'FALLA'} {nombre}")
    informe.append(f"BASE={BASE}")
    informe.append("RESULTADO: " + ("TODO OK" if fallos == 0 else f"{fallos} FALLAS"))
    with open(archivo, "w", encoding="utf-8") as f:
        f.write("\n".join(informe))
    return 0 if fallos == 0 else 1


def main():
    if "--autotest" in sys.argv:
        i = sys.argv.index("--autotest")
        archivo = sys.argv[i + 1] if len(sys.argv) > i + 1 else "autotest.txt"
        os._exit(autoprueba(archivo))
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
