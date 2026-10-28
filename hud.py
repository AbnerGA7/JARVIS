# -*- coding: utf-8 -*-
"""
Interfaz holográfica de J.A.R.V.I.S.
- ORBE: un pequeño reactor flotante en la esquina que late con tu voz (clic = hablar).
- PANEL: HUD completo estilo Iron Man que se despliega cuando Jarvis trabaja.
"""
import math, time, queue, random, datetime
import tkinter as tk

CLAVE = "#010203"          # color que Windows vuelve transparente
FONDO = "#04101a"
TEXTO = "#d9f6ff"
COLORES = {
    "EN LÍNEA": "#00d8ff", "EN ESPERA": "#00d8ff", "ESCUCHANDO": "#29ffd8", "RECONOCIENDO": "#29ffd8",
    "PROCESANDO": "#ffb000", "HABLANDO": "#00d8ff", "ALERTA": "#ff7a1a", "ERROR": "#ff3b3b",
    "SILENCIO": "#55707d", "DESCARGANDO": "#ffb000", "INICIANDO": "#00d8ff",
}
ACTIVOS = ("ESCUCHANDO", "RECONOCIENDO", "PROCESANDO", "HABLANDO", "ALERTA", "ERROR", "DESCARGANDO", "INICIANDO")
ARRANQUE = ["INICIALIZANDO NÚCLEO J.A.R.V.I.S.", "CALIBRANDO MICRÓFONO ........ OK", "SINTETIZADOR DE VOZ .......... OK",
            "ENLACE RED NEURONAL ......... OK", "MÓDULOS DE CONTROL .......... OK", "PROTOCOLOS DE SEGURIDAD ..... OK",
            "TODOS LOS SISTEMAS EN LÍNEA"]
W, H, ORB = 900, 540, 150


def _rgb(c):
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def mezclar(a, b, t):
    """Mezcla dos colores: t=0 -> a, t=1 -> b"""
    ra, rb = _rgb(a), _rgb(b)
    return "#%02x%02x%02x" % tuple(int(x + (y - x) * t) for x, y in zip(ra, rb))


class HUD:
    def __init__(self, cfg, icono=None, al_clic=None, menu=None):
        self.cfg = cfg
        self.al_clic = al_clic or (lambda: None)
        self.menu_acciones = menu or []
        self.icono = icono
        self.q = queue.Queue()
        self.nivel_mic = 0.0
        self.nivel_voz = 0.0
        self.silenciado = False

        self.root = tk.Tk()
        self.root.title("J.A.R.V.I.S.")
        if icono:
            try:
                self.root.iconbitmap(icono)
            except Exception:
                pass
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg=CLAVE)
        try:
            self.root.attributes("-transparentcolor", CLAVE)
        except Exception:
            pass
        self.k = max(1.0, self.root.winfo_fpixels("1i") / 96.0)
        self.sw, self.sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        self.cv = tk.Canvas(self.root, bg=CLAVE, highlightthickness=0)
        self.cv.pack(fill="both", expand=True)

        # estado
        self.estado_txt, self.detalle = "INICIANDO", ""
        self.t_estado = time.time()
        self.color = COLORES["INICIANDO"]
        self.registro = []           # [(quien, texto)]
        self.registro_cambio = True
        self.clima_txt = "SIN DATOS DE CLIMA"
        self.prog, self.prog_txt = None, ""
        self.stats = {"CPU": 0, "RAM": 0, "DISCO": 0, "BATERÍA": None}
        self._stats_t = 0
        self.t = 0
        self.t_arranque = time.time()
        self.modo = None
        self.pos_orbe = (int(self.sw - (ORB + 24) * self.k), int(self.sh - (ORB + 70) * self.k))
        self.ultimo_activo = time.time()
        self.alpha = 0.0
        self.barras = [0.0] * 40
        self._arrastre = None
        self.cambiar_modo("panel")

        self.cv.bind("<ButtonPress-1>", self._presionar)
        self.cv.bind("<B1-Motion>", self._mover)
        self.cv.bind("<ButtonRelease-1>", self._soltar)
        self.cv.bind("<Button-3>", self._menu)
        self._tick()

    # ================================================================ API (segura entre hilos)
    def estado(self, est, detalle=None):
        self.q.put(("estado", est, detalle))

    def registrar(self, quien, texto):
        self.q.put(("log", quien, texto))

    def clima(self, texto):
        self.q.put(("clima", texto, None))

    def progreso(self, p, texto=""):
        self.q.put(("prog", p, texto))

    def alerta(self, texto):
        self.q.put(("estado", "ALERTA", texto))
        self.q.put(("log", "ALERTA", texto))

    def silencio(self, activo):
        self.q.put(("silencio", activo, None))

    def mostrar_orbe(self, si=True):
        self.q.put(("orbe", si, None))

    def cerrar(self):
        self.q.put(("salir", None, None))

    def pedir_clave(self, error=None):
        """Muestra la ventana para pegar la clave de Groq y espera. Devuelve la clave o None si se cancela."""
        import threading
        listo, caja = threading.Event(), {}
        self.q.put(("dialogo", (listo, caja), error))
        listo.wait()
        return caja.get("clave")

    def run(self):
        self.root.mainloop()

    # ================================================================ ventana
    def S(self, v):
        return v * self.k

    def cambiar_modo(self, modo):
        if modo == self.modo:
            return
        self.modo = modo
        k = self.k
        if modo == "oculto":
            self.root.withdraw()
            return
        self.root.deiconify()
        if modo == "panel":
            w, h = int(W * k), int(H * k)
            if self.cfg.get("hud_posicion") == "centro":
                x, y = (self.sw - w) // 2, (self.sh - h) // 2
            else:
                x, y = self.sw - w - int(24 * k), max(0, (self.sh - h) // 2 - int(20 * k))
        else:
            w = h = int(ORB * k)
            x, y = self.pos_orbe
        self.root.geometry(f"{w}x{h}+{x}+{y}")
        self.cv.config(width=w, height=h)
        self.registro_cambio = True
        self._dibujar_fijo()

    def _presionar(self, e):
        self._arrastre = (e.x_root, e.y_root, self.root.winfo_x(), self.root.winfo_y(), False)

    def _mover(self, e):
        if not self._arrastre:
            return
        x0, y0, wx, wy, _ = self._arrastre
        dx, dy = e.x_root - x0, e.y_root - y0
        if abs(dx) + abs(dy) > 4:
            self._arrastre = (x0, y0, wx, wy, True)
            self.root.geometry(f"+{wx + dx}+{wy + dy}")

    def _soltar(self, e):
        if self._arrastre is None:
            return
        if self._arrastre[4]:
            if self.modo == "orbe":
                self.pos_orbe = (self.root.winfo_x(), self.root.winfo_y())
        else:
            self.al_clic()
        self._arrastre = None

    def _menu(self, e):
        m = tk.Menu(self.root, tearoff=0, bg=FONDO, fg=TEXTO, activebackground=self.color,
                    activeforeground="#000000", font=("Segoe UI", 10))
        for etiqueta, fn in self.menu_acciones:
            if etiqueta == "-":
                m.add_separator()
            else:
                m.add_command(label=etiqueta() if callable(etiqueta) else etiqueta, command=fn)
        m.tk_popup(e.x_root, e.y_root)

    # ================================================================ bucle
    def _procesar_cola(self):
        while True:
            try:
                tipo, a, b = self.q.get_nowait()
            except queue.Empty:
                return
            if tipo == "salir":
                self.root.destroy()
                raise SystemExit
            if tipo == "estado":
                if self.silenciado and a in ("EN ESPERA", "EN LÍNEA"):
                    a = "SILENCIO"
                self.estado_txt = a
                self.t_estado = time.time()
                if b is not None:
                    self.detalle = b
                nuevo = COLORES.get(a, "#00d8ff")
                if nuevo != self.color:
                    self.color = nuevo
                    self._dibujar_fijo()
                if a in ACTIVOS and a not in ("ALERTA", "ERROR"):
                    self.ultimo_activo = time.time()
            elif tipo == "log":
                self.registro.append((a, b))
                self.registro = self.registro[-8:]
                self.registro_cambio = True
            elif tipo == "clima":
                self.clima_txt = a
            elif tipo == "prog":
                self.prog, self.prog_txt = a, b
                self.ultimo_activo = time.time()
            elif tipo == "silencio":
                self.silenciado = a
                self.q.put(("estado", "SILENCIO" if a else "EN ESPERA", None))
            elif tipo == "dialogo":
                self._dialogo_clave(*a, error=b)
            elif tipo == "orbe":
                self.cfg["mostrar_orbe"] = a
                if self.modo == "orbe" and not a:
                    self.cambiar_modo("oculto")

    def _tick(self):
        try:
            self._procesar_cola()
        except SystemExit:
            return
        ahora = time.time()
        arrancando = ahora - self.t_arranque < 4.2
        aviso_viejo = self.estado_txt in ("ALERTA", "ERROR") and ahora - self.t_estado > 15
        activo = arrancando or (self.estado_txt in ACTIVOS and not aviso_viejo) or self.prog is not None or \
            ahora - self.ultimo_activo < float(self.cfg.get("hud_segundos_visible", 8))
        objetivo = "panel" if activo else ("orbe" if self.cfg.get("mostrar_orbe", True) else "oculto")
        if objetivo != self.modo:
            self.alpha = 0.0
            self.cambiar_modo(objetivo)
        if self.modo != "oculto":
            self.alpha += (0.96 - self.alpha) * 0.18
            try:
                self.root.attributes("-alpha", round(self.alpha, 3))
            except Exception:
                pass
            if self.modo == "panel":
                self._actualizar_stats(ahora)
                self._dibujar_panel(ahora)
            else:
                self._dibujar_orbe()
        self.t += 1
        self.root.after(33, self._tick)

    def _actualizar_stats(self, ahora):
        if ahora - self._stats_t < 1.5:
            return
        self._stats_t = ahora
        try:
            import psutil
            self.stats["CPU"] = psutil.cpu_percent(interval=None)
            self.stats["RAM"] = psutil.virtual_memory().percent
            import os
            self.stats["DISCO"] = psutil.disk_usage(os.environ.get("SystemDrive", "C:") + "\\" if os.name == "nt" else "/").percent
            b = psutil.sensors_battery()
            self.stats["BATERÍA"] = b.percent if b else None
        except Exception:
            pass

    # ================================================================ ventana de la clave
    def _dialogo_clave(self, listo, caja, error=None):
        import webbrowser
        c = COLORES["EN LÍNEA"]
        tenue = mezclar(c, FONDO, 0.55)
        d = tk.Toplevel(self.root)
        d.title("J.A.R.V.I.S. — Núcleo en la nube")
        try:
            if self.icono:
                d.iconbitmap(self.icono)
        except Exception:
            pass
        d.configure(bg=FONDO, highlightthickness=2, highlightbackground=c)
        d.attributes("-topmost", True)
        d.resizable(False, False)
        cuerpo = tk.Frame(d, bg=FONDO, padx=28, pady=22)
        cuerpo.pack(fill="both", expand=True)
        tk.Label(cuerpo, text="◤ ACTIVAR NÚCLEO EN LA NUBE", fg=c, bg=FONDO,
                 font=("Consolas", 14, "bold")).pack(anchor="w")
        tk.Label(cuerpo, text="Groq · gratis · ultrarrápido · no usa tu tarjeta gráfica", fg=tenue, bg=FONDO,
                 font=("Consolas", 9)).pack(anchor="w", pady=(2, 14))
        pasos = ("1.  Abre Groq con el botón de abajo e inicia sesión (con Google es un clic).\n"
                 "2.  Pulsa  «Create API Key», ponle de nombre JARVIS y copia la clave.\n"
                 "3.  Pégala aquí (Ctrl+V) y pulsa CONECTAR.")
        tk.Label(cuerpo, text=pasos, fg=TEXTO, bg=FONDO, justify="left", font=("Segoe UI", 10)).pack(anchor="w")
        tk.Button(cuerpo, text="ABRIR GROQ  ↗", command=lambda: webbrowser.open("https://console.groq.com/keys"),
                  bg=FONDO, fg=c, activebackground=c, activeforeground="#000000", relief="flat", bd=0,
                  highlightthickness=1, highlightbackground=c, font=("Consolas", 10, "bold"), padx=14, pady=6,
                  cursor="hand2").pack(anchor="w", pady=(12, 16))
        tk.Label(cuerpo, text="CLAVE DE GROQ", fg=c, bg=FONDO, font=("Consolas", 9, "bold")).pack(anchor="w")
        valor = tk.StringVar()
        entrada = tk.Entry(cuerpo, textvariable=valor, show="•", width=52, bg="#081c2a", fg=TEXTO,
                           insertbackground=c, relief="flat", font=("Consolas", 11),
                           highlightthickness=1, highlightbackground=tenue, highlightcolor=c)
        entrada.pack(fill="x", ipady=7, pady=(4, 6))
        aviso = tk.Label(cuerpo, text=error or "", fg="#ff7a1a", bg=FONDO, font=("Segoe UI", 9))
        aviso.pack(anchor="w")

        def terminar(clave):
            caja["clave"] = clave
            listo.set()
            d.destroy()

        def conectar(_=None):
            clave = valor.get().strip()
            if not clave:
                aviso.config(text="Pega primero tu clave")
                return
            terminar(clave)

        botones = tk.Frame(cuerpo, bg=FONDO)
        botones.pack(fill="x", pady=(14, 0))
        tk.Button(botones, text="CONECTAR", command=conectar, bg=c, fg="#000000", activebackground=TEXTO,
                  relief="flat", bd=0, font=("Consolas", 11, "bold"), padx=22, pady=7,
                  cursor="hand2").pack(side="right")
        tk.Button(botones, text="Ahora no", command=lambda: terminar(None), bg=FONDO, fg=tenue,
                  activebackground=FONDO, activeforeground=TEXTO, relief="flat", bd=0, font=("Segoe UI", 10),
                  cursor="hand2").pack(side="right", padx=14)
        entrada.bind("<Return>", conectar)
        d.protocol("WM_DELETE_WINDOW", lambda: terminar(None))
        d.update_idletasks()
        w, hh = d.winfo_reqwidth(), d.winfo_reqheight()
        d.geometry(f"+{(self.sw - w) // 2}+{(self.sh - hh) // 2}")
        d.lift()
        d.focus_force()
        entrada.focus_set()

    # ================================================================ dibujo
    def _poligono_panel(self, x1, y1, x2, y2, corte=14, tag="fijo", relleno=FONDO):
        S = self.S
        c = corte
        pts = [x1 + c, y1, x2, y1, x2, y2 - c, x2 - c, y2, x1, y2, x1, y1 + c]
        self.cv.create_polygon(*[S(p) for p in pts], fill=relleno, outline=mezclar(self.color, FONDO, 0.45),
                               width=max(1, S(1.2)), tags=tag)
        # esquinas brillantes
        for (x, y, dx, dy) in ((x2, y1, -1, 1), (x1, y2, 1, -1)):
            self.cv.create_line(S(x), S(y), S(x + 26 * dx), S(y), fill=self.color, width=S(2), tags=tag)
            self.cv.create_line(S(x), S(y), S(x), S(y + 26 * dy), fill=self.color, width=S(2), tags=tag)

    def _dibujar_fijo(self):
        cv, S = self.cv, self.S
        cv.delete("all")
        self.registro_cambio = True
        if self.modo != "panel":
            return
        c = self.color
        tenue = mezclar(c, FONDO, 0.6)
        # cabecera
        self._poligono_panel(20, 10, 880, 54, 12)
        cv.create_text(S(42), S(32), text="J.A.R.V.I.S.", anchor="w", fill=c, font=("Consolas", 18, "bold"), tags="fijo")
        cv.create_text(S(244), S(33), text="JUST A RATHER VERY INTELLIGENT SYSTEM", anchor="w", fill=tenue,
                       font=("Consolas", 8), tags="fijo")
        # paneles laterales
        self._poligono_panel(20, 66, 288, 440)
        cv.create_text(S(36), S(84), text="◤ REGISTRO DE COMANDOS", anchor="w", fill=c, font=("Consolas", 9, "bold"), tags="fijo")
        cv.create_line(S(36), S(96), S(272), S(96), fill=tenue, tags="fijo")
        self._poligono_panel(612, 66, 880, 440)
        cv.create_text(S(628), S(84), text="◤ ESTADO DEL SISTEMA", anchor="w", fill=c, font=("Consolas", 9, "bold"), tags="fijo")
        cv.create_line(S(628), S(96), S(864), S(96), fill=tenue, tags="fijo")
        cv.create_text(S(628), S(330), text="◤ ENTORNO", anchor="w", fill=c, font=("Consolas", 9, "bold"), tags="fijo")
        cv.create_line(S(628), S(342), S(864), S(342), fill=tenue, tags="fijo")
        # barra inferior
        self._poligono_panel(20, 452, 880, 528, 12)
        # anillo graduado fijo del reactor
        cx, cy = 450, 250
        for i in range(72):
            a = math.radians(i * 5)
            largo = 12 if i % 6 == 0 else 6
            r1, r2 = 162, 162 + largo
            cv.create_line(S(cx + r1 * math.cos(a)), S(cy + r1 * math.sin(a)), S(cx + r2 * math.cos(a)),
                           S(cy + r2 * math.sin(a)), fill=c if i % 6 == 0 else tenue, width=S(1.5), tags="fijo")
        for ang, txt in ((90, "090"), (270, "270")):
            a = math.radians(ang)
            cv.create_text(S(cx + 188 * math.cos(a)), S(cy + 188 * math.sin(a)), text=txt, fill=tenue,
                           font=("Consolas", 7), tags="fijo")

    def _dibujar_registro(self, arrancando, ahora):
        cv, S = self.cv, self.S
        cv.delete("log")
        if arrancando:
            n = min(len(ARRANQUE), int((ahora - self.t_arranque) / 0.5) + 1)
            for i, linea in enumerate(ARRANQUE[:n]):
                col = self.color if i in (0, len(ARRANQUE) - 1) else TEXTO
                cv.create_text(S(36), S(118 + i * 24), text="> " + linea, anchor="w", fill=col,
                               font=("Consolas", 8), tags="log")
            self.registro_cambio = True
            return
        y = 428
        for quien, texto in reversed(self.registro):
            col = self.color if quien == "JARVIS" else ("#ff9a3c" if quien == "ALERTA" else TEXTO)
            cuerpo = cv.create_text(S(36), S(y), text=texto, anchor="sw", fill=col if quien != "TÚ" else TEXTO,
                                    width=S(236), font=("Segoe UI", 9), tags="log")
            x1, y1, x2, y2 = cv.bbox(cuerpo)
            etiqueta_y = y1 / self.k - 4
            if etiqueta_y < 108:
                cv.delete(cuerpo)
                break
            cv.create_text(S(36), S(etiqueta_y), text=("▸ " + quien), anchor="sw", fill=col,
                           font=("Consolas", 8, "bold"), tags="log")
            y = etiqueta_y - 18
        self.registro_cambio = False

    def _dibujar_panel(self, ahora):
        cv, S, t, c = self.cv, self.S, self.t, self.color
        arrancando = ahora - self.t_arranque < 4.2
        if self.registro_cambio or arrancando:
            self._dibujar_registro(arrancando, ahora)
        cv.delete("dyn")
        tenue = mezclar(c, FONDO, 0.55)
        oscuro = mezclar(c, FONDO, 0.8)
        nivel = max(self.nivel_voz, self.nivel_mic * (1 if self.estado_txt in ("ESCUCHANDO", "RECONOCIENDO") else 0.35))
        rapidez = 3.2 if self.estado_txt in ("PROCESANDO", "DESCARGANDO") else 1.0
        armado = min(1.0, (ahora - self.t_arranque) / 2.5)
        cx, cy = 450, 250

        # reloj
        cv.create_text(S(862), S(32), text=datetime.datetime.now().strftime("%H:%M:%S  ·  %d/%m/%Y"), anchor="e",
                       fill=c, font=("Consolas", 12, "bold"), tags="dyn")

        # --- reactor
        def arco(r, inicio, ext, ancho, col):
            cv.create_arc(S(cx - r), S(cy - r), S(cx + r), S(cy + r), start=inicio, extent=ext * armado,
                          style="arc", outline=col, width=S(ancho), tags="dyn")

        for i in range(3):                                         # anillo exterior
            arco(148, t * 1.4 * rapidez + i * 120, 82, 7, c)
        for i in range(24):                                        # anillo punteado
            arco(130, -t * 0.9 * rapidez + i * 15, 8, 2, tenue if i % 4 else c)
        for i in range(10):                                        # bobinas del reactor
            arco(110, t * 0.3 + i * 36 + 4, 26, 12, oscuro if i % 2 else tenue)
        arco(92, -t * 2.2 * rapidez, 300, 1.5, tenue)
        if self.prog is not None:                                  # progreso de descarga
            arco(176, 90, -360 * self.prog, 4, "#ffb000")
        for i, vel in enumerate((2.0, -1.3, 3.1)):                 # satélites
            a = math.radians(t * vel * rapidez + i * 120)
            x, y = cx + 148 * math.cos(a), cy + 148 * math.sin(a)
            cv.create_oval(S(x - 4), S(y - 4), S(x + 4), S(y + 4), fill=TEXTO, outline="", tags="dyn")
        # triángulo interior
        pts = []
        for k in range(3):
            a = math.radians(-90 + 120 * k + t * 0.2)
            pts += [S(cx + 78 * math.cos(a)), S(cy + 78 * math.sin(a))]
        cv.create_polygon(*pts, outline=tenue, fill="", width=S(2), tags="dyn")
        # barrido de radar
        if self.estado_txt in ("PROCESANDO", "DESCARGANDO", "INICIANDO", "RECONOCIENDO"):
            a = math.radians(t * 7)
            cv.create_line(S(cx), S(cy), S(cx + 160 * math.cos(a)), S(cy + 160 * math.sin(a)), fill=c,
                           width=S(1.5), tags="dyn")
        # núcleo
        pulso = 34 + 6 * math.sin(t / 7) + nivel * 30
        for rr, col in ((pulso + 22, oscuro), (pulso + 12, mezclar(c, FONDO, 0.65)), (pulso + 4, tenue),
                        (pulso, mezclar(c, "#ffffff", 0.15)), (pulso * 0.62, mezclar(c, "#ffffff", 0.6)),
                        (pulso * 0.32, "#ffffff")):
            cv.create_oval(S(cx - rr), S(cy - rr), S(cx + rr), S(cy + rr), fill=col, outline="", tags="dyn")

        # --- estado del sistema
        y = 122
        for nombre, valor in self.stats.items():
            if valor is None:
                continue
            cv.create_text(S(628), S(y), text=nombre, anchor="w", fill=TEXTO, font=("Consolas", 9), tags="dyn")
            cv.create_text(S(864), S(y), text=f"{valor:.0f}%", anchor="e", fill=c, font=("Consolas", 9, "bold"), tags="dyn")
            cv.create_rectangle(S(628), S(y + 12), S(864), S(y + 20), outline=oscuro, fill=FONDO, tags="dyn")
            alerta = valor > 85 if nombre != "BATERÍA" else valor < 20
            cv.create_rectangle(S(628), S(y + 12), S(628 + 236 * valor / 100), S(y + 20),
                                outline="", fill="#ff5a3c" if alerta else c, tags="dyn")
            y += 46
        cv.create_text(S(628), S(362), text=self.clima_txt, anchor="nw", fill=TEXTO, width=S(236),
                       font=("Consolas", 9), tags="dyn")
        modo = "MICRÓFONO: SILENCIADO" if self.silenciado else "MICRÓFONO: ACTIVO"
        cv.create_text(S(628), S(412), text=modo, anchor="nw", fill=tenue, font=("Consolas", 8), tags="dyn")

        # --- barra inferior
        parpadeo = "●" if (t // 12) % 2 else "○"
        cv.create_text(S(42), S(478), text=f"{parpadeo}  {self.estado_txt}", anchor="w", fill=c,
                       font=("Consolas", 15, "bold"), tags="dyn")
        if self.prog is not None:
            sub = f"{self.prog_txt}  {self.prog * 100:.0f}%"
        else:
            sub = self.detalle or 'Di "Jarvis", aplaude dos veces o haz clic en el reactor'
        cv.create_text(S(42), S(506), text=sub[:70], anchor="w", fill=TEXTO, font=("Segoe UI", 9), tags="dyn")
        n = len(self.barras)
        for i in range(n):
            centro = 1 - abs(i - n / 2) / (n / 2)
            objetivo = nivel * (0.35 + 0.65 * random.random()) * (0.4 + 0.6 * centro) + 0.04 * (1 + math.sin(t / 5 + i / 2))
            self.barras[i] += (objetivo - self.barras[i]) * 0.45
            x = 470 + i * 9.8
            hgt = 2 + self.barras[i] * 30
            cv.create_rectangle(S(x), S(490 - hgt), S(x + 6), S(490 + hgt), fill=c if i % 3 else tenue,
                                outline="", tags="dyn")

    def _dibujar_orbe(self):
        cv, S, t, c = self.cv, self.S, self.t, self.color
        cv.delete("all")
        cx = cy = ORB / 2
        tenue = mezclar(c, FONDO, 0.55)
        oscuro = mezclar(c, FONDO, 0.8)
        nivel = max(self.nivel_voz, self.nivel_mic * 0.8)
        cv.create_oval(S(cx - 66), S(cy - 66), S(cx + 66), S(cy + 66), fill=FONDO, outline=oscuro, width=S(2))
        for i in range(3):
            a0 = t * 1.6 + i * 120
            cv.create_arc(S(cx - 58), S(cy - 58), S(cx + 58), S(cy + 58), start=a0, extent=80, style="arc",
                          outline=c, width=S(4))
        for i in range(12):
            cv.create_arc(S(cx - 46), S(cy - 46), S(cx + 46), S(cy + 46), start=-t * 1.1 + i * 30, extent=12,
                          style="arc", outline=tenue, width=S(2))
        pulso = 20 + 3 * math.sin(t / 8) + nivel * 18
        for rr, col in ((pulso + 10, oscuro), (pulso + 4, tenue), (pulso, mezclar(c, "#ffffff", 0.2)),
                        (pulso * 0.55, mezclar(c, "#ffffff", 0.65)), (pulso * 0.25, "#ffffff")):
            cv.create_oval(S(cx - rr), S(cy - rr), S(cx + rr), S(cy + rr), fill=col, outline="")
