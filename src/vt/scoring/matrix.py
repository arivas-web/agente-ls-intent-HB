def priority(fit_tier, intent_tier, matrix_cfg):
    """Devuelve (código, acción). Código = fit_tier + intent_tier."""
    code = f"{fit_tier}{intent_tier}"
    return code, matrix_cfg["actions"].get(code, "espera")


def rank(code, matrix_cfg):
    """Posición en el orden de reparto (menor = antes). Los códigos fuera de la lista no se reparten."""
    order = matrix_cfg["order"]
    return order.index(code) if code in order else len(order)
