# Lead scoring + intención de compra (Visual Trans)

Prioriza CUENTAS para Emma y Laura (HubSpot) con 4 puntuaciones (fit, engagement, intención, persona), una matriz de
prioridad y un reparto semanal medible contra un grupo de control. Estado: **fases 1 a 5 implementadas** (ver `PLAN.md`). Pendiente de configuración: secretos de Gmail y Claude, despliegue del dashboard y CSV de Venzo.

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

## Calendario (cron en UTC con doble hora; el código decide con la hora de Madrid)
| Trabajo | Madrid | Workflow |
|---|---|---|
| Recálculo diario + sync (dry-run) | 03:00 | `daily.yml` |
| Borrador de la semana siguiente | jueves 09:00 | `draft.yml` |
| Envío a las SDR (solo si está validado) | lunes 08:00 | `send.yml` |
| Alertas | L-V 09:00-18:00, cada hora | `alerts.yml` |
| Informe mensual | día 1, 07:00 | `monthly.yml` |
| Carga de Venzo | al subir un CSV a `data/venzo/` | `venzo.yml` |

## Escritura en HubSpot
Siempre DRY-RUN salvo que pongas la variable de repositorio `VT_HUBSPOT_APPLY=true` (Settings > Secrets and variables > Actions > Variables)
o lances `sync.yml` a mano marcando "apply". Antes crea las propiedades `vt_` (lo hace el propio sync en modo real). Nunca se borra nada.
El token de HubSpot necesita permiso de escritura en empresas y en propiedades de empresa.

## Dashboard
Carpeta `dashboard/` (Next.js + Supabase Auth). Ver `dashboard/README.md`: Vercel con Root Directory `dashboard`, variables
`NEXT_PUBLIC_SUPABASE_URL` y `NEXT_PUBLIC_SUPABASE_ANON_KEY`, y un usuario creado en Supabase (Auth > Users).

## Workflows
Los manuales (`probe`, `migrate`, `recalc`, `diag`, `whatif`, `sync`) y los programados de arriba.
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
