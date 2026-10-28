# -*- coding: utf-8 -*-
"""
Enlace con el celular (app JARVIS para Android).

- En la misma WiFi el celular se conecta directo (y encuentra la PC solo por UDP: "JARVIS?").
- Desde cualquier lugar (datos móviles) entra por un túnel de Cloudflare cuya dirección se publica cifrada (tunel.py).
- El celular se vincula una vez con un código que muestra la PC (p. ej. K7P2-QX9M); luego usa un token secreto.

API (JSON, con cabecera  Authorization: Bearer <token>):
  POST /api/emparejar   {"pin", "dispositivo"}            -> {"token", "pc", "canal_id", "canal_clave", "url", ...}
  GET  /api/estado                                         -> CPU, RAM, batería, volumen, clima, núcleo
  POST /api/orden       {"texto", "hablar_en_pc", "confirmado"} -> {"respuestas": [...], "pregunta"?}
  POST /api/accion      {"tipo", "valor", ..., "confirmado"}      -> igual que /api/orden
  GET  /api/pantalla?ancho=1000&calidad=60                 -> imagen JPEG de la pantalla
  POST /api/raton       {"dx","dy"} | {"clic": "izq|der|doble"} | {"rueda": n}
  POST /api/teclado     {"texto"} | {"teclas": "ctrl+c"}
  GET  /api/apps                                           -> nombres de las apps instaladas
"""
import io, json, time, socket, secrets, datetime, threading
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from config import log, VERSION, Almacen
import tunel as tun

PUERTO = 47654
PUERTO_DESCUBRIR = 47655
PIN_MINUTOS = 5

_contexto = threading.local()       # datos del pedido remoto en curso (por hilo)


def es_remoto():
    return getattr(_contexto, "activo", False)


def capturar(texto):
    """Lo que JARVIS dice durante un pedido remoto se devuelve al celular."""
    if es_remoto():
        _contexto.respuestas.append(texto)
        return True
    return False


def hablar_en_pc():
    return getattr(_contexto, "hablar_en_pc", False)


def confirmar_remoto(pregunta):
    """En pedidos remotos la confirmación se hace con un botón en el celular."""
    if getattr(_contexto, "confirmado", False):
        return True
    _contexto.pregunta = pregunta
    return False


def ip_local():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


class Enlace:
    def __init__(self, nucleo):
        self.n = nucleo                     # instancia de Jarvis
        self.dispositivos = Almacen("dispositivos.json", {})
        self.pin = None
        self.pin_vence = 0.0
        self.fallos = 0
        self.bloqueado_hasta = 0.0
        self.lock = threading.Lock()        # una orden remota a la vez
        self.activo = False
        self.tunel = None

    # ------------------------------------------------------------ arranque
    def iniciar(self):
        try:
            servidor = ThreadingHTTPServer(("0.0.0.0", PUERTO), self._manejador())
            servidor.daemon_threads = True
            threading.Thread(target=servidor.serve_forever, daemon=True).start()
            threading.Thread(target=self._responder_descubrimiento, daemon=True).start()
            self.activo = True
            log.info("Enlace con el celular activo en %s:%s", ip_local(), PUERTO)
            if self.n.cfg.get("acceso_remoto", True):
                self.tunel = tun.Tunel(PUERTO, al_cambiar=self._url_nueva, progreso=self.n.hud.progreso)
                self.tunel.iniciar()
        except OSError as e:
            log.error("No pude abrir el enlace con el celular (puerto %s): %s", PUERTO, e)

    def nuevo_pin(self):
        """Código de vinculación (válido 5 min). Sirve en la misma WiFi y también por internet."""
        self.pin = tun.codigo_nuevo()
        self.pin_vence = time.time() + PIN_MINUTOS * 60
        self.fallos = 0
        self._anunciar_codigo()
        return self.pin

    def _datos_conexion(self):
        return {"ip": ip_local(), "puerto": PUERTO, "pc": socket.gethostname()}

    def _anunciar_codigo(self):
        if self.tunel and self.pin and time.time() < self.pin_vence:
            self.tunel.anunciar_codigo(self.pin, self._datos_conexion())

    def _url_nueva(self, url):
        self._anunciar_codigo()          # si estabas vinculando, el celular recibe la dirección nueva
        self.n.hud.registrar("JARVIS", "Acceso desde internet listo.")

    def url_remota(self):
        return self.tunel.url if self.tunel else None

    def _responder_descubrimiento(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("0.0.0.0", PUERTO_DESCUBRIR))
        except OSError as e:
            log.warning("Sin descubrimiento automático: %s", e)
            return
        while True:
            try:
                datos, origen = s.recvfrom(256)
                if datos.strip() == b"JARVIS?":
                    info = {"jarvis": True, "pc": socket.gethostname(), "puerto": PUERTO, "version": VERSION}
                    s.sendto(json.dumps(info).encode(), origen)
            except Exception:
                time.sleep(0.5)

    # ------------------------------------------------------------ lógica
    def emparejar(self, pin, dispositivo):
        ahora = time.time()
        if ahora < self.bloqueado_hasta:
            return 429, {"error": "Demasiados intentos. Espera unos minutos."}
        if not self.pin or ahora > self.pin_vence:
            return 403, {"error": "En la PC: clic derecho en el reactor → Conectar celular, para ver el PIN."}
        if not secrets.compare_digest(tun.normalizar_codigo(pin), tun.normalizar_codigo(self.pin)):
            self.fallos += 1
            if self.fallos >= 5:
                self.bloqueado_hasta = ahora + 300
                self.pin = None
            return 403, {"error": "PIN incorrecto."}
        token = secrets.token_urlsafe(32)
        nombre = (dispositivo or "Celular")[:60]
        self.dispositivos.datos[token] = {"nombre": nombre, "desde": datetime.datetime.now().isoformat(timespec="seconds")}
        self.dispositivos.guardar()
        self.pin = None
        cfg = self.n.cfg
        respuesta = {"token": token, "version": VERSION, "trato": cfg.get("trato", "señor"), **self._datos_conexion()}
        if self.tunel:
            respuesta.update(canal_id=self.tunel.canal_id, canal_clave=self.tunel.canal.datos["clave"],
                             url=self.tunel.url)
        if cfg.get("compartir_clave_con_celular", True) and cfg.get("groq_api_key"):
            respuesta["groq_api_key"] = cfg["groq_api_key"]      # para el modo asistente sin PC
        self.n.hud.cerrar_pin()
        self.n.hud.registrar("JARVIS", f"{nombre} conectado.")
        threading.Thread(target=self.n.decir, args=(f"{nombre} vinculado correctamente, {cfg.get('trato', 'señor')}.",),
                         daemon=True).start()
        return 200, respuesta

    def desvincular_todos(self):
        self.dispositivos.datos.clear()
        self.dispositivos.guardar()

    def autorizado(self, cabecera):
        token = (cabecera or "").removeprefix("Bearer ").strip()
        return bool(token) and token in self.dispositivos.datos

    def ejecutar_remoto(self, funcion, hablar_en_pc=False, confirmado=False):
        with self.lock:
            _contexto.activo = True
            _contexto.respuestas = []
            _contexto.pregunta = None
            _contexto.confirmado = confirmado
            _contexto.hablar_en_pc = hablar_en_pc
            try:
                funcion()
            finally:
                _contexto.activo = False
            salida = {"respuestas": list(_contexto.respuestas)}
            if _contexto.pregunta:
                salida["pregunta"] = _contexto.pregunta
            return salida

    def estado(self):
        import psutil
        n = self.n
        bat = psutil.sensors_battery()
        datos = {"pc": socket.gethostname(), "version": VERSION, "cpu": psutil.cpu_percent(interval=0.2),
                 "ram": psutil.virtual_memory().percent, "bateria": round(bat.percent) if bat else None,
                 "cargando": bool(bat.power_plugged) if bat else None, "silencio": n.silencio,
                 "clima": getattr(n, "clima_largo", None), "volumen": None, "nucleo": None}
        try:
            vol = n.hab._volumen()
            datos["volumen"] = round(vol.GetMasterVolumeLevelScalar() * 100)
            datos["mudo"] = bool(vol.GetMute())
        except Exception:
            pass
        c = n.cerebro
        datos["nucleo"] = (f"Groq {c.groq_principal}" if c.motor == "groq" else c.modelo) or "desconectado"
        return datos

    def pantalla(self, ancho=1000, calidad=60):
        from PIL import ImageGrab
        img = ImageGrab.grab(all_screens=False)
        if img.width > ancho:
            img = img.resize((ancho, int(img.height * ancho / img.width)))
        buf = io.BytesIO()
        img.convert("RGB").save(buf, "JPEG", quality=max(20, min(90, calidad)))
        return buf.getvalue()

    def raton(self, d):
        import pyautogui
        if "dx" in d or "dy" in d:
            pyautogui.moveRel(float(d.get("dx", 0)), float(d.get("dy", 0)), _pause=False)
        clic = d.get("clic")
        if clic == "izq":
            pyautogui.click(_pause=False)
        elif clic == "der":
            pyautogui.click(button="right", _pause=False)
        elif clic == "doble":
            pyautogui.doubleClick(_pause=False)
        if d.get("rueda"):
            pyautogui.scroll(int(d["rueda"]) * 120, _pause=False)

    # ------------------------------------------------------------ HTTP
    def _manejador(self):
        enlace = self

        class Manejador(BaseHTTPRequestHandler):
            server_version = "JARVIS/" + VERSION

            def log_message(self, formato, *args):
                pass

            def _json(self, codigo, datos):
                cuerpo = json.dumps(datos, ensure_ascii=False).encode("utf-8")
                self.send_response(codigo)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(cuerpo)))
                self.end_headers()
                self.wfile.write(cuerpo)

            def _leer(self):
                largo = int(self.headers.get("Content-Length") or 0)
                if largo > 1_000_000:
                    return {}
                try:
                    return json.loads(self.rfile.read(largo) or b"{}")
                except Exception:
                    return {}

            def do_GET(self):
                url = urlparse(self.path)
                if url.path == "/api/hola":
                    return self._json(200, {"jarvis": True, "pc": socket.gethostname(), "version": VERSION})
                if not enlace.autorizado(self.headers.get("Authorization")):
                    return self._json(401, {"error": "Este celular no está vinculado."})
                try:
                    if url.path == "/api/estado":
                        return self._json(200, enlace.estado())
                    if url.path == "/api/pantalla":
                        q = parse_qs(url.query)
                        datos = enlace.pantalla(int(q.get("ancho", [1000])[0]), int(q.get("calidad", [60])[0]))
                        self.send_response(200)
                        self.send_header("Content-Type", "image/jpeg")
                        self.send_header("Content-Length", str(len(datos)))
                        self.end_headers()
                        return self.wfile.write(datos)
                    if url.path == "/api/apps":
                        apps = sorted({v[0] for v in enlace.n.hab.apps.apps.values()}, key=str.lower)
                        return self._json(200, {"apps": apps})
                except Exception as e:
                    log.exception("Error en %s", url.path)
                    return self._json(500, {"error": str(e)})
                self._json(404, {"error": "No existe"})

            def do_POST(self):
                url = urlparse(self.path)
                d = self._leer()
                if url.path == "/api/emparejar":
                    return self._json(*enlace.emparejar(d.get("pin", ""), d.get("dispositivo", "")))
                if not enlace.autorizado(self.headers.get("Authorization")):
                    return self._json(401, {"error": "Este celular no está vinculado."})
                n = enlace.n
                try:
                    if url.path == "/api/orden":
                        texto = str(d.get("texto", "")).strip()[:500]
                        if not texto:
                            return self._json(400, {"error": "Orden vacía"})
                        n.hud.registrar("CELULAR", texto)
                        r = enlace.ejecutar_remoto(lambda: n.procesar(texto, origen="celular"),
                                                   bool(d.get("hablar_en_pc")), bool(d.get("confirmado")))
                        return self._json(200, r)
                    if url.path == "/api/accion":
                        accion = {k: v for k, v in d.items() if k not in ("confirmado", "hablar_en_pc")}

                        def hacer():
                            clase, texto = n.hab.ejecutar(accion)
                            if clase in ("decir", "info") and texto:
                                n.decir(texto.split("] ", 1)[-1] if texto.startswith("[") else texto)
                        r = enlace.ejecutar_remoto(hacer, bool(d.get("hablar_en_pc")), bool(d.get("confirmado")))
                        return self._json(200, r)
                    if url.path == "/api/raton":
                        enlace.raton(d)
                        return self._json(200, {"ok": True})
                    if url.path == "/api/teclado":
                        if d.get("texto"):
                            n.hab.h_escribir(str(d["texto"])[:2000], {})
                        if d.get("teclas"):
                            n.hab.h_teclas(str(d["teclas"]), {})
                        return self._json(200, {"ok": True})
                except Exception as e:
                    log.exception("Error en %s", url.path)
                    return self._json(500, {"error": str(e)})
                self._json(404, {"error": "No existe"})

        return Manejador
