"""Contexto compacto de una cuenta para Claude (cronología reciente, contactos, Venzo, interés)."""


def build_context(company, signals, contacts, venzo, interests):
    """company: dict; signals: [{at,type,object,points,contact_id}] ya ordenadas; contacts: [{id,email,cargo,persona}];
    venzo: [{stage,status,loss_reason,last_management,last_management_at}]; interests: {producto, vertical}."""
    L = [f"Empresa: {company.get('name')} | País: {company.get('pais')} | Target: {company.get('target_market')} | "
         f"Proveedor actual: {company.get('proveedor')} | Estado: {company.get('status')}",
         f"Puntuaciones: fit {company.get('fit')} ({company.get('fit_tier')}), engagement {company.get('engagement')}, "
         f"intención {company.get('intent')} (velocidad {company.get('velocity')}), prioridad {company.get('code')}"]
    if interests.get("producto") or interests.get("vertical"):
        L.append(f"Interés: producto={interests.get('producto')} vertical={interests.get('vertical')}")
    L.append("Cronología reciente (más nueva primero):")
    L += [f"- {s['at'][:10]} {s['type']} {s['object']} ({s['points']} pts, contacto {s['contact_id']})" for s in signals[:15]] \
        or ["- sin actividad reciente registrada"]
    L.append("Contactos (id | email | cargo | persona score):")
    L += [f"- {c['id']} | {c['email']} | {c.get('cargo') or 'sin cargo'} | {c.get('persona')}" for c in contacts[:8]]
    L.append("Gestiones comerciales de Venzo:")
    L += [f"- {v.get('last_management_at')}: {v.get('stage')} / {v.get('status')} {v.get('loss_reason') or ''} "
          f"{v.get('last_management') or ''}" for v in venzo[:5]] or ["- ninguna registrada"]
    return "\n".join(L)
