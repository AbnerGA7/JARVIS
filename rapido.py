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
    (r"^((me )?(dices|digas|dime|das|des) )?(que hora es|la hora( que es)?|hora)( ahora)?$", lambda m: [{"tipo": "hora", "valor": ""}]),
    (r"^((me )?(dices|digas|dime) )?(que (dia|fecha) es( hoy)?|la fecha( de hoy)?|que dia es hoy)$",
     lambda m: [{"tipo": "fecha", "valor": ""}]),
    (r"^(pausa|pon pausa|pausa la musica|pausa el video|continua|reanuda|play|dale play|sigue la musica)$",
     lambda m: [{"tipo": "media", "valor": "pausa"}]),
    (r"^(siguiente|siguiente cancion|pasa la cancion|cambia la cancion|otra cancion)$",
     lambda m: [{"tipo": "media", "valor": "siguiente"}]),
    (r"^(anterior|cancion anterior|regresa la cancion)$", lambda m: [{"tipo": "media", "valor": "anterior"}]),
    (r"^(sube|subele|subir|subas|aumenta|aumentar)( el| al)? volumen$", lambda m: [{"tipo": "volumen", "valor": "subir"}]),
    (r"^(baja|bajale|bajar|bajes|disminuye|disminuir)( el| al)? volumen$", lambda m: [{"tipo": "volumen", "valor": "bajar"}]),
    (r"^(silencia|silencio total|mutea|quita el sonido)( la pc| todo)?$", lambda m: [{"tipo": "volumen", "valor": "silenciar"}]),
    (r"^((pon|poner|pongas|ponme|sube|subir|subas|baja|bajar|bajes|deja|dejes|cambia|cambiar) )?(el )?volumen "
     r"(al|a|en) (\d{1,3})( por ciento)?$", lambda m: [{"tipo": "volumen", "valor": m.group(5)}]),
    (r"^((pon|poner|pongas|ponme|sube|subir|subas|baja|bajar|bajes|deja|dejes|cambia|cambiar) )?(el )?brillo "
     r"(al|a|en) (\d{1,3})( por ciento)?$", lambda m: [{"tipo": "brillo", "valor": m.group(5)}]),
    (r"^(toma|haz|saca) (una )?captura( de pantalla)?$", lambda m: [{"tipo": "captura", "valor": ""}]),
    (r"^(minimiza todo|muestra el escritorio|ve al escritorio)$", lambda m: [{"tipo": "ventana", "valor": "minimizar_todo"}]),
    (r"^(bloquea|bloquea la pc|bloquea la computadora|bloquea el equipo)$", lambda m: [{"tipo": "bloquear", "valor": ""}]),
]

ABRIR = re.compile(r"^(abre|abreme|abras|abrir|inicia|inicies|ejecuta|ejecutes|lanza|pon|entra a|entra en|ve a|vayas a)"
                   r"\s+(el |la |los |las |mi )?(.+)$")
# formas educadas de pedir algo: se quitan antes de buscar un reflejo
CORTESIA = re.compile(r"^(oye |hey |ey |por favor |porfa )*((yo )?quiero que |necesito que |(me )?puedes |podrias |"
                      r"(me )?podrias |seria posible que |te pido que |hazme el favor de |ayudame a )?")


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
        n = CORTESIA.sub("", n, count=1).replace(" por favor", "").strip()
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
            if m.group(1) not in ("pon",) and self.apps and self.apps.seguro(objetivo):
                return {"respuesta": f"Abriendo {objetivo}.", "acciones": [{"tipo": "abrir_app", "valor": objetivo}]}
        return None
