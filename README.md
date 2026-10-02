# Lead scoring + intención de compra (Visual Trans)

Prioriza CUENTAS para Emma y Laura (HubSpot) con 4 puntuaciones (fit, engagement, intención, persona), una matriz de
prioridad y un reparto semanal medible contra un grupo de control. Estado: **Fase 1 completada** (ver `PLAN.md`).

## Arquitectura
HubSpot = fuente de datos y escaparate (solo lectura; escritura de propiedades `vt_` únicamente con `--apply`, hoy solo dry-run).
Toda la lógica está en este repositorio y se ejecuta con GitHub Actions. Datos en Supabase. Pesos, umbrales y listas en `config/*.yaml`.

## Secretos (GitHub: Settings > Secrets and variables > Actions)
| Secreto | Uso |
|---|---|
| `HUBSPOT_TOKEN` | Token de app privada de HubSpot (lectura de contactos y empresas) |
| `DATABASE_URL` | Cadena del *pooler* de Supabase (`postgresql://postgres.<ref>:<pass>@aws-0-<región>.pooler.supabase.com:5432/postgres`). La conexión directa NO sirve desde GitHub (solo IPv6) |
| `CLAUDE_CODE_OAUTH_TOKEN` | Token de tu suscripción (`claude setup-token`), para la capa de Claude (Fase 3) |
| `GMAIL_USER`, `GMAIL_APP_PASSWORD` | Envío de emails (Fase 3), cuenta con verificación en dos pasos |
Nunca pegues secretos en el chat ni en el código.

## Workflows (todos manuales por ahora)
- `probe.yml`: sonda de solo lectura de HubSpot (permisos, volumen, propietarios).
- `migrate.yml`: aplica `db/migrations/*.sql` (idempotente).
- `daily.yml`: migración + ingesta de HubSpot + recálculo.
- `recalc.yml`: solo recálculo sobre lo ya ingerido.
- `diag.yml`: recuentos agregados para calibrar (sin datos personales).
- `ci.yml`: tests en cada push.

## Cómo subir un CSV nuevo de Venzo
1. Copia el CSV a `data/venzo/` (repositorio privado). Se usa siempre el más reciente.
2. Rellena `config/venzo_mapping.yaml` (columnas del CSV). El casado con HubSpot es por CIF, luego dominio, luego nombre.
3. Las coincidencias dudosas no se asumen: salen en el informe de revisión.
Los datos comerciales no se imprimen en logs.

## Tests
`pip install -r requirements.txt && python -m pytest -q`
