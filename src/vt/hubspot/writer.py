"""Escritura en HubSpot. DRY-RUN por defecto: con apply=False no se hace ninguna petición de escritura.
Nunca se borran registros ni propiedades."""
from ..config import load


def prop_payload(name, spec, group):
    p = {"name": name, "label": spec["label"], "type": spec["type"], "fieldType": spec["fieldType"],
         "groupName": group}
    if spec["type"] == "enumeration":
        if spec["fieldType"] == "booleancheckbox":
            p["options"] = [{"label": "Sí", "value": "true", "displayOrder": 0},
                            {"label": "No", "value": "false", "displayOrder": 1}]
        else:
            p["options"] = [{"label": str(o), "value": str(o), "displayOrder": i} for i, o in enumerate(spec["options"])]
    return p


def ensure_properties(client, apply=False, specs=None):
    """Crea las propiedades vt_ que falten. Devuelve la lista de nombres que se crean (o se crearían)."""
    cfg = specs or load("vt_properties")
    missing = []
    for name, spec in cfg["properties"].items():
        st, _ = client.get(f"/crm/v3/properties/companies/{name}")
        if st == 404:
            missing.append(name)
            if apply:
                st2, body = client.request("POST", "/crm/v3/properties/companies",
                                           json=prop_payload(name, spec, cfg["group"]))
                if st2 not in (200, 201):
                    raise RuntimeError(f"No se pudo crear {name}: HTTP {st2} ({(body or {}).get('category')})")
        elif st != 200:
            raise RuntimeError(f"Comprobando {name}: HTTP {st}")
    return missing


def update_companies(client, updates, apply=False, log=None, chunk=100):
    """updates: {company_id: {prop: value}}. log(company_id, prop, old, new, mode) para cada cambio."""
    mode = "apply" if apply else "dry-run"
    items = list(updates.items())
    for cid, props in items:
        for k, v in props.items():
            if log:
                log(cid, k, None, v, mode)
    if not apply:
        return 0
    done = 0
    for i in range(0, len(items), chunk):
        part = items[i:i + chunk]
        body = {"inputs": [{"id": cid, "properties": {k: _fmt(v) for k, v in p.items()}} for cid, p in part]}
        st, resp = client.request("POST", "/crm/v3/objects/companies/batch/update", json=body)
        if st not in (200, 201, 204):
            raise RuntimeError(f"batch update: HTTP {st} ({(resp or {}).get('category')})")
        done += len(part)
    return done


def _fmt(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    return "" if v is None else str(v)
