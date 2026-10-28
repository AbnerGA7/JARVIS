# -*- coding: utf-8 -*-
"""Iniciar JARVIS automáticamente al encender la PC (registro de Windows del usuario, sin permisos de admin)."""
import os, sys
from config import log, ES_WINDOWS

CLAVE = r"Software\Microsoft\Windows\CurrentVersion\Run"
NOMBRE = "JARVIS"


def comando():
    """Cómo se lanza JARVIS: el .exe instalado, o pythonw + jarvis.py cuando se usa desde el código."""
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}" --inicio'
    pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    interprete = pythonw if os.path.exists(pythonw) else sys.executable
    script = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "jarvis.py"))
    return f'"{interprete}" "{script}" --inicio'


def activo():
    if not ES_WINDOWS:
        return False
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, CLAVE) as k:
            valor, _ = winreg.QueryValueEx(k, NOMBRE)
            return bool(valor)
    except OSError:
        return False


def activar():
    if not ES_WINDOWS:
        return False
    import winreg
    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, CLAVE) as k:
            winreg.SetValueEx(k, NOMBRE, 0, winreg.REG_SZ, comando())
        log.info("JARVIS se iniciará con Windows: %s", comando())
        return True
    except OSError as e:
        log.warning("No pude activar el inicio con Windows: %s", e)
        return False


def desactivar():
    if not ES_WINDOWS:
        return False
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, CLAVE, 0, winreg.KEY_SET_VALUE) as k:
            winreg.DeleteValue(k, NOMBRE)
        log.info("Inicio con Windows desactivado")
        return True
    except OSError:
        return True
