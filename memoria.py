# -*- coding: utf-8 -*-
"""
Memoria de J.A.R.V.I.S.: una base de datos (SQLite) donde JARVIS y tú aprenden juntos.

- conocimiento : lo que JARVIS aprende de ti (datos, gustos, preferencias, correcciones).
- conversacion : todo lo que hablan (para seguir el hilo aunque reinicies la PC).
- patrones     : órdenes que repites; a la segunda vez que salen bien, JARVIS las hace al instante.
- lecciones    : lo que JARVIS te enseña; puedes pedir un resumen o un repaso.
"""
import os, re, json, random, sqlite3, difflib, datetime, threading
from config import ruta, normalizar, log

VACIAS = set("""a al algo como con de del el ella ellas ellos en es esa ese eso esta este esto estoy fue ha hay la las le les
lo los me mi mis muy no nos o para pero por que se si sin sobre su sus te tu tus un una uno unos unas y ya yo jarvis senor
quiero puedes dime haz hazme pon abre favor por""".split())

ESQUEMA = """
CREATE TABLE IF NOT EXISTS conocimiento(
    id INTEGER PRIMARY KEY, tipo TEXT NOT NULL, texto TEXT NOT NULL, fuente TEXT,
    creado TEXT, usado TEXT, usos INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS conversacion(
    id INTEGER PRIMARY KEY, fecha TEXT, origen TEXT, usuario TEXT, jarvis TEXT, acciones TEXT, motor TEXT);
CREATE TABLE IF NOT EXISTS patrones(
    frase TEXT PRIMARY KEY, acciones TEXT NOT NULL, respuesta TEXT, veces INTEGER DEFAULT 1,
    ultima TEXT, activo INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS lecciones(
    id INTEGER PRIMARY KEY, fecha TEXT, tema TEXT, contenido TEXT, repasos INTEGER DEFAULT 0, ultimo_repaso TEXT);
"""

# Acciones que se pueden repetir tal cual (no dependen de datos del momento): candidatas a volverse reflejos
REPETIBLES = {"abrir_app", "cerrar_app", "abrir_web", "buscar_google", "buscar_youtube", "reproducir", "abrir_carpeta",
              "volumen", "brillo", "media", "ventana", "teclas", "configuracion", "rutina", "ajustes_audio",
              "centro_control", "captura", "modo", "bloquear", "suspender"}
VECES_PARA_APRENDER = 2
# órdenes que dependen de lo que hay en pantalla en ese momento ("ciérralo", "abre esto"): nunca se vuelven reflejos
DEICTICAS = re.compile(r"\b(esto|eso|esta|este|esa|ese|estos|estas|esos|esas|aqui|ahi|alli|aca)\b|^\w+(melo|mela|selo|sela|lo|la|los|las)\b")


def ahora():
    return datetime.datetime.now().isoformat(timespec="seconds")


def palabras(texto):
    return {p for p in normalizar(texto).split() if len(p) > 2 and p not in VACIAS}


class Memoria:
    def __init__(self, archivo=None):
        self.archivo = archivo or ruta("jarvis.db")
        self.lock = threading.RLock()
        self.db = sqlite3.connect(self.archivo, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        with self.lock:
            self.db.executescript(ESQUEMA)
            self.db.commit()
        self._migrar_memoria_vieja()

    def _ejecutar(self, sql, params=(), uno=False, todos=False):
        with self.lock:
            cur = self.db.execute(sql, params)
            if uno:
                return cur.fetchone()
            if todos:
                return cur.fetchall()
            self.db.commit()
            return cur

    def _migrar_memoria_vieja(self):
        """Los datos de memoria.json (versiones anteriores) pasan a la base de datos una sola vez."""
        viejo = ruta("memoria.json")
        if not os.path.exists(viejo) or os.path.exists(viejo + ".migrado"):
            return
        try:
            for dato in json.load(open(viejo, encoding="utf-8")):
                self.aprender(str(dato), "dato", "memoria anterior")
            os.replace(viejo, viejo + ".migrado")
        except Exception as e:
            log.warning("No pude migrar memoria.json: %s", e)

    # ------------------------------------------------------------------ conocimiento
    def aprender(self, texto, tipo="dato", fuente="conversación"):
        """Guarda algo nuevo. Si ya sabía algo casi igual, lo actualiza en vez de duplicarlo. Devuelve True si es nuevo."""
        texto = " ".join(str(texto).split()).strip(" .")
        if len(texto) < 4:
            return False
        tipo = tipo if tipo in ("dato", "preferencia", "correccion", "habito") else "dato"
        n = normalizar(texto)
        for fila in self._ejecutar("SELECT id, texto FROM conocimiento", todos=True):
            if difflib.SequenceMatcher(None, n, normalizar(fila["texto"])).ratio() > 0.82:
                self._ejecutar("UPDATE conocimiento SET texto=?, tipo=?, usado=? WHERE id=?",
                               (texto, tipo, ahora(), fila["id"]))
                return False
        self._ejecutar("INSERT INTO conocimiento(tipo, texto, fuente, creado, usado) VALUES(?,?,?,?,?)",
                       (tipo, texto, fuente, ahora(), ahora()))
        log.info("Aprendí (%s): %s", tipo, texto)
        return True

    def olvidar(self, texto):
        n = normalizar(texto)
        mejor, puntos = None, 0.0
        for fila in self._ejecutar("SELECT id, texto FROM conocimiento", todos=True):
            t = normalizar(fila["texto"])
            p = 1.0 if n and n in t else difflib.SequenceMatcher(None, n, t).ratio()
            if p > puntos:
                mejor, puntos = fila, p
        if mejor and puntos > 0.55:
            self._ejecutar("DELETE FROM conocimiento WHERE id=?", (mejor["id"],))
            return mejor["texto"]
        return None

    def borrar_conocimiento(self, ident):
        self._ejecutar("DELETE FROM conocimiento WHERE id=?", (ident,))

    def todo_el_conocimiento(self):
        return [dict(f) for f in self._ejecutar("SELECT * FROM conocimiento ORDER BY usos DESC, usado DESC", todos=True)]

    def relevantes(self, consulta, k=10):
        """Lo que JARVIS sabe que tiene que ver con lo que pides ahora (más lo más usado)."""
        filas = self._ejecutar("SELECT * FROM conocimiento", todos=True)
        if not filas:
            return []
        clave = palabras(consulta)
        hoy = datetime.datetime.now()

        def puntaje(f):
            comunes = len(clave & palabras(f["texto"]))
            try:
                dias = (hoy - datetime.datetime.fromisoformat(f["usado"] or f["creado"])).days
            except Exception:
                dias = 30
            base = 3.0 * comunes + 0.15 * min(f["usos"], 20) + max(0.0, 1.0 - dias / 30)
            if f["tipo"] in ("preferencia", "correccion"):
                base += 0.8          # cómo te gustan las cosas pesa siempre
            return base
        elegidos = sorted(filas, key=puntaje, reverse=True)[:k]
        with self.lock:
            for f in elegidos:
                if clave & palabras(f["texto"]):
                    self.db.execute("UPDATE conocimiento SET usos=usos+1, usado=? WHERE id=?", (ahora(), f["id"]))
            self.db.commit()
        return [f["texto"] for f in elegidos]

    # ------------------------------------------------------------------ conversaciones
    def registrar_conversacion(self, usuario, jarvis, acciones=None, origen="voz", motor=""):
        self._ejecutar("INSERT INTO conversacion(fecha, origen, usuario, jarvis, acciones, motor) VALUES(?,?,?,?,?,?)",
                       (ahora(), origen, usuario, jarvis, json.dumps(acciones or [], ensure_ascii=False), motor))

    def ultimas_conversaciones(self, n=6):
        filas = self._ejecutar("SELECT * FROM conversacion ORDER BY id DESC LIMIT ?", (n,), todos=True)
        return [dict(f) for f in reversed(filas)]

    def conversaciones_de(self, dias=1):
        desde = (datetime.datetime.now() - datetime.timedelta(days=dias)).isoformat(timespec="seconds")
        return [dict(f) for f in self._ejecutar("SELECT * FROM conversacion WHERE fecha>=? ORDER BY id", (desde,), todos=True)]

    # ------------------------------------------------------------------ patrones (órdenes que se vuelven reflejos)
    def registrar_patron(self, frase, acciones, respuesta=""):
        """Cuenta cuántas veces una frase terminó en las mismas acciones. A la 2.ª vez queda aprendida."""
        if not acciones or any(a.get("tipo") not in REPETIBLES for a in acciones):
            return False
        clave = normalizar(frase)
        if len(clave) < 3 or DEICTICAS.search(clave):
            return False
        texto = json.dumps(acciones, ensure_ascii=False, sort_keys=True)
        fila = self._ejecutar("SELECT * FROM patrones WHERE frase=?", (clave,), uno=True)
        if fila and fila["acciones"] == texto:
            self._ejecutar("UPDATE patrones SET veces=veces+1, ultima=?, respuesta=? WHERE frase=?",
                           (ahora(), respuesta or fila["respuesta"], clave))
            veces = fila["veces"] + 1
        else:
            self._ejecutar("INSERT OR REPLACE INTO patrones(frase, acciones, respuesta, veces, ultima, activo) "
                           "VALUES(?,?,?,1,?,1)", (clave, texto, respuesta, ahora()))
            veces = 1
        if veces == VECES_PARA_APRENDER:
            log.info("Aprendí la orden «%s»", frase)
            return True
        return False

    def buscar_patron(self, frase):
        clave = normalizar(frase)
        fila = self._ejecutar("SELECT * FROM patrones WHERE frase=? AND activo=1 AND veces>=?",
                              (clave, VECES_PARA_APRENDER), uno=True)
        if not fila and len(clave) > 8:
            # tolera pequeñas diferencias de la transcripción ("abre mi musica" / "abre mi música pues")
            activas = self._ejecutar("SELECT frase FROM patrones WHERE activo=1 AND veces>=?", (VECES_PARA_APRENDER,), todos=True)
            cerca = difflib.get_close_matches(clave, [f["frase"] for f in activas], n=1, cutoff=0.9)
            if cerca:
                fila = self._ejecutar("SELECT * FROM patrones WHERE frase=?", (cerca[0],), uno=True)
        if not fila:
            return None
        return {"respuesta": fila["respuesta"] or "", "acciones": json.loads(fila["acciones"]), "frase": fila["frase"]}

    def desactivar_patron(self, frase):
        self._ejecutar("UPDATE patrones SET activo=0, veces=0 WHERE frase=?", (normalizar(frase),))

    def patrones(self):
        return [dict(f) for f in self._ejecutar("SELECT * FROM patrones WHERE veces>=? AND activo=1 ORDER BY veces DESC",
                                                (VECES_PARA_APRENDER,), todos=True)]

    # ------------------------------------------------------------------ lecciones (lo que tú aprendes)
    def agregar_leccion(self, tema, contenido):
        tema, contenido = str(tema).strip()[:120], str(contenido).strip()[:1200]
        if not tema or not contenido:
            return
        existe = self._ejecutar("SELECT id FROM lecciones WHERE lower(tema)=lower(?)", (tema,), uno=True)
        if existe:
            self._ejecutar("UPDATE lecciones SET contenido=?, fecha=? WHERE id=?", (contenido, ahora(), existe["id"]))
        else:
            self._ejecutar("INSERT INTO lecciones(fecha, tema, contenido) VALUES(?,?,?)", (ahora(), tema, contenido))

    def lecciones(self, dias=None, limite=50):
        if dias:
            desde = (datetime.datetime.now() - datetime.timedelta(days=dias)).isoformat(timespec="seconds")
            filas = self._ejecutar("SELECT * FROM lecciones WHERE fecha>=? ORDER BY id DESC LIMIT ?", (desde, limite), todos=True)
        else:
            filas = self._ejecutar("SELECT * FROM lecciones ORDER BY id DESC LIMIT ?", (limite,), todos=True)
        return [dict(f) for f in filas]

    def para_repasar(self, n=3):
        """Elige lecciones para repasar: primero las menos repasadas."""
        filas = [dict(f) for f in self._ejecutar("SELECT * FROM lecciones ORDER BY repasos ASC, id DESC LIMIT 12", todos=True)]
        elegidas = random.sample(filas, min(n, len(filas)))
        with self.lock:
            for f in elegidas:
                self.db.execute("UPDATE lecciones SET repasos=repasos+1, ultimo_repaso=? WHERE id=?", (ahora(), f["id"]))
            self.db.commit()
        return elegidas

    def borrar_leccion(self, ident):
        self._ejecutar("DELETE FROM lecciones WHERE id=?", (ident,))

    # ------------------------------------------------------------------ resumen
    def estadisticas(self):
        cuenta = lambda t, w="": self._ejecutar(f"SELECT COUNT(*) c FROM {t} {w}", uno=True)["c"]
        return {"conocimiento": cuenta("conocimiento"), "conversaciones": cuenta("conversacion"),
                "ordenes": cuenta("patrones", f"WHERE veces>={VECES_PARA_APRENDER} AND activo=1"),
                "lecciones": cuenta("lecciones")}
