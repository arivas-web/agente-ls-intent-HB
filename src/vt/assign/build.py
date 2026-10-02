"""Reparto semanal equilibrado por nivel. Funciones puras (sin base de datos), testeables."""
import random
from ..scoring.matrix import rank

TIER_ORDER = {"A": 0, "B": 1, "C": 2}


def is_eligible(c, cfg, open_opportunity_ids=frozenset()):
    """c: dict con status, tipo_de_contacto, hs_id."""
    if c.get("internal"):
        return False
    if c.get("status") in set(cfg["excluded_statuses"]):
        return False
    if c.get("tipo_de_contacto") in set(cfg.get("excluded_company_types", [])):
        return False
    return c["hs_id"] not in open_opportunity_ids


def rank_candidates(rows, matrix_cfg):
    """rows: dict con hs_id, code, velocity, fit, engagement. Orden: código -> velocidad -> fit -> engagement.
    Solo entran los códigos del orden de reparto (A1..A3)."""
    ok = [r for r in rows if r["code"] in matrix_cfg["order"]]
    return sorted(ok, key=lambda r: (rank(r["code"], matrix_cfg), -(r["velocity"] or 0), -(r["fit"] or 0),
                                     -(r["engagement"] or 0), r["hs_id"]))


def pick_control(pool, k_per_sdr, n_sdrs, seed, extra=0):
    """Sorteo aleatorio reproducible (seed) del grupo de control. Devuelve (elegidas, reservas para sustituir)."""
    rng = random.Random(seed)
    k = k_per_sdr * n_sdrs
    order = rng.sample(pool, len(pool))
    return order[:k], order[k:k + extra]


def balance(ranked, sdrs, n_per_sdr):
    """Reparte la lista ordenada entre SDR EQUILIBRANDO POR NIVEL: cada cuenta va a la SDR con menos
    cuentas totales; en empate, a la que menos tiene de ese código (la diferencia por código es ≤ 1)."""
    total = {s: 0 for s in sdrs}
    by_code = {s: {} for s in sdrs}
    out = {s: [] for s in sdrs}
    for r in ranked:
        open_sdrs = [s for s in sdrs if total[s] < n_per_sdr]
        if not open_sdrs:
            break
        sdr = min(open_sdrs, key=lambda s: (by_code[s].get(r["code"], 0), total[s], sdrs.index(s)))
        out[sdr].append(r)
        total[sdr] += 1
        by_code[sdr][r["code"]] = by_code[sdr].get(r["code"], 0) + 1
    return out


def build_draft(rows, cfg, matrix_cfg, seed, open_opportunity_ids=frozenset(), inactive_ids=frozenset()):
    """rows: todas las empresas con puntuación (code, velocity, fit, fit_tier, engagement, status, tipo, hs_id).
    Devuelve (asignaciones, candidatos). Cada asignación: {hs_id, sdr, rank, is_control, origin, code}."""
    sdrs = list(cfg["sdrs"].keys())
    n = cfg["accounts_per_sdr_per_week"]
    k_ctrl = cfg.get("control_per_sdr", 0)
    elig = [r for r in rows if is_eligible(r, cfg, open_opportunity_ids)]
    min_tier = TIER_ORDER[cfg.get("control_min_fit_tier", "B")]
    pool = sorted([r for r in elig if r["hs_id"] in inactive_ids and TIER_ORDER.get(r["fit_tier"], 9) <= min_tier],
                  key=lambda r: r["hs_id"])
    control, control_reserve = pick_control(pool, k_ctrl, len(sdrs), seed, extra=10)
    control_ids = {r["hs_id"] for r in control}
    ranked = rank_candidates([r for r in elig if r["hs_id"] not in control_ids], matrix_cfg)
    scored = balance(ranked, sdrs, n - k_ctrl)
    assignments, used = [], set()
    for sdr in sdrs:
        for i, r in enumerate(scored[sdr], 1):
            assignments.append({"hs_id": r["hs_id"], "sdr": sdr, "rank": i, "is_control": False,
                                "origin": "scored", "code": r["code"]})
            used.add(r["hs_id"])
    # Control: se reparte alternando entre SDR (orden estable por id tras el sorteo).
    for i, r in enumerate(control):
        sdr = sdrs[i % len(sdrs)]
        pos = sum(1 for a in assignments if a["sdr"] == sdr) + 1
        assignments.append({"hs_id": r["hs_id"], "sdr": sdr, "rank": pos, "is_control": True,
                            "origin": "control", "code": r["code"]})
        used.add(r["hs_id"])
    candidates = [r for r in ranked if r["hs_id"] not in used][:cfg.get("candidate_pool_size", 60)]
    candidates += [{**r, "is_control_pool": True} for r in control_reserve]   # reservas de control (sustituciones)
    return assignments, candidates
