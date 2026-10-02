"""Refresco rápido para alertas: contactos de las cuentas de fit A (lectura de HubSpot por lotes)."""
import json
from ..config import load
from ..db.batch import Batch
from ..db.conn import connect
from ..hubspot.client import HubSpotClient
from .history import signals_from_history
from .hubspot_ingest import SIG_SQL


def main():
    props_cfg, url_cfg, eng_cfg = load("hubspot_properties"), load("url_scoring"), load("engagement")
    act = props_cfg["contact_activity"]
    history = [act["last_url"], act["visits"], act["email_clicks"], act["email_optout"], act["email_last_replied"]]
    c = HubSpotClient()
    with connect() as conn:
        rows = conn.execute("""select c.hs_id, c.company_hs_id from contacts c
            join company_scores_daily s on s.company_hs_id = c.company_hs_id
              and s.date = (select max(date) from company_scores_daily)
            join companies co on co.hs_id = c.company_hs_id
            where s.fit_tier = 'A' and not c.excluded and coalesce(co.status,'') not in ('Client','Discarded')""").fetchall()
        comp = {r[0]: r[1] for r in rows}
        ids = list(comp)
        sgb, n = Batch(conn, SIG_SQL), 0
        for i in range(0, len(ids), 50):
            body = {"properties": ["email"], "propertiesWithHistory": history,
                    "inputs": [{"id": x} for x in ids[i:i + 50]]}
            st, resp = c.request("POST", "/crm/v3/objects/contacts/batch/read", json=body)
            if st not in (200, 207):
                raise SystemExit(f"HubSpot batch/read: HTTP {st} ({(resp or {}).get('category')})")
            for r in (resp or {}).get("results", []):
                for s in signals_from_history(r["id"], comp[r["id"]], r.get("propertiesWithHistory") or {},
                                              url_cfg, eng_cfg, act):
                    sgb.add((s.company_id, s.contact_id, s.kind, s.type, s.object_key, s.at, s.points, json.dumps(s.meta)))
                    n += 1
        sgb.flush()
        conn.commit()
    print(f"Contactos de cuentas A refrescados: {len(ids)} | señales procesadas: {n}")


if __name__ == "__main__":
    main()
