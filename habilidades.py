# -*- coding: utf-8 -*-
"""
Habilidades de J.A.R.V.I.S.: todo lo que puede hacer en tu PC y en internet.
Cada acción devuelve (clase, texto):
  None      -> nada que decir
  "decir"   -> Jarvis lo dice tal cual
  "info"    -> datos que la IA usará para responder
  "salir"   -> apagar a Jarvis
"""
import os, re, ast, json, math, time, uuid, difflib, datetime, threading, subprocess, webbrowser, urllib.parse, xml.etree.ElementTree as ET
import requests
from config import log, normalizar, SIN_VENTANA, ES_WINDOWS, DATOS

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) JARVIS/2.0"}
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
         "noviembre", "diciembre"]
CLIMA = {0: "despejado", 1: "mayormente despejado", 2: "parcialmente nublado", 3: "nublado", 45: "con neblina",
         48: "con neblina", 51: "con llovizna ligera", 53: "con llovizna", 55: "con llovizna intensa",
         56: "con llovizna helada", 57: "con llovizna helada", 61: "con lluvia ligera", 63: "con lluvia",
         65: "con lluvia fuerte", 66: "con lluvia helada", 67: "con lluvia helada", 71: "con nieve ligera",
         73: "con nieve", 75: "con nieve intensa", 77: "con granizo fino", 80: "con chubascos",
         81: "con chubascos", 82: "con chubascos fuertes", 85: "con chubascos de nieve", 86: "con nieve intensa",
         95: "con tormenta eléctrica", 96: "con tormenta y granizo", 99: "con tormenta y granizo"}
PROTEGIDOS = {"explorer", "svchost", "system", "csrss", "winlogon", "lsass", "services", "smss", "wininit",
              "dwm", "jarvis", "python", "pythonw", "ollama", "ollama app", "fontdrvhost", "sihost"}
PROCESOS = {"word": "winword", "powerpoint": "powerpnt", "bloc de notas": "notepad", "notas": "notepad",
            "calculadora": "calculatorapp", "edge": "msedge", "navegador": "chrome", "vs code": "code",
            "visual studio code": "code", "visual": "code", "teams": "ms-teams", "whatsapp": "whatsapp",
            "paint": "mspaint", "fotos": "photos", "reproductor": "microsoft.media.player", "configuracion": "systemsettings",
            "administrador de tareas": "taskmgr", "terminal": "windowsterminal", "consola": "cmd"}
CARPETAS = {"descargas": "shell:Downloads", "documentos": "shell:Personal", "mis documentos": "shell:Personal",
            "escritorio": "shell:Desktop", "imagenes": "shell:My Pictures", "fotos": "shell:My Pictures",
            "musica": "shell:My Music", "videos": "shell:My Video", "papelera": "shell:RecycleBinFolder",
            "papelera de reciclaje": "shell:RecycleBinFolder", "este equipo": "shell:MyComputerFolder",
            "mi pc": "shell:MyComputerFolder", "onedrive": "shell:OneDrive", "inicio": "shell:Startup"}
AJUSTES = {"wifi": "network-wifi", "red": "network", "internet": "network", "bluetooth": "bluetooth",
           "sonido": "sound", "audio": "sound", "pantalla": "display", "bateria": "batterysaver",
           "energia": "powersleep", "actualizaciones": "windowsupdate", "windows update": "windowsupdate",
           "apps": "appsfeatures", "aplicaciones": "appsfeatures", "fondo": "personalization-background",
           "fondo de pantalla": "personalization-background", "temas": "themes", "notificaciones": "notifications",
           "privacidad": "privacy", "almacenamiento": "storagesense", "mouse": "mousetouchpad",
           "teclado": "typing", "hora": "dateandtime", "idioma": "regionlanguage", "cuentas": "yourinfo",
           "impresoras": "printers", "camara": "privacy-webcam", "microfono": "privacy-microphone"}
VENTANA = {"minimizar_todo": "win+d", "escritorio": "win+d", "cambiar": "alt+tab", "maximizar": "win+up",
           "minimizar": "win+down", "cerrar": "alt+f4", "izquierda": "win+left", "derecha": "win+right",
           "vista_tareas": "win+tab", "nuevo_escritorio": "ctrl+win+d", "pantalla_completa": "f11"}
TECLAS = {"control": "ctrl", "mayusculas": "shift", "mayus": "shift", "windows": "win", "intro": "enter",
          "escape": "esc", "suprimir": "delete", "borrar": "backspace", "espacio": "space",
          "tabulador": "tab", "arriba": "up", "abajo": "down", "izquierda": "left", "derecha": "right",
          "inicio": "home", "fin": "end", "retroceso": "backspace", "supr": "delete"}
PELIGRO = re.compile(r"remove-item|\brm\b|\bdel\b|\berase\b|rmdir|\brd\b|format|clear-disk|stop-computer|"
                     r"restart-computer|set-executionpolicy|\breg\b|remove-|uninstall|diskpart|bcdedit|cipher|"
                     r"takeown|icacls|vssadmin|net user|disable-|stop-service|kill|taskkill", re.I)


def _carpeta_usuario(*partes):
    return os.path.join(os.path.expanduser("~"), *partes)


# ====================================================================== APPS
class IndiceApps:
    """Conoce TODAS las apps del menú Inicio (incluidas las de Microsoft Store)."""

    BASICAS = {"notepad": "notepad", "calc": "calc", "cmd": "cmd", "taskmgr": "taskmgr", "control": "control",
               "explorer": "explorer", "mspaint": "mspaint", "ms-settings:": "ms-settings:",
               "powershell": "powershell", "chrome": "chrome", "msedge": "msedge", "edge": "msedge"}

    def __init__(self, cfg):
        self.cfg = cfg
        self.apps = {}
        self.listo = threading.Event()
        threading.Thread(target=self.cargar, daemon=True).start()

    def cargar(self):
        if ES_WINDOWS:
            try:
                ps = ("[Console]::OutputEncoding=[System.Text.Encoding]::UTF8; "
                      "Get-StartApps | Select-Object Name,AppID | ConvertTo-Json -Compress")
                out = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True,
                                     timeout=40, creationflags=SIN_VENTANA).stdout.decode("utf-8", "ignore")
                datos = json.loads(out) if out.strip() else []
                if isinstance(datos, dict):
                    datos = [datos]
                self.apps = {normalizar(d["Name"]): (d["Name"], d["AppID"]) for d in datos if d.get("Name")}
                log.info("Conozco %d aplicaciones instaladas", len(self.apps))
            except Exception as e:
                log.warning("No pude listar las apps: %s", e)
        self.listo.set()

    @staticmethod
    def _puntaje(q, nombre):
        castigo = 0.5 if re.search(r"uninstall|desinstal|readme|help|ayuda|website|sitio web|manual|release notes", nombre) else 1
        if q == nombre:
            return 1.0 * castigo
        p = difflib.SequenceMatcher(None, q, nombre).ratio()
        palabras = nombre.split()
        if len(q) >= 3 and nombre.startswith(q):
            p = max(p, 0.93)
        if q in palabras:
            p = max(p, 0.9)
        elif len(q) >= 4 and q in nombre:
            p = max(p, 0.8)
        if palabras:
            p = max(p, difflib.SequenceMatcher(None, q, palabras[0]).ratio() * 0.92)
        return p * castigo

    def buscar(self, nombre):
        self.listo.wait(10)
        alias = {normalizar(k): v for k, v in self.cfg.get("alias_apps", {}).items()}
        destino = str(alias.get(normalizar(nombre), nombre))
        if destino.endswith(":"):                      # p. ej. "ms-settings:"
            return 1.0, (nombre, None, destino)
        q = normalizar(destino)
        mejor, puntos = None, 0.0
        for consulta in dict.fromkeys(x for x in (normalizar(nombre), q) if x):
            for n, (vis, appid) in self.apps.items():
                p = self._puntaje(consulta, n)
                if p > puntos + 1e-9 or (abs(p - puntos) <= 1e-9 and mejor and len(vis) < len(mejor[0])):
                    mejor, puntos = (vis, appid, None), p
        if puntos < 0.9 and q in self.BASICAS:
            return 0.95, (destino, None, self.BASICAS[q])
        return puntos, mejor

    def seguro(self, nombre):
        if not self.listo.is_set():
            return False
        p, _ = self.buscar(nombre)
        return p >= 0.9

    def abrir(self, nombre):
        puntos, app = self.buscar(nombre)
        if app and puntos >= 0.62:
            vis, appid, comando = app
            if comando:
                os.startfile(comando)
            else:
                subprocess.Popen(["explorer.exe", "shell:AppsFolder\\" + appid])
            return vis
        try:  # último intento: algo del PATH ("code", "steam"...)
            os.startfile(nombre)
            return nombre
        except Exception:
            return None


# ====================================================================== RECORDATORIOS
class Recordatorios:
    def __init__(self, almacen, al_sonar):
        self.alm = almacen
        self.al_sonar = al_sonar
        threading.Thread(target=self._vigilar, daemon=True).start()

    def agregar(self, texto, cuando):
        self.alm.datos.append({"id": uuid.uuid4().hex[:8], "cuando": cuando.isoformat(timespec="seconds"), "texto": texto})
        self.alm.guardar()

    def pendientes(self):
        return sorted(self.alm.datos, key=lambda r: r["cuando"])

    def cancelar_todos(self):
        self.alm.datos.clear(); self.alm.guardar()

    def _vigilar(self):
        while True:
            time.sleep(1)
            ahora = datetime.datetime.now()
            vencidos = [r for r in list(self.alm.datos) if datetime.datetime.fromisoformat(r["cuando"]) <= ahora]
            for r in vencidos:
                self.alm.datos.remove(r)
                self.alm.guardar()
                try:
                    self.al_sonar(r["texto"])
                except Exception as e:
                    log.error("Error al avisar recordatorio: %s", e)


def calcular_momento(accion, ahora=None):
    """Interpreta minutos/horas/segundos u hora "HH:MM" (con am/pm) y devuelve un datetime."""
    ahora = ahora or datetime.datetime.now()
    total = 0.0
    for clave, mult in (("segundos", 1), ("minutos", 60), ("horas", 3600)):
        v = accion.get(clave)
        if v not in (None, ""):
            try:
                total += float(str(v).replace(",", ".")) * mult
            except ValueError:
                pass
    if total > 0:
        return ahora + datetime.timedelta(seconds=total)
    hora = normalizar(str(accion.get("hora") or "").lower().replace(".", "").replace(":", " dospuntos "))
    m = re.search(r"(\d{1,2})(?: dospuntos (\d{2}))?\s*(am|pm|de la manana|de la tarde|de la noche)?", hora)
    if m:
        h, mi = int(m.group(1)), int(m.group(2) or 0)
        suf = m.group(3) or ""
        if suf in ("pm", "de la tarde", "de la noche") and h < 12:
            h += 12
        if suf in ("am", "de la manana") and h == 12:
            h = 0
        if h > 23 or mi > 59:
            return None
        momento = ahora.replace(hour=h, minute=mi, second=0, microsecond=0)
        if accion.get("fecha"):
            try:
                f = datetime.date.fromisoformat(str(accion["fecha"]))
                momento = momento.replace(year=f.year, month=f.month, day=f.day)
            except ValueError:
                pass
        if momento <= ahora:
            momento += datetime.timedelta(days=1)
        return momento
    return None


def hora_hablada(dt):
    h = dt.hour % 12 or 12
    momento = "de la mañana" if dt.hour < 12 else "de la tarde" if dt.hour < 19 else "de la noche"
    if dt.minute == 0:
        return f"las {h} en punto {momento}" if h != 1 else f"la una en punto {momento}"
    art = "la" if h == 1 else "las"
    return f"{art} {h} y {dt.minute:02d} {momento}" if dt.minute < 10 else f"{art} {h}:{dt.minute:02d} {momento}"


# ====================================================================== CÁLCULO SEGURO
_FUNCS = {k: getattr(math, k) for k in ("sqrt", "sin", "cos", "tan", "log", "log10", "exp", "floor", "ceil", "factorial", "radians", "degrees")}
_FUNCS.update({"abs": abs, "round": round, "pi": math.pi, "e": math.e, "raiz": math.sqrt})


def calcular(expr):
    expr = str(expr).replace("^", "**").replace("×", "*").replace("÷", "/").replace(",", ".")

    def ev(n):
        if isinstance(n, ast.Expression):
            return ev(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
            return n.value
        if isinstance(n, ast.BinOp):
            a, b = ev(n.left), ev(n.right)
            ops = {ast.Add: lambda: a + b, ast.Sub: lambda: a - b, ast.Mult: lambda: a * b, ast.Div: lambda: a / b,
                   ast.Mod: lambda: a % b, ast.FloorDiv: lambda: a // b,
                   ast.Pow: lambda: a ** b if abs(b) < 1000 else float("inf")}
            return ops[type(n.op)]()
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.USub, ast.UAdd)):
            return -ev(n.operand) if isinstance(n.op, ast.USub) else ev(n.operand)
        if isinstance(n, ast.Name) and n.id in _FUNCS and not callable(_FUNCS[n.id]):
            return _FUNCS[n.id]
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and callable(_FUNCS.get(n.func.id)):
            return _FUNCS[n.func.id](*[ev(x) for x in n.args])
        raise ValueError("expresión no permitida")

    r = ev(ast.parse(expr, mode="eval"))
    if isinstance(r, float):
        r = round(r, 6)
        if r.is_integer():
            r = int(r)
    return r


def numero_hablado(n):
    return str(n).replace(".", ",")


# ====================================================================== HABILIDADES
class Habilidades:
    def __init__(self, cfg, nucleo):
        self.cfg = cfg
        self.n = nucleo          # da acceso a: decir, confirmar, cerebro, hud, almacenes, poner_modo
        self.apps = IndiceApps(cfg)
        self.ultimos_archivos = []
        self.recordatorios = Recordatorios(nucleo.alm_recordatorios, nucleo.sonar_recordatorio)

    @property
    def trato(self):
        return self.cfg.get("trato", "señor")

    def ejecutar(self, accion):
        tipo = (accion.get("tipo") or "").lower()
        valor = accion.get("valor", "")
        if isinstance(valor, (list, dict)):
            valor = json.dumps(valor, ensure_ascii=False)
        valor = str(valor or "").strip()
        f = getattr(self, "h_" + tipo, None)
        if not f:
            log.warning("Acción desconocida: %s", accion)
            return ("info", f"[{tipo}] Esa acción no existe. Usa solo las acciones de la lista.")
        log.info("Acción: %s %s", tipo, valor)
        try:
            return f(valor, accion) or (None, "")
        except Exception as e:
            log.exception("Fallo en la acción %s", tipo)
            return ("info", f"[{tipo}] Falló: {e}")

    # ------------------------------------------------------------ apps y web
    def h_abrir_app(self, v, a):
        sitio = self._sitio(v)
        if sitio and not self.apps.seguro(v):
            webbrowser.open(sitio); return
        if v.lower().startswith("http"):
            webbrowser.open(v); return
        if not self.apps.abrir(v):
            return ("decir", f"No encuentro {v} instalada en su equipo, {self.trato}.")

    def h_cerrar_app(self, v, a):
        import psutil
        q = normalizar(v)
        objetivo = PROCESOS.get(q, q.replace(" ", ""))
        cerrados = 0
        for p in psutil.process_iter(["name"]):
            nombre = (p.info.get("name") or "").lower().removesuffix(".exe")
            if not nombre or nombre in PROTEGIDOS:
                continue
            if nombre == objetivo or nombre.startswith(objetivo) or (len(objetivo) >= 5 and objetivo in nombre):
                try:
                    p.terminate(); cerrados += 1
                except Exception:
                    pass
        if not cerrados:
            return ("decir", f"{v} no parece estar abierto, {self.trato}.")

    def _sitio(self, v):
        sitios = {normalizar(k): u for k, u in self.cfg.get("sitios", {}).items()}
        return sitios.get(normalizar(v))

    def h_abrir_web(self, v, a):
        url = self._sitio(v) or v
        if not re.match(r"^[a-z]+://", url):
            url = "https://" + url.replace(" ", "")
        webbrowser.open(url)

    def h_buscar_google(self, v, a):
        webbrowser.open("https://www.google.com/search?q=" + urllib.parse.quote(v))

    def h_buscar_youtube(self, v, a):
        webbrowser.open("https://www.youtube.com/results?search_query=" + urllib.parse.quote(v))

    def h_reproducir(self, v, a):
        if self.cfg.get("musica") == "spotify":
            os.startfile("spotify:search:" + urllib.parse.quote(v)); return
        try:
            html = requests.get("https://www.youtube.com/results?search_query=" + urllib.parse.quote(v),
                                headers=UA, timeout=8).text
            vid = re.search(r'"videoId":"([\w-]{11})"', html) or re.search(r"watch\?v=([\w-]{11})", html)
            webbrowser.open(f"https://www.youtube.com/watch?v={vid.group(1)}")
        except Exception:
            self.h_buscar_youtube(v, a)

    def h_abrir_carpeta(self, v, a):
        destino = CARPETAS.get(normalizar(v))
        if destino:
            subprocess.Popen(["explorer.exe", destino]); return
        if os.path.exists(v):
            os.startfile(v); return
        return ("decir", f"No encuentro la carpeta {v}.")

    def h_buscar_archivo(self, v, a):
        palabras = normalizar(v).split()
        if not palabras:
            return ("info", "[buscar_archivo] No se indicó qué buscar.")
        raices = [_carpeta_usuario(c) for c in ("Desktop", "Documents", "Downloads", "Pictures", "Music", "Videos",
                                                 "OneDrive", "Escritorio", "Documentos", "Descargas")]
        encontrados, t0 = [], time.time()
        for raiz in dict.fromkeys(r for r in raices if os.path.isdir(r)):
            for carpeta, subs, archivos in os.walk(raiz):
                subs[:] = [s for s in subs if not s.startswith((".", "node_modules", "AppData", "$"))]
                for nombre in archivos:
                    nn = normalizar(nombre)
                    if all(p in nn for p in palabras):
                        encontrados.append(os.path.join(carpeta, nombre))
                if len(encontrados) >= 8 or time.time() - t0 > 5:
                    break
            if len(encontrados) >= 8 or time.time() - t0 > 5:
                break
        self.ultimos_archivos = encontrados[:8]
        if not encontrados:
            return ("info", f"[buscar_archivo] No encontré archivos que coincidan con '{v}'.")
        lista = "\n".join(f"{i + 1}. {os.path.basename(p)} (en {os.path.dirname(p)})" for i, p in enumerate(self.ultimos_archivos))
        return ("info", f"[buscar_archivo] Encontré {len(encontrados)}:\n{lista}\nPregunta si quiere abrir alguno (acción abrir_archivo con el número).")

    def h_abrir_archivo(self, v, a):
        ruta = v
        if v.isdigit() and 0 < int(v) <= len(self.ultimos_archivos):
            ruta = self.ultimos_archivos[int(v) - 1]
        elif not os.path.exists(v) and self.ultimos_archivos:
            n = normalizar(v)
            ruta = next((p for p in self.ultimos_archivos if n and n in normalizar(os.path.basename(p))), self.ultimos_archivos[0])
        if os.path.exists(ruta):
            os.startfile(ruta); return
        return ("decir", "No encuentro ese archivo.")

    # ------------------------------------------------------------ control
    def _volumen(self):
        import comtypes
        try:
            comtypes.CoInitialize()
        except Exception:
            pass
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        dev = AudioUtilities.GetSpeakers()
        ev = getattr(dev, "EndpointVolume", None)
        if ev is not None:
            return ev
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        return cast(dev.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None), POINTER(IAudioEndpointVolume))

    def h_volumen(self, v, a):
        n = normalizar(v)
        num = re.search(r"\d+", n)
        try:
            vol = self._volumen()
            if num:
                vol.SetMute(0, None)
                vol.SetMasterVolumeLevelScalar(max(0, min(100, int(num.group()))) / 100, None)
            elif "silen" in n or "mute" in n or "quita" in n:
                vol.SetMute(1, None)
            elif "activ" in n or "desilen" in n:
                vol.SetMute(0, None)
            else:
                actual = vol.GetMasterVolumeLevelScalar()
                paso = 0.15 if "sub" in n or "aument" in n or "mas" in n else -0.15
                vol.SetMute(0, None)
                vol.SetMasterVolumeLevelScalar(max(0.0, min(1.0, actual + paso)), None)
        except Exception as e:
            log.info("Volumen por teclas (%s)", e)
            import pyautogui
            if num:
                pyautogui.press("volumedown", presses=50)
                pyautogui.press("volumeup", presses=int(num.group()) // 2)
            elif "silen" in n or "activ" in n:
                pyautogui.press("volumemute")
            else:
                pyautogui.press("volumeup" if "sub" in n or "aument" in n else "volumedown", presses=8)

    def h_brillo(self, v, a):
        try:
            import screen_brightness_control as sbc
            n = normalizar(v)
            num = re.search(r"\d+", n)
            if num:
                sbc.set_brightness(max(0, min(100, int(num.group()))))
            else:
                actual = sbc.get_brightness()[0]
                sbc.set_brightness(max(0, min(100, actual + (20 if "sub" in n or "aument" in n else -20))))
        except Exception as e:
            log.warning("Brillo: %s", e)
            return ("decir", f"No puedo controlar el brillo de esta pantalla, {self.trato}.")

    def h_media(self, v, a):
        import pyautogui
        n = normalizar(v)
        tecla = "nexttrack" if "sig" in n else "prevtrack" if "ant" in n else "stop" if "deten" in n else "playpause"
        pyautogui.press(tecla)

    def h_teclas(self, v, a):
        import pyautogui
        partes = [TECLAS.get(normalizar(k), k.strip().lower()) for k in re.split(r"\s*\+\s*", v) if k.strip()]
        if partes:
            pyautogui.hotkey(*partes)

    def h_ventana(self, v, a):
        combo = VENTANA.get(normalizar(v).replace(" ", "_"), None)
        if combo:
            self.h_teclas(combo, a)

    def h_escribir(self, v, a):
        import pyautogui, pyperclip
        anterior = ""
        try:
            anterior = pyperclip.paste()
        except Exception:
            pass
        pyperclip.copy(v)
        time.sleep(0.15)
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.3)
        try:
            pyperclip.copy(anterior)
        except Exception:
            pass

    def h_captura(self, v, a):
        import pyautogui
        carpeta = _carpeta_usuario("Pictures", "JARVIS")
        os.makedirs(carpeta, exist_ok=True)
        archivo = os.path.join(carpeta, f"captura_{datetime.datetime.now():%Y%m%d_%H%M%S}.png")
        pyautogui.screenshot(archivo)
        return ("decir", f"Captura guardada en Imágenes, carpeta JARVIS, {self.trato}.")

    def h_configuracion(self, v, a):
        os.startfile("ms-settings:" + AJUSTES.get(normalizar(v), ""))

    # ------------------------------------------------------------ información
    def h_hora(self, v, a):
        return ("decir", f"Son {hora_hablada(datetime.datetime.now())}, {self.trato}.")

    def h_fecha(self, v, a):
        h = datetime.date.today()
        return ("decir", f"Hoy es {DIAS[h.weekday()]} {h.day} de {MESES[h.month - 1]} de {h.year}.")

    def clima_texto(self, ciudad=""):
        ciudad = ciudad or self.cfg.get("ciudad", "Lima")
        g = requests.get("https://geocoding-api.open-meteo.com/v1/search",
                         params={"name": ciudad, "count": 1, "language": "es"}, timeout=6).json()
        if not g.get("results"):
            return None, None
        lugar = g["results"][0]
        d = requests.get("https://api.open-meteo.com/v1/forecast", params={
            "latitude": lugar["latitude"], "longitude": lugar["longitude"], "timezone": "auto", "forecast_days": 2,
            "current": "temperature_2m,apparent_temperature,relative_humidity_2m,weather_code,wind_speed_10m",
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,weather_code"},
                         timeout=6).json()
        c, dia = d["current"], d["daily"]
        estado = CLIMA.get(c["weather_code"], "")
        largo = (f"{lugar['name']}: {round(c['temperature_2m'])} °C, sensación {round(c['apparent_temperature'])} °C, "
                 f"{estado}, humedad {c['relative_humidity_2m']} %, viento {round(c['wind_speed_10m'])} km/h. "
                 f"Hoy: máxima {round(dia['temperature_2m_max'][0])} °C, mínima {round(dia['temperature_2m_min'][0])} °C, "
                 f"lluvia {dia['precipitation_probability_max'][0]} %. Mañana: {CLIMA.get(dia['weather_code'][1], '')}, "
                 f"máxima {round(dia['temperature_2m_max'][1])} °C, mínima {round(dia['temperature_2m_min'][1])} °C.")
        corto = f"{round(c['temperature_2m'])}°C  {estado.replace('con ', '').upper()}  ·  {lugar['name'].upper()}"
        return largo, corto

    def h_clima(self, v, a):
        largo, _ = self.clima_texto(v)
        return ("info", f"[clima] {largo}" if largo else f"[clima] No encontré la ciudad '{v}'.")

    def h_noticias(self, v, a):
        pais = self.cfg.get("pais_noticias", "PE")
        base = "https://news.google.com/rss"
        params = f"hl=es-419&gl={pais}&ceid={pais}:es-419"
        url = f"{base}/search?q={urllib.parse.quote(v)}&{params}" if v else f"{base}?{params}"
        xml = requests.get(url, headers=UA, timeout=8).content
        items = ET.fromstring(xml).findall(".//item")[:6]
        titulos = [re.sub(r"\s+-\s+[^-]+$", "", i.findtext("title", "")) + " (" + (i.findtext("source") or "") + ")" for i in items]
        if not titulos:
            return ("info", "[noticias] No encontré noticias.")
        return ("info", "[noticias] Titulares" + (f" sobre {v}" if v else "") + ":\n- " + "\n- ".join(titulos) +
                "\nResume los 3 o 4 más relevantes en pocas frases.")

    def h_wikipedia(self, v, a):
        api = "https://es.wikipedia.org/w/api.php"
        r = requests.get(api, params={"action": "query", "list": "search", "srsearch": v, "format": "json", "srlimit": 1},
                         headers=UA, timeout=8).json()
        hits = r.get("query", {}).get("search", [])
        if not hits:
            return ("info", f"[wikipedia] Sin resultados para '{v}'.")
        titulo = hits[0]["title"]
        s = requests.get("https://es.wikipedia.org/api/rest_v1/page/summary/" + urllib.parse.quote(titulo.replace(" ", "_")),
                         headers=UA, timeout=8).json()
        return ("info", f"[wikipedia] {titulo}: {s.get('extract', '')[:1500]}")

    def h_buscar_web(self, v, a):
        try:
            from ddgs import DDGS
            res = list(DDGS().text(v, region="es-es", max_results=5))
            if res:
                return ("info", "[buscar_web] Resultados:\n" + "\n".join(
                    f"- {r.get('title', '')}: {r.get('body', '')[:300]}" for r in res))
        except Exception as e:
            log.info("Búsqueda web directa no disponible (%s)", e)
        clase, texto = self.h_wikipedia(v, a)
        if "Sin resultados" in texto:
            self.h_buscar_google(v, a)
            return ("info", f"[buscar_web] No pude leer resultados; abrí la búsqueda de '{v}' en Google.")
        return (clase, texto)

    def h_divisa(self, v, a):
        nombres = {"dolar": "USD", "dolares": "USD", "sol": "PEN", "soles": "PEN", "euro": "EUR", "euros": "EUR",
                   "peso mexicano": "MXN", "peso colombiano": "COP", "peso argentino": "ARS", "peso chileno": "CLP",
                   "libra": "GBP", "yen": "JPY", "real": "BRL", "bitcoin": "BTC"}
        n = normalizar(v)
        for k, c in sorted(nombres.items(), key=lambda x: -len(x[0])):
            n = n.replace(k, c.lower())
        codigos = [c.upper() for c in re.findall(r"\b[a-z]{3}\b", n)] or ["USD"]
        de, a_ = codigos[0], (codigos[1] if len(codigos) > 1 else ("PEN" if codigos[0] != "PEN" else "USD"))
        d = requests.get(f"https://open.er-api.com/v6/latest/{de}", timeout=8).json()
        tasa = d.get("rates", {}).get(a_)
        if not tasa:
            return ("info", f"[divisa] No tengo la cotización {de}-{a_}.")
        return ("info", f"[divisa] 1 {de} = {tasa:.4f} {a_} (actualizado {d.get('time_last_update_utc', '')[:16]}).")

    def h_calcular(self, v, a):
        try:
            return ("decir", f"El resultado es {numero_hablado(calcular(v))}.")
        except Exception:
            return ("info", f"[calcular] No pude calcular '{v}'. Responde tú el cálculo.")

    def h_info_sistema(self, v, a):
        import psutil
        ram = psutil.virtual_memory()
        disco = psutil.disk_usage(os.environ.get("SystemDrive", "C:") + "\\" if ES_WINDOWS else "/")
        bat = psutil.sensors_battery()
        encendido = datetime.timedelta(seconds=int(time.time() - psutil.boot_time()))
        partes = [f"CPU {psutil.cpu_percent(interval=0.5):.0f} %",
                  f"RAM {ram.percent:.0f} % ({ram.used / 1024 ** 3:.1f} de {ram.total / 1024 ** 3:.1f} GB)",
                  f"disco libre {disco.free / 1024 ** 3:.0f} GB de {disco.total / 1024 ** 3:.0f} GB",
                  f"encendida hace {encendido}"]
        if bat:
            partes.append(f"batería {bat.percent:.0f} % {'cargando' if bat.power_plugged else 'sin cargador'}")
        return ("info", "[info_sistema] " + ", ".join(partes))

    def h_portapapeles(self, v, a):
        import pyperclip
        t = (pyperclip.paste() or "").strip()
        return ("info", f"[portapapeles] {t[:3000]}" if t else "[portapapeles] El portapapeles está vacío.")

    def h_ver_pantalla(self, v, a):
        import pyautogui
        archivo = os.path.join(DATOS, "pantalla.png")
        img = pyautogui.screenshot()
        img.thumbnail((1280, 1280))
        img.save(archivo)
        hud = getattr(self.n, "hud", None)
        if hud:
            hud.estado("PROCESANDO", "Analizando la pantalla...")
        desc = self.n.cerebro.ver(archivo, v)
        if desc is None:
            return ("info", "[ver_pantalla] El módulo de visión necesita la clave gratuita de Gemini. Dile al usuario "
                            "que la agregue con clic derecho en el reactor, opción Clave de Gemini.")
        return ("info", f"[ver_pantalla] Descripción de la pantalla (si está en inglés, tradúcela y resume): {desc[:2500]}")

    # ------------------------------------------------------------ productividad
    def h_recordatorio(self, v, a):
        cuando = calcular_momento(a)
        if not cuando:
            return ("info", "[recordatorio] Falta indicar cuándo. Pregunta al usuario para cuándo lo quiere.")
        self.recordatorios.agregar(v or "Recordatorio", cuando)

    def h_alarma(self, v, a):
        return self.h_recordatorio(v or "Alarma", a)

    def h_temporizador(self, v, a):
        return self.h_recordatorio(v or "El temporizador ha terminado", a)

    def h_listar_recordatorios(self, v, a):
        p = self.recordatorios.pendientes()
        if not p:
            return ("info", "[recordatorios] No hay recordatorios pendientes.")
        return ("info", "[recordatorios]\n" + "\n".join(
            f"- {r['texto']}: {datetime.datetime.fromisoformat(r['cuando']):%d/%m %H:%M}" for r in p[:10]))

    def h_cancelar_recordatorios(self, v, a):
        self.recordatorios.cancelar_todos()

    def _lista(self, nombre):
        n = normalizar(nombre) or "notas"
        n = {"tarea": "tareas", "pendientes": "tareas", "compra": "compras", "nota": "notas",
             "lista de compras": "compras", "lista de tareas": "tareas"}.get(n, n)
        listas = self.n.alm_listas.datos
        listas.setdefault(n, [])
        return n, listas[n]

    def h_anotar(self, v, a):
        n, lista = self._lista(a.get("lista", "notas"))
        lista.append(v)
        self.n.alm_listas.guardar()

    def h_leer_lista(self, v, a):
        n, lista = self._lista(v or a.get("lista", "notas"))
        return ("info", f"[lista {n}] " + ("vacía." if not lista else "; ".join(lista)))

    def h_quitar_de_lista(self, v, a):
        n, lista = self._lista(a.get("lista", "tareas"))
        cerca = difflib.get_close_matches(normalizar(v), [normalizar(x) for x in lista], n=1, cutoff=0.5)
        if cerca:
            lista.pop([normalizar(x) for x in lista].index(cerca[0]))
            self.n.alm_listas.guardar()
        else:
            return ("decir", f"No encuentro eso en la lista de {n}.")

    def h_vaciar_lista(self, v, a):
        n, lista = self._lista(v)
        if lista and self.n.confirmar(f"¿Borro los {len(lista)} elementos de la lista de {n}?"):
            lista.clear(); self.n.alm_listas.guardar()
            return ("decir", "Lista vaciada.")
        return ("decir", "Cancelado.")

    def h_crear_nota(self, v, a):
        escritorio = _carpeta_usuario("Desktop")
        if not os.path.isdir(escritorio):
            escritorio = _carpeta_usuario("OneDrive", "Desktop")
        archivo = os.path.join(escritorio if os.path.isdir(escritorio) else DATOS,
                               f"Nota JARVIS {datetime.datetime.now():%Y-%m-%d %H%M}.txt")
        with open(archivo, "w", encoding="utf-8") as f:
            f.write(v)
        os.startfile(archivo)

    def h_correo(self, v, a):
        para, asunto = a.get("para", ""), a.get("asunto", "")
        if self.cfg.get("correo") == "gmail":
            webbrowser.open("https://mail.google.com/mail/?view=cm&fs=1&" + urllib.parse.urlencode(
                {"to": para, "su": asunto, "body": v}))
        else:
            webbrowser.open(f"mailto:{para}?" + urllib.parse.urlencode({"subject": asunto, "body": v}, quote_via=urllib.parse.quote))
        return ("decir", "El correo está listo. Revíselo y presione enviar cuando guste.")

    def h_whatsapp(self, v, a):
        import pyautogui
        contactos = self.cfg.get("contactos", {})
        claves = {normalizar(k): k for k in contactos}
        quien = normalizar(a.get("contacto", ""))
        cerca = difflib.get_close_matches(quien, list(claves), n=1, cutoff=0.6) if quien else []
        tel = re.sub(r"\D", "", contactos[claves[cerca[0]]]) if cerca else ""
        texto = urllib.parse.quote(v)
        try:
            os.startfile(f"whatsapp://send?phone={tel}&text={texto}" if tel else f"whatsapp://send?text={texto}")
        except Exception:
            webbrowser.open(f"https://web.whatsapp.com/send?phone={tel}&text={texto}")
        if not tel:
            return ("decir", f"No tengo a {a.get('contacto', 'esa persona')} en mis contactos. Le dejé el mensaje listo "
                             "para que elija el chat. Puede agregar contactos en mi configuración.")
        time.sleep(4)
        if self.n.confirmar(f"El mensaje para {a.get('contacto')} está listo. ¿Lo envío?"):
            pyautogui.press("enter")
            return ("decir", "Mensaje enviado.")
        return ("decir", "Lo dejé escrito sin enviar.")

    # ------------------------------------------------------------ memoria y aprendizaje
    def h_recordar_dato(self, v, a):
        mem = self.n.alm_memoria
        if v and v not in mem.datos:
            mem.datos.append(v)
            mem.datos[:] = mem.datos[-60:]
            mem.guardar()

    def h_olvidar_dato(self, v, a):
        mem = self.n.alm_memoria
        n = normalizar(v)
        antes = len(mem.datos)
        mem.datos[:] = [d for d in mem.datos if not (n and (n in normalizar(d) or
                        difflib.SequenceMatcher(None, n, normalizar(d)).ratio() > 0.6))]
        mem.guardar()
        if antes == len(mem.datos):
            return ("decir", "No tenía ese dato en mi memoria.")

    def h_aprender(self, v, a):
        frase = a.get("frase") or v
        acciones = a.get("acciones")
        if isinstance(acciones, str):
            try:
                acciones = json.loads(acciones)
            except Exception:
                acciones = None
        if not frase or not isinstance(acciones, list) or not acciones:
            return ("info", "[aprender] Faltan la frase o las acciones. Pide al usuario que explique qué debe hacer ese comando.")
        self.n.alm_comandos.datos[str(frase).lower()] = acciones
        self.n.alm_comandos.guardar()

    def h_rutina(self, v, a):
        rutinas = self.cfg.get("rutinas", {})
        claves = {normalizar(k): k for k in rutinas}
        aprendidos = {normalizar(k): k for k in self.n.alm_comandos.datos}
        cerca = difflib.get_close_matches(normalizar(v), list(claves), n=1, cutoff=0.75)
        if cerca:
            pasos = rutinas[claves[cerca[0]]]
        else:
            cerca = difflib.get_close_matches(normalizar(v), list(aprendidos), n=1, cutoff=0.75)
            if not cerca:
                return ("decir", f"No tengo una rutina llamada {v}. Puede enseñarme una cuando quiera.")
            pasos = self.n.alm_comandos.datos[aprendidos[cerca[0]]]
        salida = []
        for paso in pasos:
            clase, texto = self.ejecutar(paso)
            if clase in ("decir", "info") and texto:
                salida.append(texto)
            time.sleep(0.6)
        if salida:
            return ("info", "\n".join(salida))

    # ------------------------------------------------------------ sistema
    def h_comando(self, v, a):
        if PELIGRO.search(v) and not self.n.confirmar("Ese comando podría modificar o borrar cosas importantes. ¿Lo ejecuto?"):
            return ("decir", "Cancelado. Más vale prevenir, " + self.trato + ".")
        r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command",
                            "[Console]::OutputEncoding=[System.Text.Encoding]::UTF8; " + v],
                           capture_output=True, timeout=90, creationflags=SIN_VENTANA)
        salida = (r.stdout.decode("utf-8", "ignore") or r.stderr.decode("utf-8", "ignore")).strip()
        return ("info", f"[comando] {salida[:2500] if salida else 'Ejecutado correctamente, sin salida.'}")

    def h_apagar(self, v, a):
        if self.n.confirmar(f"¿Confirma que apago el equipo, {self.trato}?"):
            self.n.decir("Apagando. Hasta pronto.")
            os.system("shutdown /s /t 3")
        else:
            return ("decir", "Cancelado.")

    def h_reiniciar(self, v, a):
        if self.n.confirmar(f"¿Confirma que reinicio el equipo, {self.trato}?"):
            self.n.decir("Reiniciando. Nos vemos en un momento.")
            os.system("shutdown /r /t 3")
        else:
            return ("decir", "Cancelado.")

    def h_cerrar_sesion(self, v, a):
        if self.n.confirmar("¿Cierro la sesión de Windows?"):
            os.system("shutdown /l")
        else:
            return ("decir", "Cancelado.")

    def h_suspender(self, v, a):
        os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")

    def h_bloquear(self, v, a):
        import ctypes
        ctypes.windll.user32.LockWorkStation()

    def h_modo(self, v, a):
        self.n.poner_modo("silencio" if "silen" in normalizar(v) or "pausa" in normalizar(v) else "activo")

    def h_salir(self, v, a):
        return ("salir", "")
