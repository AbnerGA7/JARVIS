# -*- coding: utf-8 -*-
"""
Centro de control de J.A.R.V.I.S.: toda la configuración en una ventana, sin editar archivos.
Pestañas: General · Voz · Cerebro · Memoria · Celular · Acerca de.
"""
import os, threading, datetime
import tkinter as tk
from tkinter import ttk
from config import VERSION, DATOS, guardar_config
from hud import FONDO, TEXTO, COLORES, mezclar

C = COLORES["EN LÍNEA"]
PANEL = "#081c2a"
TENUE = mezclar(C, FONDO, 0.55)
VOCES = [
    ("es-MX-JorgeNeural", "Jorge · México (voz oficial de JARVIS)"), ("es-MX-DaliaNeural", "Dalia · México (mujer)"),
    ("es-PE-AlexNeural", "Alex · Perú (hombre)"), ("es-PE-CamilaNeural", "Camila · Perú (mujer)"),
    ("es-ES-AlvaroNeural", "Álvaro · España (hombre)"), ("es-ES-ElviraNeural", "Elvira · España (mujer)"),
    ("es-CO-GonzaloNeural", "Gonzalo · Colombia (hombre)"), ("es-CO-SalomeNeural", "Salomé · Colombia (mujer)"),
    ("es-AR-TomasNeural", "Tomás · Argentina (hombre)"), ("es-AR-ElenaNeural", "Elena · Argentina (mujer)"),
    ("es-US-AlonsoNeural", "Alonso · EE. UU. (hombre)"), ("es-US-PalomaNeural", "Paloma · EE. UU. (mujer)"),
    ("es-CL-LorenzoNeural", "Lorenzo · Chile (hombre)"), ("es-VE-SebastianNeural", "Sebastián · Venezuela (hombre)"),
]


def _numero(texto, defecto=0):
    try:
        return int(str(texto).replace("%", "").replace("Hz", "").replace("+", ""))
    except ValueError:
        return defecto


class CentroControl:
    def __init__(self, raiz, jarvis, icono=None):
        self.j = jarvis
        self.cfg = jarvis.cfg
        self.v = {}
        d = self.d = tk.Toplevel(raiz)
        d.title("J.A.R.V.I.S. — Centro de control")
        try:
            if icono:
                d.iconbitmap(icono)
        except Exception:
            pass
        d.configure(bg=FONDO, highlightthickness=2, highlightbackground=C)
        d.attributes("-topmost", True)
        d.resizable(False, False)
        self._estilos()
        cab = tk.Frame(d, bg=FONDO, padx=26, pady=16)
        cab.pack(fill="x")
        tk.Label(cab, text="◤ CENTRO DE CONTROL", fg=C, bg=FONDO, font=("Consolas", 15, "bold")).pack(side="left")
        tk.Label(cab, text=f"J.A.R.V.I.S. {VERSION}", fg=TENUE, bg=FONDO, font=("Consolas", 9)).pack(side="right")
        self.nb = ttk.Notebook(d, style="J.TNotebook")
        self.nb.pack(fill="both", expand=True, padx=18)
        for titulo, construir in (("General", self._general), ("Voz", self._voz), ("Cerebro", self._cerebro),
                                  ("Memoria", self._memoria), ("Celular", self._celular), ("Acerca de", self._acerca)):
            marco = tk.Frame(self.nb, bg=FONDO, padx=22, pady=18)
            self.nb.add(marco, text=f"  {titulo}  ")
            construir(marco)
        pie = tk.Frame(d, bg=FONDO, padx=22, pady=16)
        pie.pack(fill="x")
        self.estado = tk.Label(pie, text="", fg="#29ffd8", bg=FONDO, font=("Segoe UI", 9))
        self.estado.pack(side="left")
        self._boton(pie, "GUARDAR", self.guardar, lleno=True).pack(side="right")
        self._boton(pie, "Cerrar", d.destroy, discreto=True).pack(side="right", padx=12)
        d.update_idletasks()
        w, h = d.winfo_reqwidth(), d.winfo_reqheight()
        d.geometry(f"+{(d.winfo_screenwidth() - w) // 2}+{max(0, (d.winfo_screenheight() - h) // 2 - 20)}")
        d.lift()
        d.focus_force()

    # ------------------------------------------------------------ estilo y piezas
    def _estilos(self):
        e = ttk.Style(self.d)
        try:
            e.theme_use("clam")
        except Exception:
            pass
        e.configure("J.TNotebook", background=FONDO, borderwidth=0, tabmargins=(0, 0, 0, 0))
        e.configure("J.TNotebook.Tab", background=PANEL, foreground=TENUE, padding=(12, 7), borderwidth=0,
                    font=("Consolas", 10, "bold"))
        e.map("J.TNotebook.Tab", background=[("selected", C)], foreground=[("selected", "#000000")])
        e.configure("J.TCombobox", fieldbackground=PANEL, background=FONDO, foreground=TEXTO, arrowcolor=C,
                    bordercolor=TENUE, lightcolor=FONDO, darkcolor=FONDO, padding=5)
        e.map("J.TCombobox", fieldbackground=[("readonly", PANEL)], foreground=[("readonly", TEXTO)],
              selectbackground=[("readonly", PANEL)], selectforeground=[("readonly", TEXTO)])
        self.d.option_add("*TCombobox*Listbox.background", PANEL)
        self.d.option_add("*TCombobox*Listbox.foreground", TEXTO)
        self.d.option_add("*TCombobox*Listbox.selectBackground", C)
        self.d.option_add("*TCombobox*Listbox.selectForeground", "#000000")

    def _titulo(self, padre, texto):
        tk.Label(padre, text=texto, fg=C, bg=FONDO, font=("Consolas", 9, "bold")).pack(anchor="w", pady=(10, 4))

    def _nota(self, padre, texto):
        tk.Label(padre, text=texto, fg=TENUE, bg=FONDO, font=("Segoe UI", 9), justify="left", wraplength=560).pack(anchor="w")

    def _boton(self, padre, texto, accion, lleno=False, discreto=False):
        if lleno:
            return tk.Button(padre, text=texto, command=accion, bg=C, fg="#000000", activebackground=TEXTO, relief="flat",
                             bd=0, font=("Consolas", 10, "bold"), padx=18, pady=6, cursor="hand2")
        if discreto:
            return tk.Button(padre, text=texto, command=accion, bg=FONDO, fg=TENUE, activebackground=FONDO,
                             activeforeground=TEXTO, relief="flat", bd=0, font=("Segoe UI", 10), cursor="hand2")
        return tk.Button(padre, text=texto, command=accion, bg=FONDO, fg=C, activebackground=C, activeforeground="#000000",
                         relief="flat", bd=0, highlightthickness=1, highlightbackground=C, font=("Consolas", 9, "bold"),
                         padx=12, pady=5, cursor="hand2")

    def _campo(self, padre, etiqueta, clave, ancho=34):
        fila = tk.Frame(padre, bg=FONDO)
        fila.pack(fill="x", pady=3)
        tk.Label(fila, text=etiqueta, fg=TEXTO, bg=FONDO, font=("Segoe UI", 10), width=24, anchor="w").pack(side="left")
        var = tk.StringVar(value=str(self.cfg.get(clave, "")))
        tk.Entry(fila, textvariable=var, width=ancho, bg=PANEL, fg=TEXTO, insertbackground=C, relief="flat",
                 font=("Segoe UI", 10), highlightthickness=1, highlightbackground=TENUE, highlightcolor=C).pack(side="left", ipady=4)
        self.v[clave] = var
        return var

    def _casilla(self, padre, texto, clave, defecto=True):
        var = tk.BooleanVar(value=bool(self.cfg.get(clave, defecto)))
        tk.Checkbutton(padre, text=texto, variable=var, bg=FONDO, fg=TEXTO, selectcolor=PANEL, activebackground=FONDO,
                       activeforeground=C, font=("Segoe UI", 10), anchor="w", highlightthickness=0, bd=0).pack(anchor="w", pady=2)
        self.v[clave] = var
        return var

    def _deslizador(self, padre, etiqueta, desde, hasta, valor, sufijo=""):
        fila = tk.Frame(padre, bg=FONDO)
        fila.pack(fill="x", pady=3)
        tk.Label(fila, text=etiqueta, fg=TEXTO, bg=FONDO, font=("Segoe UI", 10), width=24, anchor="w").pack(side="left")
        var = tk.DoubleVar(value=valor)
        tk.Scale(fila, from_=desde, to=hasta, orient="horizontal", variable=var, bg=FONDO, fg=TEXTO, troughcolor=PANEL,
                 highlightthickness=0, activebackground=C, sliderrelief="flat", length=300, font=("Consolas", 8),
                 resolution=1 if isinstance(valor, int) else 0.05).pack(side="left")
        if sufijo:
            tk.Label(fila, text=sufijo, fg=TENUE, bg=FONDO, font=("Consolas", 9)).pack(side="left", padx=6)
        return var

    def _lista(self, padre, elementos, alto=6):
        marco = tk.Frame(padre, bg=FONDO)
        marco.pack(fill="x")
        lb = tk.Listbox(marco, height=alto, bg=PANEL, fg=TEXTO, selectbackground=C, selectforeground="#000000",
                        relief="flat", highlightthickness=1, highlightbackground=TENUE, font=("Segoe UI", 10),
                        activestyle="none", width=70)
        for e in elementos:
            lb.insert("end", e)
        lb.pack(side="left", fill="x", expand=True)
        return lb

    # ------------------------------------------------------------ pestañas
    def _general(self, m):
        self._titulo(m, "CÓMO TE TRATO")
        self._campo(m, "Tu nombre", "nombre_usuario")
        self._campo(m, "Cómo te llamo", "trato")
        self._campo(m, "Ciudad (clima)", "ciudad")
        self._campo(m, "País (noticias, ej. PE)", "pais_noticias", 8)
        self._titulo(m, "COMPORTAMIENTO")
        self.v["segundos_conversacion"] = self._deslizador(
            m, "Te sigo escuchando (s)", 0, 20, int(self.cfg.get("segundos_conversacion", 7)))
        self._casilla(m, "Iniciar JARVIS al encender la PC", "iniciar_con_windows")
        self._casilla(m, "Activarme con dos aplausos", "aplausos")
        self._casilla(m, "Mostrar el reactor flotante cuando estoy en espera", "mostrar_orbe")
        self._casilla(m, "Saludar al iniciar", "saludo_al_iniciar")
        fila = tk.Frame(m, bg=FONDO)
        fila.pack(fill="x", pady=(12, 0))
        self._boton(fila, "MICRÓFONO, PARLANTES Y APLAUSOS", self.j.abrir_ajustes_audio).pack(side="left")

    def _voz(self, m):
        self._titulo(m, "VOZ DE JARVIS")
        fila = tk.Frame(m, bg=FONDO)
        fila.pack(fill="x", pady=3)
        tk.Label(fila, text="Voz", fg=TEXTO, bg=FONDO, font=("Segoe UI", 10), width=24, anchor="w").pack(side="left")
        nombres = [n for _, n in VOCES]
        actual = next((n for k, n in VOCES if k == self.cfg.get("voz")), self.cfg.get("voz", nombres[0]))
        self.voz_var = tk.StringVar(value=actual)
        ttk.Combobox(fila, textvariable=self.voz_var, values=nombres, state="readonly", width=34, style="J.TCombobox",
                     font=("Segoe UI", 10)).pack(side="left")
        self.vel_var = self._deslizador(m, "Velocidad", -30, 40, _numero(self.cfg.get("velocidad_voz", "-4%"), -4), "%")
        self.tono_var = self._deslizador(m, "Tono", -20, 20, _numero(self.cfg.get("tono_voz", "-12Hz"), -12), "Hz")
        fila2 = tk.Frame(m, bg=FONDO)
        fila2.pack(fill="x", pady=(10, 0))
        self._boton(fila2, "▶ PROBAR VOZ", self._probar_voz).pack(side="left")
        self._boton(fila2, "🎩 VOZ DE MAYORDOMO", self._mayordomo).pack(side="left", padx=8)
        self._nota(m, "El celular usa esta misma voz (la pide a tu PC). Sin PC, usa la voz de Android más parecida.")
        self._titulo(m, "OÍDO")
        self.trans_var = tk.StringVar(value="Whisper (Groq) — más preciso" if self.cfg.get("transcriptor", "groq") == "groq"
                                      else "Google — básico")
        fila3 = tk.Frame(m, bg=FONDO)
        fila3.pack(fill="x", pady=3)
        tk.Label(fila3, text="Entender órdenes con", fg=TEXTO, bg=FONDO, font=("Segoe UI", 10), width=24, anchor="w").pack(side="left")
        ttk.Combobox(fila3, textvariable=self.trans_var, values=["Whisper (Groq) — más preciso", "Google — básico"],
                     state="readonly", width=34, style="J.TCombobox", font=("Segoe UI", 10)).pack(side="left")
        self._nota(m, "Para detectar «Jarvis» siempre se usa el reconocimiento básico; Whisper entiende mejor lo que pides "
                      "una vez que te escucho.")

    def _aplicar_voz(self):
        clave = next((k for k, n in VOCES if n == self.voz_var.get()), self.cfg.get("voz"))
        self.cfg["voz"] = clave
        self.cfg["velocidad_voz"] = f"{int(self.vel_var.get()):+d}%"
        self.cfg["tono_voz"] = f"{int(self.tono_var.get()):+d}Hz"
        self.cfg["transcriptor"] = "groq" if self.trans_var.get().startswith("Whisper") else "google"

    def _mayordomo(self):
        """Ajuste recomendado: voz masculina mexicana, pausada y grave, como el JARVIS del doblaje."""
        self.voz_var.set(next(n for k, n in VOCES if k == "es-MX-JorgeNeural"))
        self.vel_var.set(-4)
        self.tono_var.set(-12)
        self._probar_voz()

    def _probar_voz(self):
        self._aplicar_voz()
        frase = f"Así sonaré a partir de ahora, {self.cfg.get('trato', 'señor')}. Todos los sistemas en línea."
        threading.Thread(target=self.j.decir, args=(frase,), kwargs={"registrar": False}, daemon=True).start()

    def _cerebro(self, m):
        c = self.j.cerebro
        self._titulo(m, "NÚCLEO DE INTELIGENCIA")
        if c.motor == "groq":
            principal = f"● Groq · {c.groq_principal}   (respaldo: {c.groq_respaldo})"
        elif c.motor:
            principal = f"● {c.motor} · {c.modelo}"
        else:
            principal = "○ Desconectado — agrega tu clave de Groq"
        tk.Label(m, text=principal, fg="#29ffd8" if c.motor else "#ffb000", bg=FONDO, font=("Consolas", 10)).pack(anchor="w")
        tk.Label(m, text=(f"● Gemini · {c.modelo_gemini}   (respaldo y visión)" if c.modelo_gemini else
                          "○ Gemini sin configurar (opcional: respaldo y ver la pantalla)"),
                 fg="#29ffd8" if c.modelo_gemini else TENUE, bg=FONDO, font=("Consolas", 10)).pack(anchor="w", pady=(2, 0))
        whisper = c.modelo_whisper() if hasattr(c, "modelo_whisper") else None
        tk.Label(m, text=f"● Oído preciso · {whisper}" if whisper else "○ Oído preciso no disponible",
                 fg="#29ffd8" if whisper else TENUE, bg=FONDO, font=("Consolas", 10)).pack(anchor="w", pady=(2, 10))
        fila = tk.Frame(m, bg=FONDO)
        fila.pack(fill="x")
        self._boton(fila, "CLAVE DE GROQ", lambda: (self.d.destroy(), self.j.cambiar_clave())).pack(side="left")
        self._boton(fila, "CLAVE DE GEMINI", lambda: (self.d.destroy(), self.j.cambiar_clave_gemini())).pack(side="left", padx=8)
        self._titulo(m, "PERSONALIDAD")
        self.v["temperatura"] = self._deslizador(m, "Creatividad", 0.0, 1.2, float(self.cfg.get("temperatura", 0.4)))
        self._nota(m, "Más baja = respuestas precisas y serias. Más alta = más ingenio y variedad.")
        self._titulo(m, "ENTRENAMIENTO")
        fila2 = tk.Frame(m, bg=FONDO)
        fila2.pack(fill="x")
        self._boton(fila2, "EDITAR MIS EJEMPLOS", lambda: os.startfile(os.path.join(DATOS, "mis_ejemplos.json"))).pack(side="left")
        self._boton(fila2, "RECARGAR", self.j.recargar).pack(side="left", padx=8)

    def _memoria(self, m):
        self._titulo(m, "LO QUE RECUERDO DE TI")
        mem = self.j.alm_memoria
        lb_mem = self._lista(m, mem.datos, 5)
        self._boton(m, "OLVIDAR SELECCIONADO", lambda: self._borrar(lb_mem, mem.datos, mem)).pack(anchor="w", pady=(6, 0))
        self._titulo(m, "COMANDOS QUE ME ENSEÑASTE")
        cmds = self.j.alm_comandos
        claves = list(cmds.datos)
        lb_cmd = self._lista(m, [f"{k}  →  {', '.join(a.get('tipo', '?') for a in v)}" for k, v in cmds.datos.items()], 4)

        def borrar_cmd():
            sel = lb_cmd.curselection()
            if sel:
                cmds.datos.pop(claves.pop(sel[0]), None)
                cmds.guardar()
                lb_cmd.delete(sel[0])
        self._boton(m, "BORRAR COMANDO", borrar_cmd).pack(anchor="w", pady=(6, 0))
        self._titulo(m, "LISTAS")
        listas = self.j.alm_listas
        resumen = [f"{n}: {', '.join(v[:8]) or '(vacía)'}" for n, v in listas.datos.items()]
        self._lista(m, resumen, 3)

    def _borrar(self, lb, datos, almacen):
        sel = lb.curselection()
        if sel:
            datos.pop(sel[0])
            almacen.guardar()
            lb.delete(sel[0])

    def _celular(self, m):
        enlace = self.j.enlace
        self._titulo(m, "APP JARVIS PARA ANDROID")
        url = enlace.url_remota() if enlace.activo else None
        tk.Label(m, text=("● Enlace activo en la red local" if enlace.activo else "○ Enlace desactivado"),
                 fg="#29ffd8" if enlace.activo else TENUE, bg=FONDO, font=("Consolas", 10)).pack(anchor="w")
        tk.Label(m, text=("● Acceso por internet listo (datos móviles)" if url else "○ Acceso por internet preparándose..."),
                 fg="#29ffd8" if url else "#ffb000", bg=FONDO, font=("Consolas", 10)).pack(anchor="w", pady=(2, 8))
        self._casilla(m, "Permitir el acceso desde internet (datos móviles)", "acceso_remoto")
        self._casilla(m, "Compartir mi clave de Groq con el celular (modo sin PC)", "compartir_clave_con_celular")
        self._titulo(m, "CELULARES VINCULADOS")
        dispositivos = enlace.dispositivos.datos
        self._lista(m, [f"{v.get('nombre', 'Celular')}  ·  desde {v.get('desde', '')[:10]}" for v in dispositivos.values()]
                    or ["(ninguno)"], 4)
        fila = tk.Frame(m, bg=FONDO)
        fila.pack(fill="x", pady=(8, 0))
        self._boton(fila, "CONECTAR CELULAR", lambda: (self.d.destroy(), self.j.conectar_celular())).pack(side="left")
        self._boton(fila, "DESVINCULAR TODOS", lambda: (self.j.desvincular_celulares(), self.d.destroy())).pack(side="left", padx=8)
        self._nota(m, "Descarga la app: github.com/AbnerGA7/JARVIS-Android → Releases.")

    def _acerca(self, m):
        tk.Label(m, text="J.A.R.V.I.S.", fg=C, bg=FONDO, font=("Consolas", 22, "bold")).pack(anchor="w")
        tk.Label(m, text=f"Versión {VERSION} · Just A Rather Very Intelligent System", fg=TENUE, bg=FONDO,
                 font=("Consolas", 9)).pack(anchor="w", pady=(0, 14))
        act = self.j.actualizacion
        tk.Label(m, text=(f"⬆ Hay una versión nueva: {act['version']}" if act else "✓ Tienes la última versión conocida"),
                 fg="#ffb000" if act else "#29ffd8", bg=FONDO, font=("Segoe UI", 10, "bold")).pack(anchor="w")
        if act and act.get("notas"):
            self._nota(m, act["notas"])
        fila = tk.Frame(m, bg=FONDO)
        fila.pack(fill="x", pady=(10, 0))
        self._boton(fila, "ACTUALIZAR" if act else "BUSCAR ACTUALIZACIONES",
                    lambda: (self.d.destroy(), threading.Thread(target=self.j._menu_actualizar, daemon=True).start())).pack(side="left")
        self._boton(fila, "CARPETA DE DATOS", lambda: os.startfile(DATOS)).pack(side="left", padx=8)
        self._boton(fila, "VER REGISTRO", lambda: os.startfile(os.path.join(DATOS, "jarvis.log"))).pack(side="left")
        self._titulo(m, "PROYECTO")
        self._nota(m, "PC: github.com/AbnerGA7/JARVIS\nAndroid: github.com/AbnerGA7/JARVIS-Android\n"
                      f"Hecho por AbnerGA7 · {datetime.date.today().year}")

    # ------------------------------------------------------------ guardar
    def guardar(self):
        for clave, var in self.v.items():
            valor = var.get()
            if isinstance(var, tk.DoubleVar):
                valor = round(float(valor), 2) if clave == "temperatura" else int(valor)
            self.cfg[clave] = valor
        self._aplicar_voz()
        guardar_config(self.cfg)
        threading.Thread(target=self.j.aplicar_config, daemon=True).start()
        self.estado.config(text="✓ Guardado")
        self.d.after(1500, lambda: self.estado.winfo_exists() and self.estado.config(text=""))
