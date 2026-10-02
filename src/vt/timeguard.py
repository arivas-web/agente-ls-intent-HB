"""Los cron de GitHub van en UTC. Cada trabajo se programa a las dos horas UTC posibles (verano/invierno)
y el código solo actúa si en Europe/Madrid es el momento correcto."""
import os
from datetime import datetime
from zoneinfo import ZoneInfo

MADRID = ZoneInfo("Europe/Madrid")
DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def madrid_now(now=None):
    return (now or datetime.now(MADRID)).astimezone(MADRID)


def in_window(weekdays, start, end, now=None):
    """start/end 'HH:MM' en hora de Madrid. Inclusivo en start, exclusivo en end."""
    n = madrid_now(now)
    hm = n.strftime("%H:%M")
    return DAYS[n.weekday()] in weekdays and start <= hm < end


def at_hour(weekday, hour, now=None):
    """True si en Madrid es ese día de la semana y esa hora (cualquier minuto)."""
    n = madrid_now(now)
    return DAYS[n.weekday()] == weekday and n.hour == hour


def forced():
    return os.environ.get("FORCE") == "1"
