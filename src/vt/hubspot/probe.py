"""Sonda de solo lectura: comprueba qué ofrece realmente la API con nuestro plan.
No imprime datos comerciales: solo recuentos, códigos de estado y nombres de propiedades."""
import json
import os
import sys
import yaml
from .client import HubSpotClient


def main():
    c = HubSpotClient()
    out = {}
    props_cfg = yaml.safe_load(open("config/hubspot_properties.yaml"))

    # 1. Propiedades confirmadas: ¿siguen existiendo?
    missing = []
    for obj, api in (("company", "companies"), ("contact", "contacts")):
        st, body = c.get(f"/crm/v3/properties/{api}")
        names = {p["name"] for p in (body or {}).get("results", [])}
        wanted = []
        for v in (props_cfg.get(obj) or {}).values():
            wanted += v if isinstance(v, list) else [v]
        missing += [f"{obj}.{w}" for w in wanted if w not in names]
        out[f"properties_{obj}_status"] = st
        out[f"properties_{obj}_count"] = len(names)
        out[f"vt_properties_existing_{obj}"] = sorted(n for n in names if n.startswith("vt_"))
    out["confirmed_properties_missing"] = missing

    # 2. Volumen
    for obj in ("companies", "contacts"):
        st, body = c.search(obj, {"limit": 1})
        out[f"total_{obj}"] = (body or {}).get("total"); out[f"total_{obj}_status"] = st

    # 3. Propietarios (Emma, Laura)
    st, body = c.get("/crm/v3/owners", limit=100)
    out["owners_status"] = st
    out["owners"] = [
        {"id": o["id"], "name": f'{o.get("firstName","")} {o.get("lastName","")}'.strip()}
        for o in (body or {}).get("results", [])
    ]

    # 4. Eventos por contacto (visitas web, clics de email)
    st, body = c.search("contacts", {
        "filterGroups": [{"filters": [{"propertyName": "hs_analytics_num_page_views", "operator": "GT", "value": "0"}]}],
        "limit": 1})
    cid = ((body or {}).get("results") or [{}])[0].get("id")
    out["sample_contact_with_pageviews_found"] = bool(cid)
    if cid:
        st, body = c.get("/events/v3/events", objectType="contact", objectId=cid, limit=5)
        out["events_api_status"] = st
        results = (body or {}).get("results", [])
        out["events_api_sample_types"] = sorted({e.get("eventType") for e in results})
        if st != 200 and body:
            out["events_api_error_category"] = body.get("category")
        st, body = c.get("/events/v3/events/event-types")
        out["event_types_status"] = st
        if st == 200:
            out["event_types"] = (body or {}).get("eventTypes", [])[:60]

    # 5. Actividad de email (objetos EMAIL) y reuniones/llamadas
    for obj in ("emails", "calls", "meetings"):
        st, body = c.get(f"/crm/v3/objects/{obj}", limit=1)
        out[f"{obj}_status"] = st

    # 6. Intent signals / de-anonymized: fuera de alcance por decisión del usuario.
    print(json.dumps(out, ensure_ascii=False, indent=2))
    summ = os.environ.get("GITHUB_STEP_SUMMARY")
    if summ:
        with open(summ, "a") as f:
            f.write("```json\n" + json.dumps(out, ensure_ascii=False, indent=2) + "\n```\n")
    sys.exit(1 if missing else 0)


if __name__ == "__main__":
    main()
