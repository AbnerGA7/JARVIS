# -*- coding: utf-8 -*-
"""
Cerebro de J.A.R.V.I.S. — IA local y gratuita con Ollama.
Personalidad + catálogo de acciones + ejemplos de entrenamiento + memoria a largo plazo.
"""
import os, re, json, time, shutil, base64, subprocess
import requests
from config import log, SIN_VENTANA, cargar_entrenamiento

OLLAMA = "http://127.0.0.1:11434"

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
        self.historial = []
        self.ejemplos = []
        self.recargar_entrenamiento()

    # ------------------------------------------------------------ preparación
    def recargar_entrenamiento(self):
        msgs = []
        for e in cargar_entrenamiento():
            try:
                msgs.append({"role": "user", "content": e["usuario"]})
                msgs.append({"role": "assistant", "content": json.dumps(e["jarvis"], ensure_ascii=False)})
            except Exception:
                pass
        self.ejemplos = msgs

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

    # ------------------------------------------------------------ pensar
    def pensar(self, orden, contexto="", resultados=None):
        """Devuelve {"respuesta": str, "acciones": [dict]}"""
        if not self.modelo:
            return {"respuesta": "Mi núcleo de inteligencia no está disponible. Revise que Ollama esté instalado, " + self.cfg.get("trato", "señor") + ".", "acciones": []}
        if resultados is None:
            contenido = (f"[{contexto}]\n" if contexto else "") + orden
            self.historial.append({"role": "user", "content": orden})
        else:
            contenido = ("RESULTADOS de las acciones (úsalos para responder ahora al usuario, de forma natural y breve; "
                         "no repitas la consulta):\n" + resultados)
            self.historial.append({"role": "user", "content": contenido})
        mensajes = [{"role": "system", "content": self.sistema()}] + self.ejemplos + self.historial[-14:-1] + [
            {"role": "user", "content": contenido}]
        cuerpo = {"model": self.modelo, "messages": mensajes, "format": "json", "stream": False,
                  "keep_alive": "60m",
                  "options": {"temperature": float(self.cfg.get("temperatura", 0.4)), "num_ctx": 8192}}
        if self.modelo.startswith(("qwen3", "deepseek-r1")):
            cuerpo["think"] = False
        try:
            r = requests.post(OLLAMA + "/api/chat", json=cuerpo, timeout=180)
            r.raise_for_status()
            texto = r.json()["message"]["content"]
            plan = interpretar(texto)
        except requests.ConnectionError:
            plan = {"respuesta": "Perdí la conexión con mi núcleo de inteligencia. Intentaré reconectar.", "acciones": []}
            threading_encender(self)
        except Exception as e:
            log.error("Error del cerebro: %s", e)
            plan = {"respuesta": "Disculpe, tuve un fallo procesando eso.", "acciones": []}
        self.historial.append({"role": "assistant", "content": json.dumps(plan, ensure_ascii=False)})
        self.historial = self.historial[-30:]
        return plan

    def ver(self, imagen_png, pregunta):
        """Analiza una imagen con el modelo de visión (si está instalado)."""
        modelo = self.cfg.get("modelo_vision", "moondream")
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
