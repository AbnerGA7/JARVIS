# -*- coding: utf-8 -*-
"""Notificaciones de Windows (aparecen en la esquina y en el centro de notificaciones)."""
import threading
from config import log, ICONO, ES_WINDOWS


def notificar(titulo, mensaje, url=None):
    if not ES_WINDOWS:
        return

    def _mostrar():
        try:
            from winotify import Notification, audio
            n = Notification(app_id="J.A.R.V.I.S.", title=titulo, msg=mensaje[:250], icon=ICONO, duration="short")
            n.set_audio(audio.Reminder, loop=False)
            if url:
                n.add_actions(label="Abrir", launch=url)
            n.show()
        except Exception as e:
            log.info("Sin notificación de Windows: %s", e)
    threading.Thread(target=_mostrar, daemon=True).start()
