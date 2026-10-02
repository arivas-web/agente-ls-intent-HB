"""Simulación de calibración (SOLO LECTURA, no escribe nada): cuántas cuentas elegibles salen en cada código
según saturación / semivida / umbrales de intención. Imprime solo recuentos."""
import copy
from collections import Counter, defaultdict
from datetime import datetime, timezone
from .config import load
from .db.conn import connect
from .recalc import compute_company
from .scoring.signals import Signal

SCENARIOS = {
    "base (sat50, semivida14, tiers 50/20)": {},
    "sat30": {"saturation": 30},
    "sat20": {"saturation": 20},
    "sat30 + semivida30": {"saturation": 30, "half_life_days": 30},
    "sat20 + semivida30": {"saturation": 20, "half_life_days": 30},
    "sat30 + semivida30 + tiers 40/15": {"saturation": 30, "half_life_days": 30, "tiers": {1: 40, 2: 15}},
}
MOVE = ["A1", "A2", "B1", "B2", "C1", "C2"]


def main():
    base = {k: load(v) for k, v in {"fit": "fit", "eng": "engagement", "int": "intent", "persona": "persona",
                                    "matrix": "priority_matrix", "url": "url_scoring"}.items()}
    excluded = set(load("assignment")["excluded_statuses"])
    now = datetime.now(timezone.utc)
    with connect() as conn:
        cos = [dict(zip(("hs_id", "target_market", "proveedor", "pais", "status", "tipo"), r)) for r in conn.execute(
            "select hs_id,target_market,proveedor,pais,status,tipo_de_contacto from companies")]
        cts = defaultdict(list)
        for r in conn.execute("select hs_id,company_hs_id,email,cargo_icp,phones,linkedin_url,email_bounced,excluded from contacts"):
            cts[r[1]].append(dict(zip(("hs_id", "company", "email", "cargo_icp", "phones", "linkedin_url",
                                       "email_bounced", "excluded"), r)))
        sigs = defaultdict(list)
        for r in conn.execute("select company_hs_id,contact_hs_id,kind,type,object_key,occurred_at,points_raw,meta "
                              "from signals where occurred_at > now() - interval '400 days'"):
            sigs[r[0]].append(Signal(r[1], r[2], r[3], r[5], float(r[6]), r[4], r[0], r[7] or {}))
    elig = [c for c in cos if c["status"] not in excluded]
    print("empresas totales:", len(cos), "| elegibles por estado:", len(elig))
    for name, change in SCENARIOS.items():
        cfgs = copy.deepcopy(base)
        cfgs["int"].update(change)
        cnt = Counter()
        for c in elig:
            r = compute_company(c, cts.get(c["hs_id"], []), sigs.get(c["hs_id"], []), cfgs, now)
            cnt[r["priority"]] += 1
        move = sum(cnt[k] for k in MOVE)
        print(f"\n## {name}\n   movimiento (A1,A2,B1,B2,C1,C2): {move} | " +
              " ".join(f"{k}={cnt[k]}" for k in MOVE + ['A3', 'B3', 'C3']))


if __name__ == "__main__":
    main()
