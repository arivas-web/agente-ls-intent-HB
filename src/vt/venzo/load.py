"""Carga del CSV más reciente de data/venzo/ -> Supabase. Usa config/venzo_mapping.yaml (se rellena tras revisar el CSV).
Casado con HubSpot: CIF > dominio > nombre; lo dudoso va a venzo_review. No imprime datos comerciales (solo recuentos)."""
import csv
import glob
import json
import os
from datetime import date, datetime
from ..config import ROOT, load
from ..db.conn import connect
from .match import Matcher


def newest_csv(folder):
    files = glob.glob(os.path.join(ROOT, folder, "*.csv"))
    return max(files, key=os.path.getmtime) if files else None


def read_rows(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        sample = f.read(4096)
        f.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=";,\t|")
        except csv.Error:
            dialect = csv.excel
        return list(csv.DictReader(f, dialect=dialect))


def parse_date(v):
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%y"):
        try:
            return datetime.strptime((v or "").strip(), fmt).date()
        except ValueError:
            pass
    return None


def normalize_status(v, status_map):
    t = (v or "").strip().lower()
    for key, norm in status_map.items():
        if key.lower() == t:
            return norm
    return None


def map_row(raw, cols, status_map):
    g = lambda k: raw.get(cols[k]) if cols.get(k) else None
    return {"cif": g("cif"), "domain": g("domain"), "name": g("name"), "id": g("opportunity_id"), "stage": g("stage"),
            "status_norm": normalize_status(g("status"), status_map), "loss_reason": g("loss_reason"),
            "opened_at": parse_date(g("opened_at")), "closed_at": parse_date(g("closed_at")),
            "last_management": g("notes"), "last_management_at": parse_date(g("last_activity"))}


def main():
    cfg = load("venzo_mapping")
    cols = cfg["columns"]
    if not any(cols.values()):
        print("config/venzo_mapping.yaml aún sin rellenar: primero hay que proponer y confirmar el mapeo de columnas.")
        return
    path = newest_csv(cfg["folder"])
    if not path:
        print("No hay CSV en", cfg["folder"])
        return
    rows = [map_row(r, cols, cfg.get("status_map", {})) for r in read_rows(path)]
    with connect() as conn:
        cos = [dict(zip(("hs_id", "cif", "domain", "name"), r)) for r in conn.execute("select hs_id, cif, domain, name from companies")]
        m = Matcher(cos)
        imp = conn.execute("insert into venzo_imports(file, rows) values (%s,%s) returning id", (os.path.basename(path), len(rows))).fetchone()[0]
        ok = review = none = 0
        for r in rows:
            res = m.match(r)
            rid = conn.execute("""insert into venzo_rows(import_id, raw, company_hs_id, match_method, match_confidence)
                                  values (%s,%s,%s,%s,%s) returning id""",
                               (imp, json.dumps({k: str(v) for k, v in r.items() if v}), res["hs_id"],
                                res["method"] if res["method"] in ("cif", "dominio", "nombre") else "ninguno", res["confidence"])).fetchone()[0]
            if res["review"]:
                conn.execute("insert into venzo_review(venzo_row_id, candidates) values (%s,%s)", (rid, json.dumps(res["candidates"])))
                review += 1
            elif res["hs_id"]:
                ok += 1
                if r["id"]:
                    conn.execute("""insert into opportunities(id, company_hs_id, stage, status, status_norm, loss_reason, opened_at,
                                    closed_at, last_management, last_management_at, origin)
                                    values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'inbound')
                                    on conflict (id) do update set company_hs_id = excluded.company_hs_id, stage = excluded.stage,
                                    status_norm = excluded.status_norm, loss_reason = excluded.loss_reason, closed_at = excluded.closed_at,
                                    last_management = excluded.last_management, last_management_at = excluded.last_management_at""",
                                 (r["id"], res["hs_id"], r["stage"], r["status_norm"], r["status_norm"], r["loss_reason"],
                                  r["opened_at"], r["closed_at"], r["last_management"], r["last_management_at"]))
            else:
                none += 1
        # Origen de la oportunidad: control > puntuada > alerta (14 días antes) > inbound.
        conn.execute("""update opportunities o set origin = case
            when exists (select 1 from weekly_assignments a join weekly_drafts d on d.id = a.draft_id
                         where a.company_hs_id = o.company_hs_id and a.is_control and not a.removed and d.week <= o.opened_at) then 'control'
            when exists (select 1 from weekly_assignments a join weekly_drafts d on d.id = a.draft_id
                         where a.company_hs_id = o.company_hs_id and not a.is_control and not a.removed and d.week <= o.opened_at) then 'puntuada'
            when exists (select 1 from alerts_sent s where s.company_hs_id = o.company_hs_id
                         and s.sent_at::date between o.opened_at - 14 and o.opened_at) then 'alerta'
            else 'inbound' end where o.opened_at is not null""")
        conn.commit()
    print(f"Venzo: {len(rows)} filas | casadas: {ok} | a revisión: {review} | sin coincidencia: {none}")


if __name__ == "__main__":
    main()
