from vt.hubspot.writer import ensure_properties, prop_payload, update_companies
from vt.config import load


class Fake:
    def __init__(self, existing=()):
        self.existing, self.calls = set(existing), []

    def get(self, path, **kw):
        return (200 if path.rsplit("/", 1)[1] in self.existing else 404), {}

    def request(self, method, path, **kw):
        self.calls.append((method, path))
        return 200, {}


def test_dry_run_no_escribe_nada():
    c = Fake(existing={"vt_fit_score"})
    missing = ensure_properties(c, apply=False)
    assert "vt_fit_score" not in missing and "vt_priority" in missing and c.calls == []
    log = []
    assert update_companies(c, {"1": {"vt_fit_score": 80, "vt_control_group": True}}, False,
                            lambda *a: log.append(a)) == 0
    assert c.calls == [] and log[0][4] == "dry-run"


def test_apply_crea_y_actualiza_por_lotes():
    c = Fake()
    ensure_properties(c, apply=True)
    n = len(load("vt_properties")["properties"])
    assert [m for m, _ in c.calls] == ["POST"] * n
    c.calls.clear()
    assert update_companies(c, {str(i): {"vt_fit_score": i} for i in range(250)}, True) == 250
    assert [p for _, p in c.calls] == ["/crm/v3/objects/companies/batch/update"] * 3


def test_nunca_hay_borrados():
    import inspect, vt.hubspot.writer as w
    assert "DELETE" not in inspect.getsource(w) and "archive" not in inspect.getsource(w).lower().replace("registros", "")


def test_payload_booleano_y_enum():
    cfg = load("vt_properties")
    b = prop_payload("vt_control_group", cfg["properties"]["vt_control_group"], cfg["group"])
    assert [o["value"] for o in b["options"]] == ["true", "false"]
    e = prop_payload("vt_priority", cfg["properties"]["vt_priority"], cfg["group"])
    assert len(e["options"]) == 9
