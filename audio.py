# -*- coding: utf-8 -*-
"""Micrófonos y parlantes: listarlos con nombres legibles y encontrar el que eligió el usuario."""
from config import log

PREDETERMINADO = "Predeterminado de Windows"


def _sd():
    import sounddevice as sd
    return sd


def listar_microfonos():
    """Devuelve [(nombre_guardado, nombre_para_mostrar)] de micrófonos utilizables.

    En Windows se abren por MME (acepta 16 kHz y convierte solo), pero MME corta los nombres a 31 letras;
    para mostrarlos se busca el nombre completo en WASAPI.
    """
    sd = _sd()
    try:
        dispositivos = sd.query_devices()
        apis = sd.query_hostapis()
    except Exception as e:
        log.warning("No pude listar micrófonos: %s", e)
        return []
    api_base = sd.default.hostapi if sd.default.hostapi is not None and sd.default.hostapi >= 0 else 0
    completos = [d["name"] for d in dispositivos if d["max_input_channels"] > 0
                 and "WASAPI" in apis[d["hostapi"]]["name"]]
    salida, vistos = [], set()
    for d in dispositivos:
        if d["hostapi"] != api_base or d["max_input_channels"] <= 0:
            continue
        nombre = d["name"]
        if nombre in vistos or "asignador de sonido" in nombre.lower() or "sound mapper" in nombre.lower():
            continue
        vistos.add(nombre)
        visible = next((c for c in completos if c.startswith(nombre.rstrip())), nombre)
        salida.append((nombre, visible))
    return salida


def indice_microfono(nombre):
    """Índice del micrófono guardado, o None para el predeterminado (o si ya no está conectado)."""
    if not nombre:
        return None
    sd = _sd()
    try:
        api_base = sd.default.hostapi if sd.default.hostapi is not None and sd.default.hostapi >= 0 else 0
        for i, d in enumerate(sd.query_devices()):
            if d["max_input_channels"] > 0 and d["hostapi"] == api_base and d["name"] == nombre:
                return i
        for i, d in enumerate(sd.query_devices()):
            if d["max_input_channels"] > 0 and d["name"].startswith(nombre[:25]):
                return i
    except Exception:
        pass
    log.warning("El micrófono '%s' no está conectado; uso el predeterminado", nombre)
    return None


def listar_parlantes():
    """Nombres de las salidas de audio (como las ve el reproductor de JARVIS)."""
    try:
        import pygame
        from pygame._sdl2 import audio as sdl_audio
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        return list(dict.fromkeys(sdl_audio.get_audio_device_names(False)))
    except Exception as e:
        log.warning("No pude listar parlantes: %s", e)
        return []
