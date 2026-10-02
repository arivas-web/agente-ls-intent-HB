from datetime import datetime


def decay(points, at, now, half_life_days):
    """puntos × 0,5^(días / semivida). Señales futuras no cuentan todavía."""
    days = (now - at).total_seconds() / 86400
    if days < 0:
        return 0.0
    return points * 0.5 ** (days / half_life_days)


def normalize(raw, saturation):
    """Normaliza a 0-100 con tope."""
    return max(0.0, min(100.0, raw / saturation * 100))
