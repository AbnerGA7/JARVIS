# -*- mode: python ; coding: utf-8 -*-
# Receta de PyInstaller para empaquetar J.A.R.V.I.S. (la usa compilar_exe.bat)
from PyInstaller.utils.hooks import collect_all

datas = [("jarvis.ico", "."), ("datos", "datos")]
binaries = []
hiddenimports = ["pyttsx3.drivers", "pyttsx3.drivers.sapi5", "pystray._win32", "comtypes.stream",
                 "win32timezone", "PIL._tkinter_finder", "audio", "keyboard", "pyperclip", "pycaw.pycaw"]

for paquete in ["edge_tts", "speech_recognition", "pystray", "screen_brightness_control", "pycaw",
                "ddgs", "certifi", "sounddevice", "_sounddevice_data", "pygame", "comtypes", "keyboard"]:
    try:
        d, b, h = collect_all(paquete)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception:
        pass

a = Analysis(
    ["jarvis.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["matplotlib", "scipy", "pandas", "PyQt5", "PyQt6", "PySide6", "IPython", "notebook", "torch"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="JARVIS",
    icon="jarvis.ico",
    console=False,
    upx=False,
    version=None,
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="JARVIS")
