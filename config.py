# -*- coding: utf-8 -*-
"""Rutas, configuración y almacenamiento de datos de J.A.R.V.I.S."""
import os, sys, json, copy, threading, logging, unicodedata
from logging.handlers import RotatingFileHandler

VERSION = "2.3"

# Carpeta del programa (funciona también dentro del .exe)
BASE = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
# Carpeta de datos del usuario (escribible aunque el programa esté en Archivos de Programa)
DATOS = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "JARVIS")
os.makedirs(DATOS, exist_ok=True)
ICONO = os.path.join(BASE, "jarvis.ico")

ES_WINDOWS = os.name == "nt"
SIN_VENTANA = 0x08000000 if ES_WINDOWS else 0  # CREATE_NO_WINDOW


def ruta(nombre):
    return os.path.join(DATOS, nombre)


# ---------------------------------------------------------------- registro
def iniciar_log():
    log = logging.getLogger("jarvis")
    log.setLevel(logging.INFO)
    if not log.handlers:
        h = RotatingFileHandler(ruta("jarvis.log"), maxBytes=1_000_000, backupCount=2, encoding="utf-8")
        h.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        log.addHandler(h)
        c = logging.StreamHandler(sys.stdout) if sys.stdout else None
        if c:
            c.setFormatter(logging.Formatter("%(message)s"))
            log.addHandler(c)
    return log


log = iniciar_log()


# ---------------------------------------------------------------- utilidades
def normalizar(texto):
    """minúsculas, sin tildes ni signos: 'Abré Spotify!' -> 'abre spotify'"""
    t = unicodedata.normalize("NFD", str(texto).lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = "".join(c if c.isalnum() or c.isspace() else " " for c in t)
    return " ".join(t.split())


class Almacen:
    """Archivo JSON en la carpeta de datos, seguro entre hilos."""

    def __init__(self, nombre, defecto):
        self.archivo = ruta(nombre)
        self.lock = threading.RLock()
        self.datos = copy.deepcopy(defecto)
        try:
            with open(self.archivo, encoding="utf-8") as f:
                self.datos = json.load(f)
        except FileNotFoundError:
            self.guardar()
        except Exception as e:
            log.warning("No pude leer %s (%s), uso valores por defecto", nombre, e)

    def guardar(self):
        with self.lock:
            tmp = self.archivo + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.datos, f, ensure_ascii=False, indent=2)
            os.replace(tmp, self.archivo)


def _fusionar(defecto, usuario):
    """Agrega claves nuevas del defecto sin pisar lo que el usuario cambió."""
    for k, v in defecto.items():
        if k not in usuario:
            usuario[k] = copy.deepcopy(v)
        elif isinstance(v, dict) and isinstance(usuario[k], dict) and k not in ("contactos", "rutinas", "sitios", "alias_apps"):
            _fusionar(v, usuario[k])
    return usuario


def cargar_config():
    with open(os.path.join(BASE, "datos", "config.json"), encoding="utf-8") as f:
        defecto = json.load(f)
    archivo = ruta("config.json")
    usuario = {}
    if os.path.exists(archivo):
        try:
            with open(archivo, encoding="utf-8") as f:
                usuario = json.load(f)
        except Exception as e:
            log.error("config.json tiene un error (%s). Se usará la configuración por defecto.", e)
            usuario = {}
    cfg = _fusionar(defecto, usuario)
    try:
        with open(archivo, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
    return cfg


def guardar_config(cfg):
    """Guarda la configuración del usuario (por ejemplo, la clave de Groq)."""
    archivo = ruta("config.json")
    tmp = archivo + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    os.replace(tmp, archivo)


def cargar_entrenamiento():
    """Ejemplos base + ejemplos propios del usuario (mis_ejemplos.json)."""
    with open(os.path.join(BASE, "datos", "entrenamiento.json"), encoding="utf-8") as f:
        ejemplos = json.load(f)
    propios = ruta("mis_ejemplos.json")
    if not os.path.exists(propios):
        with open(propios, "w", encoding="utf-8") as f:
            json.dump([{"usuario": "pon mi playlist para estudiar",
                        "jarvis": {"respuesta": "Su música de estudio, señor.",
                                   "acciones": [{"tipo": "reproducir", "valor": "lofi para estudiar"}]}}],
                      f, ensure_ascii=False, indent=2)
    try:
        with open(propios, encoding="utf-8") as f:
            ejemplos += [dict(e, propio=True) for e in json.load(f) if isinstance(e, dict)]
    except Exception as e:
        log.warning("mis_ejemplos.json tiene un error: %s", e)
    return ejemplos
