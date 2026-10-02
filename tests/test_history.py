from datetime import timezone
from vt.ingest.history import signals_from_history

P = {"last_url": "hs_analytics_last_url", "visits": "hs_analytics_num_visits", "email_clicks": "hs_email_click",
     "email_optout": "hs_email_optout", "email_last_replied": "hs_sales_email_last_replied"}


def v(value, ts):
    return {"value": value, "timestamp": ts}


def test_visitas_clics_y_sesiones(url_cfg, eng_cfg):
    ph = {
        "hs_analytics_last_url": [v("https://visualtrans.com/legal/", "2026-09-30T10:00:00Z"),
                                  v("https://visualtrans.com/precios/?utm=x", "2026-09-29T09:00:00Z"),
                                  v("https://visualtrans.com/noticias/webinar-consignatarios/", "2026-09-28T09:00:00Z")],
        "hs_email_click": [v("3", "2026-09-27T08:00:00Z"), v("1", "2026-09-20T08:00:00Z")],
        "hs_analytics_num_visits": [v("5", "2026-09-29T09:00:00Z"), v("4", "2026-09-28T09:00:00Z")],
        "hs_email_optout": [v("true", "2026-09-01T00:00:00Z")],
        "hs_sales_email_last_replied": [v("1790000000000", "2026-09-10T00:00:00Z")],
    }
    s = signals_from_history("c1", "k1", ph, url_cfg, eng_cfg, P)
    by = {}
    for x in s:
        by.setdefault(x.type, []).append(x)
    assert len(by["web_visit"]) == 2                       # /legal/ no puntúa
    precios = next(x for x in by["web_visit"] if x.object_key == "/precios/")
    assert (precios.kind, precios.points, precios.at.tzinfo) == ("intent", 20, timezone.utc)
    web = next(x for x in by["web_visit"] if x.kind == "engagement")
    assert web.meta["cap_key"] == "web_noticias"
    assert [x.points for x in by["email_click"]] == [3] and by["email_click"][0].meta["clicks"] == 2
    assert len(by["session"]) == 1 and by["unsubscribe"][0].points == -15
    assert by["reply_detected"][0].points == 0


def test_sin_historial(url_cfg, eng_cfg):
    assert signals_from_history("c", "k", {}, url_cfg, eng_cfg, P) == []
