# -*- coding: utf-8 -*-
"""
Cerebro de J.A.R.V.I.S. — IA en la nube con Groq (gratis y ultrarrápida) u Ollama local.
Personalidad + catálogo de acciones + ejemplos de entrenamiento + memoria a largo plazo.
"""
import os, re, json, time, shutil, base64, subprocess
import requests
from config import log, SIN_VENTANA, cargar_entrenamiento

OLLAMA = "http://127.0.0.1:11434"
GROQ = "https://api.groq.com/openai/v1"
# Groq cambia sus modelos seguido: JARVIS consulta cuáles tiene tu cuenta y elige en este orden
GROQ_PREFERIDOS = ("llama-3.3-70b-versatile", "openai/gpt-oss-120b", "moonshotai/kimi-k2-instruct",
                   "meta-llama/llama-4-maverick-17b-128e-instruct", "qwen/qwen3-32b",
                   "meta-llama/llama-4-scout-17b-16e-instruct", "openai/gpt-oss-20b", "llama-3.1-8b-instant")
GROQ_RAPIDOS = ("llama-3.1-8b-instant", "openai/gpt-oss-20b", "meta-llama/llama-4-scout-17b-16e-instruct",
                "qwen/qwen3-32b", "openai/gpt-oss-120b")
GEMINI = "https://generativelanguage.googleapis.com/v1beta"

# En la nube cada palabra cuenta para el límite gratis: se envían solo los ejemplos más didácticos
EJEMPLOS_NUBE = {
    "abre spotify y pon música de queen", "cierra chrome y abre youtube en edge", "cómo está el clima",
    "recuérdame en 20 minutos sacar la ropa de la lavadora", "anota que tengo que comprar pan y leche",
    "quién fue nikola tesla", "mándale un whatsapp a mamá diciendo que ya voy",
    "cuando te diga modo cine pausa todo, baja el brillo y abre netflix", "busca el archivo del informe de historia",
}

ACCIONES = """\
APPS Y WEB
- abrir_app: nombre de cualquier programa instalado ("spotify", "word", "steam", "calculadora")
- cerrar_app: nombre del programa a cerrar
- abrir_web: sitio conocido ("youtube", "gmail") o URL
- buscar_google: texto a buscar en Google
- buscar_youtube: texto a buscar en YouTube
- reproducir: canción, artista o video para reproducir de inmediato
- abrir_carpeta: descargas, documentos, escritorio, imágenes, música, videos, papelera, este equipo o una ruta
- buscar_archivo: nombre (o parte) de un archivo de la PC  [CONSULTA]
- abrir_archivo: ruta del archivo, o el número de un resultado de buscar_archivo
CONTROL DE LA PC
- volumen: "subir", "bajar", "silenciar", "activar" o un número 0-100
- brillo: "subir", "bajar" o un número 0-100
- media: "pausa", "siguiente" o "anterior"
- ventana: minimizar_todo, cambiar, maximizar, minimizar, cerrar, izquierda, derecha, vista_tareas
- teclas: atajo de teclado ("ctrl+c", "alt+tab", "ctrl+shift+esc")
- escribir: texto que se escribirá donde esté el cursor
- captura: (sin valor) guarda una captura de pantalla
- configuracion: wifi, bluetooth, sonido, pantalla, bateria, actualizaciones, apps, fondo, notificaciones
- ajustes_audio: (sin valor) abre la ventana para elegir el micrófono y los parlantes de JARVIS
- conectar_celular: (sin valor) muestra el PIN para vincular la app JARVIS del celular
INFORMACIÓN  [CONSULTA]
- hora / fecha: (sin valor)
- clima: ciudad (vacío = ciudad del usuario)
- noticias: tema (vacío = principales del día)
- wikipedia: tema
- buscar_web: pregunta sobre algo actual o que no sabes con seguridad
- divisa: par de monedas "USD-PEN", "EUR-USD"
- calcular: expresión matemática en Python ("(25*4)/3", "sqrt(144)", "15/100*300")
- info_sistema: (sin valor) CPU, RAM, batería, disco
- portapapeles: (sin valor) lee el texto copiado
- ver_pantalla: pregunta sobre lo que hay en la pantalla
PRODUCTIVIDAD
- recordatorio: valor=texto del aviso, y además "minutos": n  o  "hora": "HH:MM" (24 h)
- listar_recordatorios / cancelar_recordatorios: (sin valor)
- anotar: valor=texto, "lista": "notas" | "tareas" | "compras"
- leer_lista: notas | tareas | compras  [CONSULTA]
- quitar_de_lista: valor=texto, "lista": nombre
- vaciar_lista: nombre de la lista
- crear_nota: contenido de un archivo de texto que se abre en el escritorio
- correo: valor=mensaje, "para": correo, "asunto": asunto
- whatsapp: valor=mensaje, "contacto": nombre
MEMORIA Y APRENDIZAJE
- recordar_dato: dato sobre el usuario que debes recordar para siempre
- olvidar_dato: dato a olvidar
- aprender: "frase": orden del usuario, "acciones": [lista de acciones] (cuando te enseñe un comando nuevo)
- rutina: nombre de una rutina configurada
SISTEMA
- comando: comando de PowerShell (solo si ninguna otra acción sirve)  [CONSULTA]
- apagar / reiniciar / suspender / bloquear / cerrar_sesion: (sin valor)
- modo: "silencio" (dejar de escuchar) o "activo"
- salir: (sin valor) apagar a JARVIS"""

PERSONALIDAD = """Eres J.A.R.V.I.S. (Just A Rather Very Intelligent System), la inteligencia artificial personal de {quien}, igual que el asistente de Tony Stark: brillante, leal, elegante, eficiente, proactivo y con un humor seco y británico muy sutil. Te diriges al usuario como "{trato}".

Hablas SIEMPRE en español, en frases cortas y naturales porque se leen en voz alta: máximo 2 o 3 frases, sin emojis, sin listas, sin markdown, sin URLs.

Controlas por completo la computadora Windows del usuario mediante ACCIONES. Respondes ÚNICAMENTE con un objeto JSON válido, así:
{{"respuesta": "lo que dirás en voz alta", "acciones": [{{"tipo": "nombre_accion", "valor": "..."}}]}}

REGLAS
1. Si te pide hacer algo y existe una acción para ello, hazlo. Nunca digas que no puedes si hay una acción que sirve.
2. Las acciones marcadas [CONSULTA] te devuelven datos: úsalas y en "respuesta" pon solo una frase breve como "Consultando, {trato}." Después recibirás un mensaje RESULTADOS y entonces darás la respuesta final.
3. Nunca inventes datos actuales (clima, noticias, precios, resultados deportivos, archivos): consúltalos.
4. Para conversación, cultura general, chistes, consejos, traducciones o explicaciones, responde tú mismo con "acciones": [].
5. Puedes encadenar varias acciones en orden.
6. Si la orden es ambigua, haz una pregunta breve.
7. Usa la memoria y el contexto que se te dan; si el usuario te cuenta algo personal importante, guárdalo con recordar_dato.

ACCIONES DISPONIBLES (tipo: valor)
{acciones}"""


class Cerebro:
    def __init__(self, cfg, memoria):
        self.cfg = cfg
        self.memoria = memoria
        self.modelo = None
        self.motor = None            # "groq" (nube) u "ollama" (local)
        self.respaldo_hasta = 0.0    # mientras sea futuro, se usa el modelo de respaldo de Groq
        self.modelo_gemini = None    # se elige solo según la clave (respaldo y visión)
        self.groq_disponibles, self.groq_principal, self.groq_respaldo = [], None, None
        self.ultimo_motor = None     # quién respondió la última vez (para el HUD)
        self.historial = []
        self.ejemplos = []
        self.ejemplos_nube = []
        self.recargar_entrenamiento()

    # ------------------------------------------------------------ preparación
    def recargar_entrenamiento(self):
        msgs, nube = [], []
        todos = cargar_entrenamiento()
        for i, e in enumerate(todos):
            try:
                par = [{"role": "user", "content": e["usuario"]},
                       {"role": "assistant", "content": json.dumps(e["jarvis"], ensure_ascii=False)}]
            except Exception:
                continue
            msgs += par
            if e["usuario"] in EJEMPLOS_NUBE or e.get("propio") or e["usuario"].startswith("RESULTADOS"):
                nube += par
        self.ejemplos = msgs
        self.ejemplos_nube = nube

    def sistema(self):
        quien = self.cfg.get("nombre_usuario") or "tu usuario"
        return PERSONALIDAD.format(quien=quien, trato=self.cfg.get("trato", "señor"), acciones=ACCIONES)

    @staticmethod
    def ruta_ollama():
        p = shutil.which("ollama")
        if p:
            return p
        local = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Ollama", "ollama.exe")
        return local if os.path.exists(local) else None

    def en_linea(self):
        try:
            requests.get(OLLAMA + "/api/tags", timeout=2)
            return True
        except Exception:
            return False

    def encender(self):
        """Arranca Ollama si no está corriendo. Devuelve True si quedó en línea."""
        if self.en_linea():
            return True
        exe = self.ruta_ollama()
        if not exe:
            return False
        subprocess.Popen([exe, "serve"], creationflags=SIN_VENTANA,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(30):
            time.sleep(0.5)
            if self.en_linea():
                return True
        return False

    def modelos_instalados(self):
        try:
            return [m["name"] for m in requests.get(OLLAMA + "/api/tags", timeout=5).json().get("models", [])]
        except Exception:
            return []

    def modelo_ideal(self):
        elegido = self.cfg.get("modelo", "auto")
        if elegido and elegido != "auto":
            return elegido
        try:
            import psutil
            ram = psutil.virtual_memory().total / 1024 ** 3
        except Exception:
            ram = 8
        return "qwen2.5:7b" if ram >= 14 else "qwen2.5:3b"

    def preparar(self, progreso=None):
        """Elige el modelo; si no está, lo descarga mostrando el progreso."""
        ideal = self.modelo_ideal()
        instalados = self.modelos_instalados()
        base = lambda n: n if ":" in n else n + ":latest"
        if base(ideal) in instalados:
            self.modelo = ideal
        else:
            log.info("Descargando el modelo %s ...", ideal)
            if self.descargar(ideal, progreso):
                self.modelo = ideal
            else:
                texto = [m for m in instalados if "moondream" not in m and "llava" not in m and "embed" not in m]
                self.modelo = texto[0] if texto else None
        if self.modelo:
            log.info("Cerebro listo con el modelo %s", self.modelo)
            threading_precalentar(self)
        return self.modelo

    def descargar(self, nombre, progreso=None):
        try:
            with requests.post(OLLAMA + "/api/pull", json={"name": nombre, "model": nombre, "stream": True},
                               stream=True, timeout=(10, 600)) as r:
                for linea in r.iter_lines():
                    if not linea:
                        continue
                    d = json.loads(linea)
                    if d.get("error"):
                        log.error("Error descargando %s: %s", nombre, d["error"]);
                        return False
                    if progreso and d.get("total"):
                        progreso(d.get("completed", 0) / d["total"], f"DESCARGANDO CEREBRO {nombre}")
                    if d.get("status") == "success":
                        if progreso:
                            progreso(None, "")
                        return True
        except Exception as e:
            log.error("No pude descargar %s: %s", nombre, e)
        if progreso:
            progreso(None, "")
        return False

    # ------------------------------------------------------------ nube (Groq)
    def clave_groq(self):
        return (self.cfg.get("groq_api_key") or os.environ.get("GROQ_API_KEY") or "").strip()

    def usar_nube(self):
        return self.cfg.get("proveedor", "groq") == "groq"

    @staticmethod
    def modelos_groq(clave):
        """Lista los modelos que esta clave puede usar. Devuelve (lista o None, mensaje)."""
        clave = (clave or "").strip().strip('"').strip("'")
        if len(clave) < 20 or " " in clave:
            return None, "Esa clave parece incompleta. Cópiala completa desde Groq"
        try:
            r = requests.get(GROQ + "/models", headers={"Authorization": f"Bearer {clave}"}, timeout=10)
            if r.status_code == 200:
                datos = r.json().get("data", []) if isinstance(r.json(), dict) else []
                return [m.get("id", "") for m in datos if m.get("active", True) is not False and m.get("id")], "Clave válida"
            if r.status_code in (401, 403):
                return None, "Groq rechazó la clave. Cópiala de nuevo"
            return None, f"Groq respondió {r.status_code}. Intenta en un momento"
        except requests.RequestException:
            return None, "Sin conexión con Groq. Revisa tu internet"

    @classmethod
    def probar_groq(cls, clave):
        """Comprueba una clave. Devuelve (ok, mensaje)."""
        lista, msg = cls.modelos_groq(clave)
        return lista is not None, msg

    @staticmethod
    def elegir_modelo_groq(disponibles, preferido="", orden=(), excluir=()):
        """Elige un modelo de chat entre los que la cuenta tiene disponibles."""
        malos = ("whisper", "guard", "orpheus", "tts", "playai", "safeguard", "compound", "distil", "embed")
        chat = [m for m in disponibles if m and not any(x in m.lower() for x in malos) and m not in excluir]
        if not chat:
            return None
        if preferido and preferido != "auto" and preferido in chat:
            return preferido
        for candidato in orden:
            if candidato in chat:
                return candidato

        def tamano(m):   # modelos nuevos que no conozco: el más grande ("120b" > "70b" > "8b")
            n = [float(x) for x in re.findall(r"(\d+(?:\.\d+)?)b(?![a-z])", m.lower())]
            return max(n) if n else 0.0
        return sorted(chat, key=lambda m: (-tamano(m), m))[0]

    def preparar_nube(self):
        """Activa Groq si hay una clave válida y elige los mejores modelos disponibles. Devuelve (ok, mensaje)."""
        lista, msg = self.modelos_groq(self.clave_groq())
        if lista is None:
            return False, msg
        log.info("Modelos de Groq disponibles: %s", ", ".join(sorted(lista)))
        self.groq_disponibles = lista
        if not self._elegir_groq():
            return False, "Tu cuenta de Groq no tiene modelos de chat disponibles"
        self.motor = "groq"
        log.info("Cerebro en la nube listo: Groq %s (respaldo %s)", self.groq_principal, self.groq_respaldo)
        return True, msg

    def _elegir_groq(self):
        disp = getattr(self, "groq_disponibles", [])
        self.groq_principal = self.elegir_modelo_groq(disp, self.cfg.get("modelo_groq", "auto"), GROQ_PREFERIDOS)
        self.groq_respaldo = self.elegir_modelo_groq(disp, self.cfg.get("modelo_groq_respaldo", "auto"), GROQ_RAPIDOS,
                                                     excluir=(self.groq_principal,)) or self.groq_principal
        self.modelo = self.groq_principal
        return self.groq_principal

    def _modelo_groq_actual(self):
        if time.time() < self.respaldo_hasta:
            return self.groq_respaldo
        return self.groq_principal

    def _cuerpo_groq(self, modelo, mensajes, json_mode=True, razonamiento=True):
        cuerpo = {"model": modelo, "messages": mensajes, "temperature": float(self.cfg.get("temperatura", 0.4)),
                  "max_tokens": 800}
        if json_mode:
            cuerpo["response_format"] = {"type": "json_object"}
        if razonamiento and "gpt-oss" in modelo:
            cuerpo["reasoning_effort"] = "low"      # que piense poco: respuestas rápidas y menos consumo
        elif razonamiento and "qwen3" in modelo:
            cuerpo["reasoning_effort"] = "none"
        return cuerpo

    def _chat_groq(self, mensajes):
        """Llama a Groq. Si el modelo llega a su límite usa el de respaldo; si ya no existe, elige otro solo."""
        cabeceras = {"Authorization": f"Bearer {self.clave_groq()}"}
        modelo = self._modelo_groq_actual()
        json_mode, razonamiento = True, True
        for intento in range(5):
            cuerpo = self._cuerpo_groq(modelo, mensajes, json_mode, razonamiento)
            r = requests.post(GROQ + "/chat/completions", json=cuerpo, headers=cabeceras, timeout=30)
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"]
            detalle = r.text[:300]
            if r.status_code != 429:
                log.warning("Groq %s con %s: %s", r.status_code, modelo, detalle)
            if r.status_code == 429:
                espera = _segundos(r.headers.get("retry-after"))
                if modelo != self.groq_respaldo:
                    log.warning("Groq: %s llegó a su límite, uso %s por un rato", modelo, self.groq_respaldo)
                    self.respaldo_hasta = time.time() + max(espera, 120)
                    modelo = self.groq_respaldo
                    continue
                if espera <= 8:
                    time.sleep(espera or 2)
                    continue
                raise LimiteNube(espera)
            if r.status_code == 404 or "model_not_found" in detalle or "decommissioned" in detalle:
                # ese modelo ya no existe para esta cuenta: se quita y se elige otro automáticamente
                self.groq_disponibles = [m for m in getattr(self, "groq_disponibles", []) if m != modelo]
                if self.cfg.get("modelo_groq") == modelo:
                    self.cfg["modelo_groq"] = "auto"
                if self.cfg.get("modelo_groq_respaldo") == modelo:
                    self.cfg["modelo_groq_respaldo"] = "auto"
                if not self._elegir_groq():
                    raise ValueError("Groq no tiene modelos de chat disponibles")
                log.warning("Cambio automático de modelo de Groq a %s", self.groq_principal)
                modelo = self._modelo_groq_actual()
                continue
            if r.status_code == 400:
                texto = detalle.lower()
                if "reasoning" in texto and razonamiento:
                    razonamiento = False
                    continue
                if ("json" in texto or "response_format" in texto) and json_mode:
                    json_mode = False           # se pide sin modo JSON y se interpreta igual
                    continue
            if r.status_code in (401, 403):
                raise ClaveInvalida()
            if r.status_code >= 500 and intento < 4:
                time.sleep(1.5)
                continue
            r.raise_for_status()
        raise LimiteNube(60)

    # ------------------------------------------------------------ nube (Gemini: respaldo y visión)
    def clave_gemini(self):
        return (self.cfg.get("gemini_api_key") or os.environ.get("GEMINI_API_KEY") or "").strip()

    @staticmethod
    def elegir_modelo_gemini(modelos, preferido=""):
        """De la lista de modelos de la cuenta, elige el mejor Flash estable para chatear."""
        nombres = {m.get("name", "").split("/")[-1] for m in modelos
                   if "generateContent" in (m.get("supportedGenerationMethods") or [])}
        if preferido and preferido in nombres:
            return preferido
        if "gemini-flash-latest" in nombres:
            return "gemini-flash-latest"
        malos = ("tts", "live", "image", "audio", "embedding", "thinking", "exp", "robotics", "native")

        def version(n):
            m = re.match(r"gemini-(\d+(?:\.\d+)?)-flash", n)
            return float(m.group(1)) if m else 0.0
        flash = [n for n in nombres if version(n) and not any(x in n for x in malos)]
        for filtro in (lambda n: "lite" not in n and "preview" not in n,
                       lambda n: "preview" not in n,
                       lambda n: "lite" not in n,
                       lambda n: True):
            candidatos = [n for n in flash if filtro(n)]
            if candidatos:
                # versión más nueva; a igualdad, el nombre más corto (el "oficial", sin sufijos de fecha)
                return sorted(candidatos, key=lambda n: (-version(n), len(n)))[0]
        return None

    def probar_gemini(self, clave):
        """Comprueba una clave de Gemini. Devuelve (ok, mensaje, modelo)."""
        clave = (clave or "").strip().strip('"').strip("'")
        if len(clave) < 20 or " " in clave:
            return False, "Esa clave parece incompleta. Cópiala completa desde AI Studio", None
        try:
            r = None
            # Google tiene claves clásicas (AIza...) y nuevas (AQ....): se prueban las formas de enviarla
            for forma in ("cabecera", "parametro", "bearer"):
                r = requests.get(GEMINI + "/models", params=_params_gemini(clave, forma, {"pageSize": 200}),
                                 headers=_cabecera_gemini(clave, forma), timeout=10)
                if r.status_code == 200:
                    self.forma_gemini = forma
                    break
            if r.status_code == 200:
                modelo = self.elegir_modelo_gemini(r.json().get("models", []), self.cfg.get("modelo_gemini", ""))
                if modelo:
                    return True, "Clave válida", modelo
                return False, "Tu cuenta de Gemini no tiene modelos Flash disponibles", None
            if r.status_code in (400, 401, 403):
                return False, "Google rechazó la clave. Cópiala de nuevo", None
            return False, f"Gemini respondió {r.status_code}. Intenta en un momento", None
        except requests.RequestException:
            return False, "Sin conexión con Gemini. Revisa tu internet", None

    def preparar_gemini(self):
        ok, msg, modelo = self.probar_gemini(self.clave_gemini())
        if ok:
            self.modelo_gemini = modelo
            log.info("Gemini listo (respaldo y visión): %s", modelo)
            if not self.modelo:          # sin Groq, Gemini pasa a ser el cerebro principal
                self.motor, self.modelo = "gemini", modelo
        return ok, msg

    def _chat_gemini(self, mensajes, imagen_png=None):
        if not self.modelo_gemini:
            raise LimiteNube(60)
        sistema = " ".join(m["content"] for m in mensajes if m["role"] == "system")
        contenidos = []
        for m in mensajes:
            if m["role"] == "system":
                continue
            rol = "model" if m["role"] == "assistant" else "user"
            if contenidos and contenidos[-1]["role"] == rol:
                contenidos[-1]["parts"][0]["text"] += "\n" + m["content"]
            else:
                contenidos.append({"role": rol, "parts": [{"text": m["content"]}]})
        if imagen_png:
            contenidos[-1]["parts"].append({"inline_data": {"mime_type": "image/png",
                                                            "data": base64.b64encode(open(imagen_png, "rb").read()).decode()}})
        config = {"temperature": float(self.cfg.get("temperatura", 0.4)), "maxOutputTokens": 800}
        if not imagen_png:
            config["responseMimeType"] = "application/json"
        modelo = self.modelo_gemini
        if "2.5" in modelo:
            config["thinkingConfig"] = {"thinkingBudget": 0}     # responder rápido, sin "pensar en voz baja"
        elif re.match(r"gemini-[3-9]", modelo) or modelo.endswith("-latest"):
            config["thinkingConfig"] = {"thinkingLevel": "low"}
        cuerpo = {"contents": contenidos, "generationConfig": config}
        if sistema:
            cuerpo["systemInstruction"] = {"parts": [{"text": sistema}]}
        url = f"{GEMINI}/models/{modelo}:generateContent"
        forma = getattr(self, "forma_gemini", "cabecera")
        cab = _cabecera_gemini(self.clave_gemini(), forma)
        params = _params_gemini(self.clave_gemini(), forma)
        for intento in range(3):
            r = requests.post(url, json=cuerpo, headers=cab, params=params or None, timeout=45)
            if r.status_code == 200:
                d = r.json()
                partes = (d.get("candidates") or [{}])[0].get("content", {}).get("parts", [])
                texto = "".join(p.get("text", "") for p in partes if not p.get("thought"))
                if texto:
                    return texto
                raise ValueError(f"Gemini no devolvió texto: {str(d)[:200]}")
            if r.status_code == 400 and "thinking" in r.text.lower() and "thinkingConfig" in config:
                config.pop("thinkingConfig")          # este modelo no acepta ese ajuste: se reintenta sin él
                continue
            if r.status_code == 429:
                raise LimiteNube(_segundos(r.headers.get("retry-after")) or 60)
            if r.status_code in (401, 403):
                raise ClaveInvalida()
            if r.status_code >= 500 and intento < 2:
                time.sleep(1.5)
                continue
            r.raise_for_status()
        raise LimiteNube(60)

    # ------------------------------------------------------------ pensar
    def pensar(self, orden, contexto="", resultados=None):
        """Devuelve {"respuesta": str, "acciones": [dict]}"""
        trato = self.cfg.get("trato", "señor")
        if not self.modelo:
            return {"respuesta": f"Mi núcleo de inteligencia no está conectado, {trato}. Revise la clave de Groq en mi configuración.",
                    "acciones": []}
        if resultados is None:
            contenido = (f"[{contexto}]\n" if contexto else "") + orden
            self.historial.append({"role": "user", "content": orden})
        else:
            contenido = ("RESULTADOS de las acciones (úsalos para responder ahora al usuario, de forma natural y breve; "
                         "no repitas la consulta):\n" + resultados)
            self.historial.append({"role": "user", "content": contenido})
        nube = self.motor in ("groq", "gemini")
        ejemplos = self.ejemplos_nube if nube else self.ejemplos
        previos = self.historial[-(9 if nube else 14):-1]
        mensajes = [{"role": "system", "content": self.sistema()}] + ejemplos + previos + [
            {"role": "user", "content": contenido}]
        try:
            texto = self._preguntar(mensajes)
            plan = interpretar(texto)
        except LimiteNube as e:
            minutos = max(1, round(e.segundos / 60))
            plan = {"respuesta": f"Alcancé el límite gratuito de mi núcleo en la nube por ahora, {trato}. "
                                 f"Vuelvo a estar al cien por ciento en unos {minutos} minutos; mientras tanto "
                                 "puedo abrir programas, controlar el volumen y la música.", "acciones": []}
        except ClaveInvalida:
            plan = {"respuesta": f"Mi clave de acceso fue rechazada, {trato}. Revísela con clic derecho en el reactor.",
                    "acciones": []}
        except requests.ConnectionError:
            if nube:
                plan = {"respuesta": f"No logro conectar con mi núcleo en la nube, {trato}. Revise su conexión a internet.",
                        "acciones": []}
            else:
                plan = {"respuesta": "Perdí la conexión con mi núcleo de inteligencia. Intentaré reconectar.", "acciones": []}
                threading_encender(self)
        except requests.Timeout:
            plan = {"respuesta": f"Mi núcleo tardó demasiado en responder, {trato}. ¿Lo intentamos de nuevo?", "acciones": []}
        except Exception as e:
            log.error("Error del cerebro: %s", e)
            plan = {"respuesta": "Disculpe, tuve un fallo procesando eso.", "acciones": []}
        self.historial.append({"role": "assistant", "content": json.dumps(plan, ensure_ascii=False)})
        self.historial = self.historial[-30:]
        return plan

    def _preguntar(self, mensajes):
        """Groq (70B → 8B) y, si falla o se acaba el límite, Gemini. Sin Groq: Gemini u Ollama."""
        if self.motor == "groq":
            try:
                texto = self._chat_groq(mensajes)
                self.ultimo_motor = "groq"
                return texto
            except (LimiteNube, ClaveInvalida, requests.RequestException, ValueError, KeyError) as e:
                if not self.modelo_gemini:
                    raise
                log.warning("Groq no disponible (%s): respondo con Gemini", e)
        if self.motor in ("groq", "gemini"):
            texto = self._chat_gemini(mensajes)
            self.ultimo_motor = "gemini"
            return texto
        self.ultimo_motor = "ollama"
        return self._chat_ollama(mensajes)

    def _chat_ollama(self, mensajes):
        cuerpo = {"model": self.modelo, "messages": mensajes, "format": "json", "stream": False,
                  "keep_alive": "60m",
                  "options": {"temperature": float(self.cfg.get("temperatura", 0.4)), "num_ctx": 8192}}
        if self.modelo.startswith(("qwen3", "deepseek-r1")):
            cuerpo["think"] = False
        r = requests.post(OLLAMA + "/api/chat", json=cuerpo, timeout=180)
        r.raise_for_status()
        return r.json()["message"]["content"]

    def ver(self, imagen_png, pregunta):
        """Analiza una captura de pantalla: con Gemini (nube) o, si no hay, con moondream en Ollama."""
        if self.modelo_gemini:
            pedido = ("Describe en español lo que se ve en esta captura de la pantalla de mi computadora: programas, "
                      "ventanas, textos y contenido importante. Sé concreto y breve.")
            if pregunta:
                pedido += " Luego responde esta pregunta: " + pregunta
            try:
                return self._chat_gemini([{"role": "user", "content": pedido}], imagen_png=imagen_png).strip()
            except Exception as e:
                log.error("Error de visión con Gemini: %s", e)
                return None
        modelo = self.cfg.get("modelo_vision", "moondream")
        if not self.en_linea():
            return None
        if not any(m.split(":")[0] == modelo.split(":")[0] for m in self.modelos_instalados()):
            return None
        img = base64.b64encode(open(imagen_png, "rb").read()).decode()
        prompt = "Describe in detail what is visible on this computer screen: apps, windows, text and important content."
        if pregunta:
            prompt += " Then answer this question: " + pregunta
        try:
            r = requests.post(OLLAMA + "/api/generate", json={"model": modelo, "prompt": prompt, "images": [img],
                                                              "stream": False}, timeout=180)
            return r.json().get("response", "").strip()
        except Exception as e:
            log.error("Error de visión: %s", e)
            return None


# ---------------------------------------------------------------- utilidades
class LimiteNube(Exception):
    def __init__(self, segundos=60):
        super().__init__(f"límite de Groq ({segundos}s)")
        self.segundos = segundos


class ClaveInvalida(Exception):
    pass


def _cabecera_gemini(clave, forma):
    if forma == "cabecera":
        return {"x-goog-api-key": clave}
    if forma == "bearer":
        return {"Authorization": f"Bearer {clave}"}
    return {}


def _params_gemini(clave, forma, extra=None):
    p = dict(extra or {})
    if forma == "parametro":
        p["key"] = clave
    return p


def _segundos(valor):
    try:
        return float(valor)
    except (TypeError, ValueError):
        return 0.0


def interpretar(texto):
    """Convierte la salida del modelo en un plan válido, aunque venga algo desordenada."""
    datos = None
    try:
        datos = json.loads(texto)
    except Exception:
        m = re.search(r"\{.*\}", texto or "", re.S)
        if m:
            try:
                datos = json.loads(m.group(0))
            except Exception:
                datos = None
    if not isinstance(datos, dict):
        return {"respuesta": (texto or "").strip()[:400], "acciones": []}
    respuesta = datos.get("respuesta") or datos.get("response") or datos.get("mensaje") or ""
    acciones = datos.get("acciones", datos.get("actions", []))
    if isinstance(acciones, dict):
        acciones = [acciones]
    if not isinstance(acciones, list):
        acciones = []
    limpias = []
    for a in acciones:
        if isinstance(a, str):
            a = {"tipo": a, "valor": ""}
        if isinstance(a, dict) and (a.get("tipo") or a.get("type")):
            a = dict(a)
            a["tipo"] = str(a.pop("tipo", None) or a.pop("type", "")).strip().lower().replace(" ", "_")
            if "valor" not in a:
                a["valor"] = a.pop("value", "")
            limpias.append(a)
    return {"respuesta": str(respuesta), "acciones": limpias}


def threading_precalentar(cerebro):
    """Carga el modelo en memoria en segundo plano para que la primera respuesta sea rápida."""
    import threading

    def _ir():
        try:
            requests.post(OLLAMA + "/api/chat", json={
                "model": cerebro.modelo, "stream": False, "keep_alive": "60m", "format": "json",
                "options": {"num_ctx": 8192, "num_predict": 1},
                "messages": [{"role": "system", "content": cerebro.sistema()}] + cerebro.ejemplos +
                            [{"role": "user", "content": "hola"}]}, timeout=300)
        except Exception:
            pass
    threading.Thread(target=_ir, daemon=True).start()


def threading_encender(cerebro):
    import threading
    threading.Thread(target=cerebro.encender, daemon=True).start()
