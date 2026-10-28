# -*- coding: utf-8 -*-
"""Actualizaciones automáticas: busca la última versión publicada en GitHub y la instala con un clic."""
import os, re, sys, time, tempfile, subprocess
import requests
from config import log, VERSION

REPO = "AbnerGA7/JARVIS"
API = f"https://api.github.com/repos/{REPO}/releases/latest"


def numero(v):
    return tuple(int(x) for x in re.findall(r"\d+", str(v))[:3]) or (0,)


def instalado():
    """True cuando JARVIS corre desde el .exe instalado (las actualizaciones solo aplican ahí)."""
    return bool(getattr(sys, "frozen", False))


def buscar():
    """Devuelve {"version", "url", "notas", "tamano"} si hay una versión más nueva; si no, None."""
    try:
        r = requests.get(API, headers={"Accept": "application/vnd.github+json"}, timeout=10)
        if r.status_code != 200:
            return None
        d = r.json()
        version = d.get("tag_name", "").lstrip("vV")
        if numero(version) <= numero(VERSION):
            return None
        activo = next((a for a in d.get("assets", []) if a.get("name", "").lower().endswith(".exe")), None)
        if not activo:
            return None
        notas = re.sub(r"[#*`>]", "", d.get("body") or "")
        notas = "\n".join(l.strip() for l in notas.splitlines() if l.strip().startswith("-"))[:600]
        return {"version": version, "url": activo["browser_download_url"], "notas": notas,
                "tamano": activo.get("size", 0)}
    except Exception as e:
        log.info("No pude buscar actualizaciones: %s", e)
        return None


def descargar(info, progreso=None):
    destino = os.path.join(tempfile.gettempdir(), f"JARVIS_Setup_{info['version']}.exe")
    with requests.get(info["url"], stream=True, timeout=(10, 120)) as r:
        r.raise_for_status()
        total = int(r.headers.get("Content-Length") or info.get("tamano") or 0)
        hecho = 0
        with open(destino + ".part", "wb") as f:
            for trozo in r.iter_content(512 * 1024):
                f.write(trozo)
                hecho += len(trozo)
                if progreso and total:
                    progreso(hecho / total, f"DESCARGANDO JARVIS {info['version']}")
    os.replace(destino + ".part", destino)
    if progreso:
        progreso(None, "")
    return destino


def instalar(info, progreso=None):
    """Descarga el instalador y lo ejecuta en modo silencioso; el instalador cierra JARVIS y lo vuelve a abrir."""
    ruta = descargar(info, progreso)
    log.info("Instalando la versión %s", info["version"])
    subprocess.Popen([ruta, "/SILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/CLOSEAPPLICATIONS"],
                     creationflags=getattr(subprocess, "DETACHED_PROCESS", 0))
    time.sleep(1)
    os._exit(0)
