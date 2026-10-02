"""Claude vía Claude Code en modo no interactivo (suscripción, sin API de pago).
JSON estricto, validado, con reintento. Si Claude no está disponible, el flujo sigue sin textos."""
import json
import re
import subprocess
from ..config import load


class ClaudeUnavailable(Exception):
    pass


def cli_runner(prompt, cfg):
    """Ejecuta `claude -p` y devuelve el texto de la respuesta."""
    try:
        p = subprocess.run([cfg["command"], "-p", prompt, "--output-format", "json"],
                           capture_output=True, text=True, timeout=cfg["timeout_seconds"])
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        raise ClaudeUnavailable(type(e).__name__)
    if p.returncode != 0:
        raise ClaudeUnavailable(f"exit {p.returncode}")          # no se imprime stderr (puede contener datos)
    try:
        out = json.loads(p.stdout)
    except ValueError:
        return p.stdout
    if isinstance(out, dict):
        if out.get("is_error"):
            raise ClaudeUnavailable("claude_error")
        return out.get("result", "")
    return p.stdout


def extract_json(text):
    """Primer objeto JSON de un texto (admite bloques ```json)."""
    text = re.sub(r"```(?:json)?", "", text or "")
    start = text.find("{")
    while start != -1:
        depth = 0
        for i in range(start, len(text)):
            depth += text[i] == "{"
            depth -= text[i] == "}"
            if depth == 0:
                try:
                    return json.loads(text[start:i + 1])
                except ValueError:
                    break
        start = text.find("{", start + 1)
    raise ValueError("sin JSON")


def validate_summary(d, cfg, contact_ids=()):
    """Valida y normaliza el JSON de resumen de cuenta. Lanza ValueError si no cumple."""
    lim = cfg["max_chars"]
    out = {}
    for k in ("vt_why_now", "vt_angle", "contact_justification", "vt_ai_intent_reason"):
        v = d.get(k)
        if not isinstance(v, str) or not v.strip():
            raise ValueError(f"falta {k}")
        out[k] = v.strip()[:lim[k]]
    n = d.get("vt_ai_intent")
    if isinstance(n, str) and n.strip().isdigit():
        n = int(n)
    if not isinstance(n, int) or isinstance(n, bool) or not 1 <= n <= 5:
        raise ValueError("vt_ai_intent debe ser 1-5")
    out["vt_ai_intent"] = n
    bp = d.get("buyer_persona_suggested") or {}
    if not isinstance(bp, dict):
        raise ValueError("buyer_persona_suggested")
    out["buyer_persona_suggested"] = {str(k): v for k, v in bp.items()
                                      if v in ("decisor", "impulsor", "stopper") and (not contact_ids or str(k) in contact_ids)}
    return out


def ask_json(prompt, validator, runner=None, cfg=None):
    """Pregunta y valida; reintenta con aviso del error. Devuelve el dict validado."""
    cfg = cfg or load("claude")
    runner = runner or (lambda p: cli_runner(p, cfg))
    last = None
    for attempt in range(cfg["retries"] + 1):
        q = prompt if last is None else f"{prompt}\n\nTu respuesta anterior no fue válida ({last}). Responde SOLO con el JSON pedido."
        try:
            return validator(extract_json(runner(q)))
        except ValueError as e:
            last = str(e)
    raise ValueError(f"JSON no válido tras reintentos: {last}")


SUMMARY_PROMPT = """Eres analista de ventas B2B de Visual Trans (software para transitarios, aduanas, consignatarios y operadores logísticos).
Prepara el resumen de UNA cuenta para la SDR que la llamará esta semana. Usa SOLO los datos dados; no inventes hechos.
Responde SOLO con un JSON con estas claves exactas:
- "vt_why_now": 2-3 líneas, por qué llamar ahora (señales concretas y fechas).
- "vt_angle": ángulo de la llamada y objeción probable.
- "contact_justification": por qué llamar primero a ese contacto.
- "vt_ai_intent": entero 1-5 (1 = sin intención, 5 = intención muy alta).
- "vt_ai_intent_reason": motivo del número anterior.
- "buyer_persona_suggested": objeto {{id_contacto: "decisor"|"impulsor"|"stopper"}} para los contactos dados.

DATOS DE LA CUENTA:
{context}
"""


def summarize_account(context_text, contact_ids, runner=None, cfg=None):
    cfg = cfg or load("claude")
    return ask_json(SUMMARY_PROMPT.format(context=context_text),
                    lambda d: validate_summary(d, cfg, contact_ids), runner, cfg)
