"""Resultado de llamada (vt_call_outcome en la empresa, lo rellena la SDR) -> tabla call_outcomes."""
import unicodedata

VALID = {"no_contesta", "no_interesado", "mal_timing", "ya_tiene_proveedor", "seguimiento", "reunion"}


def normalize_outcome(v):
    t = unicodedata.normalize("NFKD", v or "").encode("ascii", "ignore").decode().lower().strip().replace(" ", "_")
    return t if t in VALID else None


def record_outcomes(conn, company_outcomes):
    """company_outcomes: {company_id: valor de HubSpot}. Inserta solo cuando el valor cambió respecto al último registrado."""
    new = 0
    for cid, raw in company_outcomes.items():
        oc = normalize_outcome(raw)
        if not oc:
            continue
        last = conn.execute("select outcome from call_outcomes where company_hs_id = %s order by at desc limit 1", (cid,)).fetchone()
        if last and last[0] == oc:
            continue
        sdr = conn.execute("""select a.sdr from weekly_assignments a join weekly_drafts d on d.id = a.draft_id
                              where a.company_hs_id = %s and not a.removed order by d.week desc limit 1""", (cid,)).fetchone()
        conn.execute("insert into call_outcomes(company_hs_id, sdr, at, outcome) values (%s,%s,now(),%s)",
                     (cid, sdr[0] if sdr else None, oc))
        new += 1
    return new
