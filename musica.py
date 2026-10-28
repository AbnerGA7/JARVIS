# -*- coding: utf-8 -*-
"""
Música en Spotify (la app de escritorio) sin cuentas de desarrollador:
abre Spotify, usa la búsqueda rápida (Ctrl+K), da play y comprueba que de verdad esté sonando
mirando el título de la ventana (cuando suena una canción, Spotify se titula «Artista - Canción»).
"""
import os, time
import requests
from config import log, ES_WINDOWS

VIDEO = ("video", "trailer", "tráiler", "tutorial", "como hacer", "cómo hacer", "receta", "gameplay", "en vivo",
         "pelicula", "película", "capitulo", "capítulo", "documental", "noticias", "clip", "entrevista")


def parece_video(consulta):
    c = consulta.lower()
    return any(p in c for p in VIDEO)


def ventanas():
    """[(hwnd, título, área)] de las ventanas visibles de Spotify."""
    if not ES_WINDOWS:
        return []
    import ctypes, ctypes.wintypes as wt, psutil
    pids = {p.pid for p in psutil.process_iter(["name"]) if (p.info.get("name") or "").lower() == "spotify.exe"}
    if not pids:
        return []
    u = ctypes.windll.user32
    encontradas = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)
    def cada(h, _):
        if u.IsWindowVisible(h):
            pid = wt.DWORD()
            u.GetWindowThreadProcessId(h, ctypes.byref(pid))
            n = u.GetWindowTextLengthW(h)
            if pid.value in pids and n:
                buf = ctypes.create_unicode_buffer(n + 1)
                u.GetWindowTextW(h, buf, n + 1)
                r = wt.RECT()
                u.GetWindowRect(h, ctypes.byref(r))
                encontradas.append((h, buf.value, (r.right - r.left) * (r.bottom - r.top)))
        return True
    u.EnumWindows(cada, 0)
    return encontradas


def principal():
    v = ventanas()
    return max(v, key=lambda x: x[2]) if v else None


def titulo():
    p = principal()
    return p[1] if p else ""


def sonando(t):
    """Spotify pausado se titula «Spotify», «Spotify Free» o «Spotify Premium»; sonando, «Artista - Canción»."""
    return bool(t) and " - " in t and not t.lower().startswith("spotify")


def _enfocar(h):
    import ctypes
    u = ctypes.windll.user32
    if u.GetForegroundWindow() == h:
        return
    u.ShowWindow(h, 9)                       # SW_RESTORE
    u.keybd_event(0x12, 0, 0, 0)             # un toque de Alt permite traer la ventana al frente
    u.keybd_event(0x12, 0, 2, 0)
    u.SetForegroundWindow(h)
    time.sleep(0.35)


def cancion_concreta(consulta):
    """«queen» → «Bohemian Rhapsody Queen» (catálogo público de iTunes, sin clave). Sirve cuando piden un artista."""
    try:
        r = requests.get("https://itunes.apple.com/search", timeout=6,
                         params={"term": consulta, "entity": "song", "limit": 1, "country": "MX"}).json()
        if r.get("results"):
            x = r["results"][0]
            return f"{x['trackName']} {x['artistName']}"
    except Exception as e:
        log.info("iTunes no respondió: %s", e)
    return None


def _buscar_y_dar_play(consulta, bajar=False):
    import pyautogui, pyperclip
    try:
        anterior = pyperclip.paste()
    except Exception:
        anterior = ""
    pyperclip.copy(consulta)
    pyautogui.hotkey("ctrl", "k")            # búsqueda rápida de Spotify
    time.sleep(0.7)
    pyautogui.hotkey("ctrl", "a")
    pyautogui.hotkey("ctrl", "v")
    time.sleep(1.8)                          # espera los resultados
    if bajar:
        pyautogui.press("down")
        time.sleep(0.2)
    pyautogui.press("enter")
    time.sleep(0.2)
    try:
        pyperclip.copy(anterior or "")
    except Exception:
        pass


def _esperar_cancion(antes, segundos=4.5):
    fin = time.time() + segundos
    while time.time() < fin:
        time.sleep(0.5)
        t = titulo()
        if sonando(t) and t != antes:
            return t
    return None


def reproducir(consulta):
    """Devuelve «Artista - Canción» si logró que suene, "" si Spotify abrió pero no pudo confirmar, None si no hay Spotify."""
    if not ES_WINDOWS:
        return None
    recien_abierto = not ventanas()
    try:
        os.startfile("spotify:")             # abre Spotify o lo trae al frente
    except OSError:
        return None
    fin = time.time() + 20
    while not principal() and time.time() < fin:
        time.sleep(0.5)
    p = principal()
    if not p:
        return None
    if recien_abierto:
        time.sleep(3.5)                      # deja que cargue la interfaz
    antes = p[1] if sonando(p[1]) else ""

    def intentos():
        yield consulta, False                # 1) lo que pediste tal cual (sirve para canciones y playlists)
        concreta = cancion_concreta(consulta)
        if concreta:                         # 2) si era un artista: una canción concreta suya
            yield concreta, False
            yield concreta, True             # 3) por si el primer resultado no venía seleccionado
    for q, bajar in intentos():
        p = principal()
        if not p:
            return None
        _enfocar(p[0])
        _buscar_y_dar_play(q, bajar)
        t = _esperar_cancion(antes)
        if t:
            log.info("Spotify: sonando %s", t)
            return t
    log.info("Spotify no confirmó la reproducción de %s", consulta)
    return ""
