<div align="center">

<img src="docs/icono.png" width="140" alt="Reactor de JARVIS">

# J.A.R.V.I.S. 2.0

**Just A Rather Very Intelligent System** — mi asistente de voz para Windows inspirado en Iron Man

![Windows](https://img.shields.io/badge/Windows-10%20%7C%2011-0078D6?logo=windows&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![Groq](https://img.shields.io/badge/IA-Groq%20Cloud-F55036)
![Llama](https://img.shields.io/badge/Modelo-Llama%203.3%2070B-0467DF?logo=meta&logoColor=white)
![Voz](https://img.shields.io/badge/Voz-Neural%20en%20español-00d8ff)
![Licencia](https://img.shields.io/badge/Licencia-MIT-ffb000)

*Le hablo, me entiende y controla mi PC. IA en la nube, gratis y sin gastar mi tarjeta gráfica.*

</div>

---

## ✨ Vista previa

<div align="center">
<img src="docs/hud-procesando.png" width="780" alt="HUD pensando"><br>
<sub>Pensando (modo dorado)</sub><br><br>
<img src="docs/hud-conversando.png" width="780" alt="HUD conversando"><br>
<sub>Conversando — registro de comandos, sistemas en vivo y ecualizador de voz</sub><br><br>
<img src="docs/reactor.png" width="140" alt="Reactor flotante"><br>
<sub>Reactor flotante en reposo (clic para hablar)</sub>
</div>

## 🚀 Características

| | |
|---|---|
| 🎙️ **Activación por voz** | "Jarvis, …", doble aplauso 👏👏, `Ctrl+Alt+J` o clic en el reactor |
| ☁️ **Cerebro en la nube** | Groq + Llama 3.3 70B: responde en menos de 1 s, gratis |
| 🎮 **Cero impacto al jugar** | No usa GPU; JARVIS ocupa ~200 MB de RAM |
| 🔁 **Respaldo automático** | Groq grande → Groq rápido → Google Gemini, sin que lo notes |
| 🧭 **Elige modelos solo** | Consulta qué modelos tiene tu cuenta y usa el mejor disponible |
| 🗣️ **Voz neural** | Voces de Microsoft en español, con respaldo sin internet |
| 💬 **Conversación continua** | Después de responder te sigue escuchando, sin repetir "Jarvis" |
| 🖥️ **HUD holográfico** | Reactor animado que reacciona a tu voz, colores por estado |
| ⚡ **Reflejos instantáneos** | Volumen, música y apps sin esperar a la IA |
| 🧩 **45+ habilidades** | Apps, web, sistema, archivos, info, productividad |
| 💾 **Memoria** | Recuerda datos tuyos para siempre |
| 🎓 **Aprende** | Le enseñas comandos y rutinas nuevas por voz |
| 👁️ **Visión** | "¿Qué hay en mi pantalla?" con Gemini |
| 📱 **App Android** | Háblale y controla la PC desde el celular, con WiFi o datos móviles ([JARVIS-Android](https://github.com/AbnerGA7/JARVIS-Android)) |
| 🚀 **Inicia con Windows** | Arranca solo al encender la PC; se desactiva desde el menú |
| 👏 **Prueba de aplausos** | Indicador en vivo y sensibilidad ajustable |
| 🔒 **Seguro** | Confirma por voz antes de apagar, enviar o borrar |

## 🗣️ Ejemplos

```
"Jarvis, abre Spotify y pon música de Queen"
"Jarvis, volumen al 30"                      "Jarvis, ¿cómo está el clima?"
"Jarvis, recuérdame en 20 minutos sacar la ropa"
"Jarvis, anota pan y leche en la lista de compras"
"Jarvis, busca el informe de historia" → "ábrelo"
"Jarvis, mándale un WhatsApp a mamá diciendo que ya voy"
"Jarvis, ¿a cuánto está el dólar?"           "Jarvis, ¿qué hay en mi pantalla?"
"Jarvis, cuando te diga modo cine, pausa todo, baja el brillo y abre Netflix"
"Jarvis, activa el modo gamer"
```

## 🏗️ Arquitectura

```mermaid
flowchart LR
    M[🎙️ Micrófono] --> O[oido.py<br>voz + aplausos]
    O -->|texto| R{rapido.py<br>reflejos}
    R -->|orden simple| H[habilidades.py<br>45+ acciones]
    R -->|orden compleja| C[cerebro.py<br>Groq ☁️]
    C -->|plan JSON| H
    H -->|resultados| C
    H --> PC[🖥️ Windows]
    C --> V[voz.py<br>voz neural]
    V --> HUD[hud.py<br>interfaz]
```

| Archivo | Qué hace |
|---|---|
| `jarvis.py` | Núcleo: conversación, arranque, bandeja |
| `oido.py` | Micrófono, detección de voz y de aplausos |
| `voz.py` | Voz neural y voz de Windows de respaldo |
| `cerebro.py` | Personalidad, prompt, conexión con Groq y respaldo automático |
| `rapido.py` | Órdenes instantáneas y comandos aprendidos |
| `habilidades.py` | Todas las acciones sobre la PC e internet |
| `hud.py` | Interfaz holográfica y reactor flotante |
| `datos/` | Configuración y ejemplos de entrenamiento |

## 📦 Instalación

1. Instala **[Python 3.12](https://www.python.org/downloads/)** (marca *Add Python to PATH*).
2. Crea tu clave gratis en **[Groq](https://console.groq.com/keys)** (inicia sesión con Google → *Create API Key*).
3. Ejecuta `instalar.bat` — instala las librerías (no descarga nada pesado).
4. Ejecuta `iniciar_jarvis.bat`.
5. La primera vez aparece esta ventana: pega tu clave y listo.

<div align="center"><img src="docs/clave-groq.png" width="560" alt="Ventana para pegar la clave de Groq"></div>

### Crear el instalador `.exe`

```bat
compilar_exe.bat
```

Genera `salida\JARVIS_Setup.exe` con PyInstaller + Inno Setup: icono propio, acceso en el
escritorio y opción de iniciar con Windows.

## 📱 Conectar el celular

1. Instala **JARVIS.apk** desde [JARVIS-Android → Releases](https://github.com/AbnerGA7/JARVIS-Android/releases/latest).
2. En la PC: clic derecho en el reactor → **Conectar celular** (o di *"Jarvis, conecta mi celular"*).
3. Escribe en la app el código que aparece (ej. `K7P2-QX9M`).

Funciona en la misma WiFi (conexión directa) o con datos móviles (túnel seguro de Cloudflare, sin abrir puertos).
La dirección del túnel viaja cifrada con AES-256-GCM y cada celular usa un token secreto propio.

## ⚙️ Configuración

Clic derecho en el reactor → **Configuración** (`%APPDATA%\JARVIS\config.json`):

| Clave | Ejemplo |
|---|---|
| `trato` / `nombre_usuario` | `"señor"`, `"Abner"` |
| `voz` | `es-MX-JorgeNeural`, `es-ES-AlvaroNeural`, `es-PE-AlexNeural` |
| `ciudad` | `"Lima"` |
| `contactos` | `{"mamá": "+51999999999"}` |
| `rutinas` | modo gamer, modo estudio, buenas noches… |
| `proveedor` | `groq` (nube) u `ollama` (local, opcional) |
| `modelo_groq` / `modelo_groq_respaldo` | `auto` (recomendado) o el id de un modelo |
| `gemini_api_key` / `modelo_gemini` | clave de Gemini · `auto` |
| `segundos_conversacion` | `7` (0 lo desactiva) |
| `iniciar_con_windows` | `true` |
| `sensibilidad_aplauso` | umbral de volumen (también desde la prueba de aplausos) |
| `acceso_remoto` | `true` (túnel para usarlo con datos móviles) |

## 🎓 Entrenamiento

- **Por voz:** *"cuando te diga X, haz Y"* crea un comando nuevo al instante.
- **Con ejemplos:** menú → *Entrenar (mis ejemplos)* y agregas pares orden → respuesta.
- **Memoria:** *"recuerda que…"* / *"olvida…"*.

## 🛠️ Atajos

| Atajo | Acción |
|---|---|
| `Ctrl+Alt+J` | Hablar con JARVIS |
| `Ctrl+Alt+S` | Callarlo |
| Clic en el reactor | Hablar / callar |
| Clic derecho | Menú |

## 🧰 Problemas comunes

- **No me escucha:** revisa el micrófono predeterminado de Windows.
- **Aplausos:** clic derecho → *Micrófono y parlantes* → prueba de aplausos; ajusta la sensibilidad hasta que detecte tus dos aplausos.
- **"Alcancé el límite gratuito":** el plan gratis de Groq tiene un tope diario; se renueva solo.
- **Cambiar las claves:** clic derecho en el reactor → *Clave de Groq* / *Clave de Gemini*.
- **Gemini (opcional):** crea tu clave gratis en [Google AI Studio](https://aistudio.google.com/apikey); activa el respaldo y la visión.
- **Registro:** `%APPDATA%\JARVIS\jarvis.log`.

---

<div align="center">
Hecho con ☕ por <a href="https://github.com/AbnerGA7">AbnerGA7</a> · Lima, Perú
</div>
