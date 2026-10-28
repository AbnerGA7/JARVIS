# -*- coding: utf-8 -*-
"""
Acceso desde cualquier lugar (celular con datos móviles ↔ PC en otra red).

1. JARVIS abre un túnel gratuito de Cloudflare (sin cuenta): https://algo.trycloudflare.com → tu PC.
2. Esa dirección cambia en cada arranque, así que la PC la publica CIFRADA en ntfy.sh (un buzón público);
   solo el celular vinculado tiene la clave para leerla.
3. Para vincular, la PC muestra un código (p. ej. K7P2-QX9M). Con ese código el celular encuentra la PC
   (también cifrado) y se empareja. Luego usa un token secreto de 256 bits en cada pedido.
"""
import os, re, json, time, base64, hashlib, secrets, threading, subprocess
import requests
from config import log, DATOS, BASE, SIN_VENTANA, ES_WINDOWS, Almacen

NTFY = "https://ntfy.sh"
CLOUDFLARED_URL = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
ALFABETO = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"   # sin 0/O ni 1/I para no confundirse


# ---------------------------------------------------------------- cifrado (AES-256-GCM)
def clave_de(texto):
    return hashlib.sha256(("JARVIS|" + texto).encode()).digest()


def cifrar(datos, clave):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    nonce = secrets.token_bytes(12)
    return base64.b64encode(nonce + AESGCM(clave).encrypt(nonce, json.dumps(datos).encode(), None)).decode()


def descifrar(texto, clave):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    crudo = base64.b64decode(texto)
    return json.loads(AESGCM(clave).decrypt(crudo[:12], crudo[12:], None))


def tema_de(texto):
    """Nombre del buzón en ntfy derivado del secreto (no revela el secreto)."""
    return "jarvis-" + hashlib.sha256(("TEMA|" + texto).encode()).hexdigest()[:24]


def codigo_nuevo():
    c = "".join(secrets.choice(ALFABETO) for _ in range(8))
    return c[:4] + "-" + c[4:]


def normalizar_codigo(c):
    return "".join(ch for ch in str(c).upper() if ch in ALFABETO)


def publicar(tema, datos, clave):
    try:
        r = requests.post(f"{NTFY}/{tema}", data=cifrar(datos, clave).encode(),
                          headers={"Title": "JARVIS", "Cache": "yes"}, timeout=10)
        return r.status_code < 300
    except requests.RequestException as e:
        log.warning("No pude publicar la dirección del túnel: %s", e)
        return False


# ---------------------------------------------------------------- túnel
class Tunel:
    def __init__(self, puerto, al_cambiar=None, progreso=None):
        self.puerto = puerto
        self.al_cambiar = al_cambiar or (lambda url: None)
        self.progreso = progreso
        self.url = None
        self.proceso = None
        self.activo = False
        self.canal = Almacen("canal.json", {})
        if not self.canal.datos.get("id"):
            self.canal.datos = {"id": secrets.token_hex(16), "clave": base64.b64encode(secrets.token_bytes(32)).decode()}
            self.canal.guardar()

    @property
    def canal_id(self):
        return self.canal.datos["id"]

    @property
    def canal_clave(self):
        return base64.b64decode(self.canal.datos["clave"])

    # ------------------------------------------------------------ cloudflared
    def ejecutable(self):
        for ruta in (os.path.join(BASE, "cloudflared.exe"), os.path.join(DATOS, "cloudflared.exe")):
            if os.path.exists(ruta):
                return ruta
        from shutil import which
        return which("cloudflared")

    def descargar(self):
        destino = os.path.join(DATOS, "cloudflared.exe")
        log.info("Descargando cloudflared para el acceso remoto...")
        try:
            with requests.get(CLOUDFLARED_URL, stream=True, timeout=(10, 120)) as r:
                r.raise_for_status()
                total = int(r.headers.get("Content-Length") or 0)
                hecho = 0
                with open(destino + ".tmp", "wb") as f:
                    for trozo in r.iter_content(256 * 1024):
                        f.write(trozo)
                        hecho += len(trozo)
                        if self.progreso and total:
                            self.progreso(hecho / total, "DESCARGANDO ACCESO REMOTO")
            os.replace(destino + ".tmp", destino)
            return destino
        except Exception as e:
            log.error("No pude descargar cloudflared: %s", e)
            return None
        finally:
            if self.progreso:
                self.progreso(None, "")

    def iniciar(self):
        threading.Thread(target=self._vigilar, daemon=True).start()

    def _vigilar(self):
        espera = 5
        while True:
            exe = self.ejecutable() or (self.descargar() if ES_WINDOWS else None)
            if not exe:
                log.warning("Acceso remoto no disponible (falta cloudflared)")
                return
            self.activo = True
            inicio = time.time()
            self._ejecutar(exe)
            self.url = None
            # si se cayó, se reintenta con espera creciente (máx. 5 min)
            espera = 5 if time.time() - inicio > 600 else min(espera * 2, 300)
            log.warning("El túnel se cerró; reintento en %s s", espera)
            time.sleep(espera)

    def _ejecutar(self, exe):
        cmd = [exe, "tunnel", "--no-autoupdate", "--url", f"http://127.0.0.1:{self.puerto}"]
        try:
            self.proceso = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                            encoding="utf-8", errors="ignore", creationflags=SIN_VENTANA)
        except Exception as e:
            log.error("No pude iniciar cloudflared: %s", e)
            time.sleep(30)
            return
        for linea in self.proceso.stdout:
            m = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", linea)
            if m and m.group(0) != self.url:
                self.url = m.group(0)
                log.info("Acceso remoto listo: %s", self.url)
                threading.Thread(target=self._publicar_periodicamente, args=(self.url,), daemon=True).start()
                try:
                    self.al_cambiar(self.url)
                except Exception:
                    pass
        self.proceso.wait()

    def _publicar_periodicamente(self, url):
        """ntfy guarda los mensajes 12 h: se vuelve a publicar cada 6 h mientras la dirección no cambie."""
        while self.url == url:
            publicar(tema_de(self.canal_id), {"url": url, "t": int(time.time())}, self.canal_clave)
            for _ in range(6 * 360):
                if self.url != url:
                    return
                time.sleep(10)

    def anunciar_codigo(self, codigo, extra):
        """Publica (cifrado con el código) cómo encontrar esta PC, para que el celular se vincule desde donde sea."""
        c = normalizar_codigo(codigo)
        datos = dict(extra, url=self.url, t=int(time.time()))
        threading.Thread(target=publicar, args=(tema_de(c), datos, clave_de(c)), daemon=True).start()

    def detener(self):
        try:
            if self.proceso and self.proceso.poll() is None:
                self.proceso.terminate()
        except Exception:
            pass
