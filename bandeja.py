# -*- coding: utf-8 -*-
"""Icono en la bandeja de Windows (junto al reloj) y atajos de teclado globales."""
import threading
from config import log


def iniciar_bandeja(icono_ruta, opciones):
    """opciones: lista de (texto o función que devuelve texto, función)"""
    try:
        import pystray
        from PIL import Image
        imagen = Image.open(icono_ruta)
        items = []
        for texto, fn in opciones:
            if texto == "-":
                items.append(pystray.Menu.SEPARATOR)
            else:
                items.append(pystray.MenuItem((lambda t: (lambda item: t()))(texto) if callable(texto) else texto,
                                              (lambda f: (lambda icon, item: f()))(fn),
                                              default=(texto == "Hablar con JARVIS")))
        icono = pystray.Icon("JARVIS", imagen, "J.A.R.V.I.S.", pystray.Menu(*items))
        icono.run_detached()
        return icono
    except Exception as e:
        log.warning("Sin icono de bandeja: %s", e)
        return None


def iniciar_atajos(cfg, activar, callar):
    try:
        import keyboard
        keyboard.add_hotkey(cfg.get("atajo_activar", "ctrl+alt+j"), lambda: threading.Thread(target=activar, daemon=True).start())
        keyboard.add_hotkey(cfg.get("atajo_callar", "ctrl+alt+s"), callar)
        log.info("Atajos: %s para hablar, %s para callar", cfg.get("atajo_activar"), cfg.get("atajo_callar"))
    except Exception as e:
        log.warning("Sin atajos de teclado: %s", e)
