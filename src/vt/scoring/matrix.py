def priority(fit_tier, intent_tier, matrix_cfg):
    code = "C" if fit_tier == "C" else f"{fit_tier}{intent_tier}"
    return code, matrix_cfg["actions"].get(code, "espera")
