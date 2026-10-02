"""¿Estamos recogiendo toda la actividad que HubSpot tiene? Compara recuentos de HubSpot con las señales guardadas.
Solo imprime números."""
from datetime import datetime, timedelta, timezone
from .db.conn import connect
from .hubspot.client import HubSpotClient


def ms(days):
    return str(int((datetime.now(timezone.utc) - timedelta(days=days)).timestamp() * 1000))


def hs_count(c, filters):
    st, b = c.search("contacts", {"filterGroups": [{"filters": filters}], "limit": 1})
    return (b or {}).get("total") if st == 200 else f"HTTP {st}"


def main():
    c = HubSpotClient()
    print("## HubSpot: contactos con actividad (ventanas 30/90/365 días)")
    for label, prop in (("clic en email", "hs_email_last_click_date"), ("apertura email", "hs_email_last_open_date"),
                        ("visita web (última sesión)", "hs_analytics_last_visit_timestamp"),
                        ("respuesta a email comercial", "hs_sales_email_last_replied")):
        print(f"  {label}:", [hs_count(c, [{"propertyName": prop, "operator": "GTE", "value": ms(d)}]) for d in (30, 90, 365)])
    print("  con algún clic histórico:", hs_count(c, [{"propertyName": "hs_email_click", "operator": "GT", "value": "0"}]))
    print("  con alguna visita histórica:", hs_count(c, [{"propertyName": "hs_analytics_num_visits", "operator": "GT", "value": "0"}]))
    print("\n## Nuestra base: contactos distintos con señal (30/90/365 días)")
    with connect() as conn:
        for label, typ in (("email_click", "email_click"), ("web_visit", "web_visit"), ("reply_detected", "reply_detected"), ("session", "session")):
            out = []
            for d in (30, 90, 365):
                out.append(conn.execute("select count(distinct contact_hs_id) from signals where type = %s and occurred_at > now() - make_interval(days => %s)", (typ, d)).fetchone()[0])
            print(f"  {label}:", out)
        print("  contactos totales / excluidos:", conn.execute("select count(*), count(*) filter (where excluded) from contacts").fetchone())
        print("  señales por tipo (todas):", conn.execute("select type, count(*) from signals group by 1 order by 2 desc").fetchall())



def hs_ids(c, prop, days):
    """IDs de contactos con la fecha `prop` dentro de los últimos `days` días (paginado)."""
    ids, after = [], None
    while True:
        body = {"filterGroups": [{"filters": [{"propertyName": prop, "operator": "GTE", "value": ms(days)}]}],
                "limit": 100, "properties": ["email"]}
        if after:
            body["after"] = after
        st, b = c.search("contacts", body)
        if st != 200:
            return ids
        ids += [r["id"] for r in b.get("results", [])]
        after = ((b.get("paging") or {}).get("next") or {}).get("after")
        if not after or len(ids) >= 5000:
            return ids


def breakdown():
    """Para cada contacto con actividad en HubSpot (30 días): ¿por qué está o no en nuestras señales?"""
    c = HubSpotClient()
    print("\n## Desglose: contactos con actividad en HubSpot (30 días) y qué pasa con ellos en nuestra base")
    with connect() as conn:
        info = {r[0]: (r[1], r[2]) for r in conn.execute("select hs_id, excluded, exclusion_reason from contacts")}
        for label, prop, typ in (("clic en email", "hs_email_last_click_date", "email_click"),
                                 ("visita web", "hs_analytics_last_visit_timestamp", "session")):
            ids = hs_ids(c, prop, 30)
            not_in_db = [i for i in ids if i not in info]
            excl = [i for i in ids if i in info and info[i][0]]
            ok = [i for i in ids if i in info and not info[i][0]]
            with_sig = 0
            if ok:
                with_sig = conn.execute("select count(distinct contact_hs_id) from signals where type = %s and contact_hs_id = any(%s) "
                                        "and occurred_at > now() - interval '30 days'", (typ, ok)).fetchone()[0]
            reasons = {}
            for i in excl:
                reasons[info[i][1]] = reasons.get(info[i][1], 0) + 1
            print(f"  {label}: HubSpot={len(ids)} | sin empresa asociada={len(not_in_db)} | excluidos={len(excl)} {reasons} | "
                  f"elegibles={len(ok)} -> con señal en nuestra base={with_sig}")


if __name__ == "__main__":
    main()
    breakdown()
