# -*- coding: utf-8 -*-
"""
Reflejos de J.A.R.V.I.S.: órdenes comunes que se ejecutan al instante, sin pasar por la IA.
Incluye los comandos que el usuario le enseña ("aprender").
"""
import re, random, difflib
from config import normalizar

OK = ["Enseguida, {t}.", "Hecho.", "Como ordene, {t}.", "Al instante.", "Listo, {t}."]

# (patrón sobre texto normalizado, constructor de acciones)
REGLAS = [
    (r"^(que hora es|dime la hora|la hora)$", lambda m: [{"tipo": "hora", "valor": ""}]),
    (r"^(que (dia|fecha) es( hoy)?|dime la fecha|la fecha)$", lambda m: [{"tipo": "fecha", "valor": ""}]),
    (r"^(pausa|pon pausa|pausa la musica|pausa el video|continua|reanuda|play|dale play|sigue la musica)$",
     lambda m: [{"tipo": "media", "valor": "pausa"}]),
    (r"^(siguiente|siguiente cancion|pasa la cancion|cambia la cancion|otra cancion)$",
     lambda m: [{"tipo": "media", "valor": "siguiente"}]),
    (r"^(anterior|cancion anterior|regresa la cancion)$", lambda m: [{"tipo": "media", "valor": "anterior"}]),
    (r"^(sube|subele|aumenta)( el| al)? volumen$", lambda m: [{"tipo": "volumen", "valor": "subir"}]),
    (r"^(baja|bajale|disminuye)( el| al)? volumen$", lambda m: [{"tipo": "volumen", "valor": "bajar"}]),
    (r"^(silencia|silencio total|mutea|quita el sonido)( la pc| todo)?$", lambda m: [{"tipo": "volumen", "valor": "silenciar"}]),
    (r"^(pon |sube |baja )?(el )?volumen (al|a|en) (\d{1,3})( por ciento)?$",
     lambda m: [{"tipo": "volumen", "valor": m.group(4)}]),
    (r"^(pon |sube |baja )?(el )?brillo (al|a|en) (\d{1,3})( por ciento)?$",
     lambda m: [{"tipo": "brillo", "valor": m.group(4)}]),
    (r"^(toma|haz|saca) (una )?captura( de pantalla)?$", lambda m: [{"tipo": "captura", "valor": ""}]),
    (r"^(minimiza todo|muestra el escritorio|ve al escritorio)$", lambda m: [{"tipo": "ventana", "valor": "minimizar_todo"}]),
    (r"^(bloquea|bloquea la pc|bloquea la computadora|bloquea el equipo)$", lambda m: [{"tipo": "bloquear", "valor": ""}]),
]

ABRIR = re.compile(r"^(abre|abreme|abrir|inicia|ejecuta|lanza|pon|entra a|entra en|ve a)\s+(el |la |los |las |mi )?(.+)$")


MULETILLAS = re.compile(r"^(por favor |oye |activa |activar |pon |ponme |inicia |ejecuta |haz |el |la |los |las |mi |un |una )+")


def limpiar_muletillas(n):
    return MULETILLAS.sub("", n).replace(" por favor", "").strip()


class Reflejos:
    def __init__(self, cfg, comandos, apps):
        self.cfg = cfg
        self.comandos = comandos      # Almacen con {"frase": [acciones]}
        self.apps = apps              # IndiceApps

    def _ok(self):
        return random.choice(OK).format(t=self.cfg.get("trato", "señor"))

    def interpretar(self, orden):
        n = normalizar(orden)
        if not n:
            return None
        # 1) comandos aprendidos
        aprendidos = self.comandos.datos
        if aprendidos:
            claves = {limpiar_muletillas(normalizar(k)): k for k in aprendidos}
            parecido = difflib.get_close_matches(limpiar_muletillas(n), list(claves), n=1, cutoff=0.86)
            if parecido:
                return {"respuesta": self._ok(), "acciones": list(aprendidos[claves[parecido[0]]])}
        # 2) reflejos fijos
        for patron, hacer in REGLAS:
            m = re.match(patron, n)
            if m:
                acciones = hacer(m)
                directo = acciones[0]["tipo"] in ("hora", "fecha")
                return {"respuesta": "" if directo else self._ok(), "acciones": acciones}
        # 3) "abre X" cuando X es un sitio o una app conocida con seguridad
        m = ABRIR.match(n)
        if m:
            objetivo = m.group(3).strip()
            sitios = {normalizar(k): k for k in self.cfg.get("sitios", {})}
            if objetivo in sitios:
                return {"respuesta": f"Abriendo {sitios[objetivo].title()}.",
                        "acciones": [{"tipo": "abrir_web", "valor": sitios[objetivo]}]}
            if m.group(1) != "pon" and self.apps and self.apps.seguro(objetivo):
                return {"respuesta": f"Abriendo {objetivo}.", "acciones": [{"tipo": "abrir_app", "valor": objetivo}]}
        return None
