"""Ingesta de HubSpot -> Supabase (solo LECTURA de HubSpot). Imprime solo recuentos."""
import json
from datetime import datetime, timezone
from ..config import load
from ..db.batch import Batch
from ..db.conn import connect
from ..hubspot.client import HubSpotClient
from .history import signals_from_history, parse_ts


def iter_objects(c, object_type, props, history=None, associations=None):
    after = None
    while True:
        params = {"limit": 50 if history else 100, "properties": ",".join(props)}
        if history:
            params["propertiesWithHistory"] = ",".join(history)
        if associations:
            params["associations"] = associations
        if after:
            params["after"] = after
        st, body = c.get(f"/crm/v3/objects/{object_type}", **params)
        if st != 200:
            raise SystemExit(f"HubSpot {object_type}: HTTP {st} ({(body or {}).get('category')})")
        yield from body.get("results", [])
        after = ((body.get("paging") or {}).get("next") or {}).get("after")
        if not after:
            return


CO_SQL = """insert into companies(hs_id,name,domain,target_market,proveedor,pais,status,tipo_de_contacto,last_activity_at,updated_at)
   values (%s,%s,%s,%s,%s,%s,%s,%s,%s,now())
   on conflict (hs_id) do update set name=excluded.name, domain=excluded.domain,
   target_market=excluded.target_market, proveedor=excluded.proveedor, pais=excluded.pais,
   status=excluded.status, tipo_de_contacto=excluded.tipo_de_contacto,
   last_activity_at=excluded.last_activity_at, updated_at=now()"""
CT_SQL = """insert into contacts(hs_id,company_hs_id,email,cargo_icp,phones,linkedin_url,email_bounced,excluded,exclusion_reason,updated_at)
   values (%s,%s,%s,%s,%s,%s,%s,%s,%s,now())
   on conflict (hs_id) do update set company_hs_id=excluded.company_hs_id, email=excluded.email,
   cargo_icp=excluded.cargo_icp, phones=excluded.phones, linkedin_url=excluded.linkedin_url,
   email_bounced=excluded.email_bounced, excluded=excluded.excluded,
   exclusion_reason=excluded.exclusion_reason, updated_at=now()"""
SIG_SQL = """insert into signals(company_hs_id,contact_hs_id,kind,type,object_key,occurred_at,points_raw,source,meta)
   values (%s,%s,%s,%s,%s,%s,%s,'hubspot_history',%s)
   on conflict (contact_hs_id,kind,type,object_key,day) do nothing"""


def main():
    props_cfg, url_cfg, eng_cfg = load("hubspot_properties"), load("url_scoring"), load("engagement")
    co, ct, act = props_cfg["company"], props_cfg["contact"], props_cfg["contact_activity"]
    excluded_types = set(props_cfg["excluded_contact_types"])
    c = HubSpotClient()

    company_props = ["name", "domain", co["target_market"], co["proveedor_actual"], co["ubicacion"],
                     co["estado_prospeccion"], co["tipo_de_contacto"]] + props_cfg["company_activity"]
    contact_props = ["email", ct["cargo"], *ct["telefono"], ct["linkedin_url"],
                     act["email_optout"], act["email_bounce"]]
    history = [act["last_url"], act["visits"], act["email_clicks"], act["email_optout"], act["email_last_replied"]]

    with connect() as conn:
        n_co = 0
        cob = Batch(conn, CO_SQL)
        co_excluded = {}
        for r in iter_objects(c, "companies", company_props):
            p = r["properties"]
            acts = [x for x in (p.get(k) for k in props_cfg["company_activity"]) if x]
            last = max((parse_ts(x) for x in acts), default=None)
            tipo = p.get(co["tipo_de_contacto"])
            co_excluded[r["id"]] = tipo in excluded_types
            cob.add((r["id"], p.get("name"), p.get("domain"), p.get(co["target_market"]),
                     p.get(co["proveedor_actual"]), p.get(co["ubicacion"]), p.get(co["estado_prospeccion"]),
                     tipo, last))
            n_co += 1
        cob.flush()
        conn.commit()
        print("empresas:", n_co)

        n_ct = n_sig = 0
        ctb, sgb = Batch(conn, CT_SQL), Batch(conn, SIG_SQL)
        for r in iter_objects(c, "contacts", contact_props, history=history, associations="companies"):
            p = r["properties"]
            assoc = ((r.get("associations") or {}).get("companies") or {}).get("results") or []
            company_id = assoc[0]["id"] if assoc else None
            email = (p.get("email") or "").lower()
            reason = None
            if email.endswith("@visualtrans.com"):
                reason = "interno"
            elif company_id and co_excluded.get(company_id):
                reason = "tipo_de_contacto_empresa"
            phones = [p.get(k) for k in ct["telefono"] if p.get(k)]
            if company_id is None:
                continue                                    # contacto sin empresa: no puntúa
            ctb.add((r["id"], company_id, email, p.get(ct["cargo"]), phones, p.get(ct["linkedin_url"]),
                     str(p.get(act["email_bounce"]) or "0") not in ("0", "", "None"), reason is not None, reason))
            n_ct += 1
            if reason:
                continue                                    # excluidos: sin señales
            for s in signals_from_history(r["id"], company_id, r.get("propertiesWithHistory") or {},
                                          url_cfg, eng_cfg, act):
                sgb.add((s.company_id, s.contact_id, s.kind, s.type, s.object_key, s.at, s.points,
                         json.dumps(s.meta)))
                n_sig += 1
            if n_ct % 1000 == 0:
                ctb.flush(); sgb.flush(); conn.commit()
                print("contactos:", n_ct, "señales:", n_sig, flush=True)
        ctb.flush(); sgb.flush(); conn.commit()
        print("contactos:", n_ct, "señales procesadas:", n_sig)


if __name__ == "__main__":
    main()
