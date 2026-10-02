# PLAN.md — Lead scoring + intención de compra (Visual Trans)

Estado: **BORRADOR, pendiente de aprobación.** No se crea código, propiedades ni tablas hasta que se apruebe.
Fecha: 2026-10-02.

## 0. Decisiones ya tomadas

| Tema | Decisión |
|---|---|
| Base de datos | Supabase (Postgres), proyecto `bmudirnikpgcqfieyueq` (URL en `config/database.yaml`; la contraseña va solo en `DATABASE_URL`) |
| Acceso al dashboard | Supabase Auth con email y contraseña (un único usuario, creado por ti en Supabase). Sustituye a `DASHBOARD_PASSWORD`. El dashboard sigue desplegado en Vercel (Supabase no aloja Next.js) |
| Claude | Suscripción Claude Pro, **sin API de pago**. Se usa Claude Code en modo no interactivo (`claude -p`) en GitHub Actions con un token OAuth de suscripción (`CLAUDE_CODE_OAUTH_TOKEN`, generado con `claude setup-token`) |
| Email | Gmail por SMTP con contraseña de aplicación (gratis, sin dominio que verificar). Límite ~500 envíos/día, de sobra |
| Destinatario y remitente | Todo a `arivas@visualtrans.com`, enviado desde `arivas@visualms.com` (ambos en `config/email.yaml`) |
| Envío semanal | **Lunes 08:00 (España)**, solo si la semana está validada |
| Oportunidades | Solo Venzo. Los deals de HubSpot NO se usan como oportunidades (su pipeline es el de prospección) |
| Tráfico interno | Solo se excluyen contactos `@visualtrans.com`. Sin IPs de oficina |
| Exclusión por tipo de contacto (empresa) | Excluir: Asociaciones del sector, Cliente, Competencia, Partner, Prensa. Mantener: Precliente, No target y vacío |
| Cargo | `cargo_icp` (desplegable). Si está vacío, `jobtitle` clasificado con Claude |
| Propiedades confirmadas | Ver `config/hubspot_properties.yaml` |

Confirmado: **10 cuentas por SDR y semana**.
Supuestos míos, a confirmar o cambiar en YAML (no en código): borrador el **jueves 09:00** (da margen hasta el lunes); alertas de **09:00 a 18:00** España, lunes a viernes.
Descartado: las visitas de empresas anónimas por IP (las gestiona otro sistema). No se lee `buyer_intent` ni se aplica el 50 % de esa señal.

## 1. Lo que NO se puede hacer, o no está verificado

Se marca cada punto con su alternativa.

1. **Visitas web por contacto con URL y fecha.** La Events API devuelve 403 con nuestro token (comprobado). **Solución sin permisos nuevos (comprobada con la sonda):** el historial de propiedades de contacto (`propertiesWithHistory`) de `hs_analytics_last_url`, `hs_analytics_last_timestamp` y `hs_analytics_num_page_views` guarda una versión con fecha por cada visita registrada (hasta 45 versiones por propiedad, desde oct-2025 en la muestra). Se leen en la ingesta y se guardan como señales en Supabase. Limitaciones: tope de ~45 versiones por contacto (la ingesta diaria y la de las alertas por hora van acumulando el histórico propio) y puede haber páginas intermedias de una misma sesión que HubSpot no registre.
2. **Visitas de empresas anónimas por IP.** Fuera de alcance por decisión tuya (otro sistema). No se pide el permiso `buyer_intent.read`.
3. **Email.** Decisión: no se usa la API de emails (403, y no se ampliará). Clics: se derivan del historial de `hs_email_click` y `hs_email_last_click_date` (misma técnica que las visitas). Aperturas puntúan 0, bajas con `hs_email_optout`.
4. **LinkedIn.** No hay propiedades de actividad de LinkedIn en HubSpot. Fuente alternativa propuesta: exportación manual de analíticas de la página de empresa y de Enrique a CSV en `data/linkedin/`. Nunca se extraen datos de Emma, Cecilio ni Laura. Mientras no exista el CSV, el bloque queda a 0.
5. **Webinars, descargas de contenido, newsletter, ferias.** No he localizado aún las propiedades o formularios que las representan. Se preguntarán una a una en la Fase 1.
6. **Respuestas a email: positiva / no interesa / ahora no.** Sin acceso al contenido de los emails, Claude no puede clasificarlas. Solución: propiedades de empresa que rellena la SDR (a crear): `vt_respuesta_email` (Positiva · No interesa · Ahora no) y `vt_reactivar_en` (fecha). Reglas: Positiva +25 de intención; No interesa → intención 0 y congelada 90 días; Ahora no → congelar y reactivar con +20 en la fecha. Como pista de que hubo respuesta se usa el historial de `hs_sales_email_last_replied`, que sirve para avisar a la SDR de que clasifique.
7. **Supabase gratuito** pausa el proyecto tras 7 días sin actividad. El recálculo diario lo evita.
8. **Tamaño de datos.** No sé aún cuántas empresas y contactos hay. Lo mido en la Fase 1 antes de fijar el diseño de la ingesta (límites de la API y tiempos de Actions).
9. **Zona horaria.** Los cron de GitHub van en UTC. El cambio de hora de invierno es el 25 de octubre de 2026. Cada trabajo se programa a dos horas UTC (verano e invierno) y el código sale si no son las horas correctas en `Europe/Madrid`. Así no hay que tocar nada en marzo ni en octubre.

## 2. Propiedades `vt_` a crear (HubSpot, escritura solo con `--apply`)

Empresa:
- `vt_fit_score` (número), `vt_fit_tier` (A/B/C)
- `vt_engagement_score` (número), `vt_intent_score` (número), `vt_intent_tier` (1/2/3), `vt_intent_velocity` (número)
- `vt_priority` (A1…C), `vt_best_contact` (id o texto)
- `vt_why_now`, `vt_angle` (texto largo), `vt_ai_intent` (1–5), `vt_ai_intent_reason`
- `vt_missing_decision_maker` (sí/no)
- `vt_assigned_sdr`, `vt_assigned_week`, `vt_control_group` (sí/no)
- `vt_last_alert_at`, `vt_last_alert_reason`
- `vt_respuesta_email` (Positiva · No interesa · Ahora no) y `vt_reactivar_en` (fecha): las rellena la SDR
- `vt_call_outcome` (no contesta · no interesado · mal timing · ya tiene proveedor · seguimiento · reunión)
- `vt_scored_at`

Contacto:
- `vt_persona_score`, `vt_cargo_categoria`, `vt_buyer_persona_sugerido`, `vt_buyer_persona` (confirma la SDR)

Reglas: nunca borrar propiedades ni registros; cada escritura queda en `change_log` (valor anterior, nuevo, fecha, modo); dry-run por defecto; `--apply` explícito; solo se escribe si cambia el valor.
No se crean workflows, tareas ni se usa el scoring nativo.

## 3. Estructura del repositorio

```
config/
  hubspot_properties.yaml   # nombres confirmados (ya existe)
  fit.yaml                  # puntos target market / proveedor / ubicación + mapeo aproximado de proveedores
  engagement.yaml           # pesos, topes, semivida 30, multiplicadores
  intent.yaml               # pesos, semivida 14, tiers, congelaciones
  persona.yaml              # cargo (cargo_icp -> puntos), contactabilidad
  priority_matrix.yaml      # A1,A2,B1 llamar · A3 nutrir · C fuera
  assignment.yaml           # N por SDR, SDR (ids de owner), estados excluidos, inactividad 6 meses
  alerts.yaml               # horario, ventana 7 días, reglas
  email.yaml                # destinatarios, remitente
  url_scoring.yaml          # reglas por URL (aportado)
  venzo_mapping.yaml        # columnas del CSV -> campos (propuesto tras ver el CSV)
  claude.yaml               # modelos, tokens, reintentos
data/venzo/                 # CSV de Venzo (repo privado, nunca en logs)
src/vt/
  hubspot/ (cliente, lectura, escritura dry-run, change_log)
  venzo/ (carga, casado CIF>dominio>nombre, informe de dudosos)
  scoring/ (fit, engagement, intent, persona, matrix, decay, url_rules)
  claude/ (resúmenes, disparadores, cargos, noticias, informe; JSON validado + reintento)
  assign/ (reparto equilibrado, grupo de control)
  email/ (plantillas, SMTP)
  alerts/ · reports/ · db/ (migraciones, repositorios)
  cli.py
tests/
.github/workflows/ (recalc, draft, send, alerts, monthly)
dashboard/                  # Next.js en Vercel
```

Python 3.12 para el motor y Next.js (TypeScript) para el dashboard. Tests con pytest.

## 4. Esquema de la base de datos (Supabase)

- `companies` — `hs_id`, nombre, dominio, CIF, atributos de Fit leídos, `cif_norm`, `name_norm`
- `contacts` — `hs_id`, `company_hs_id`, `email`, `cargo_icp`, `excluded` (por tipo de contacto o @visualtrans.com), contactabilidad
- `signals` — `id`, `company_id`, `contact_id`, `kind` (engagement/intent), `type`, `object_key` (URL, contenido), `occurred_at`, `points_raw`, `source`. Único por (contacto, tipo, objeto, día) para la regla “una vez al día”
- `company_scores_daily` — `date`, `company_id`, fit, engagement, intent, tier, velocity, priority, `breakdown` jsonb
- `contact_scores_daily` — `date`, `contact_id`, persona total y desglose
- `weekly_drafts` — `week`, `status` (pendiente · validado · enviado · no_enviado), `created_at`, `validated_at`
- `weekly_assignments` — `draft_id`, `company_id`, `sdr`, `rank`, `is_control`, `origin` (scored/control/manual), `claude_json`, `edited_by_user` (quitada / sustituida / cambio de SDR / añadida), `edit_log`
- `alerts_sent` — `company_id`, `reason`, `sent_at`, `sdr`
- `call_outcomes` — `company_id`, `contact_id`, `outcome`, `at`, `sdr`
- `venzo_imports` — `file`, `loaded_at`, filas
- `venzo_rows` — campos mapeados, `company_id`, `match_method` (cif/dominio/nombre/ninguno), `match_confidence`
- `venzo_review` — filas dudosas pendientes de decisión
- `opportunities` — de Venzo: etapa, estado, motivo de pérdida, fechas, `origin`
- `url_classification` — `url` → categoría (noticias clasificadas una vez por Claude)
- `freezes` — congelaciones (“no interesa” 90 días, “ahora no, en X meses” con reactivación +20)
- `change_log` — toda escritura a HubSpot
- `config_snapshots` — hash/versión del YAML usado en cada foto diaria (para auditar)

RLS activado en todas las tablas. El motor usa `DATABASE_URL`; el dashboard solo accede por rutas de servidor (sin clave pública).

## 5. Fórmulas (como se especificaron, sin modificar)

- **Fit:** `max(0, target + proveedor + ubicación) / 43 × 100`; tiers A ≥ 70 · B 45–69 · C < 45. Si hay varios target markets, el más alto. Proveedor: coincidencia exacta y luego aproximada (normalización, sin acentos/URLs); los que no casen caen en “Cualquier otro” = 0 y salen en un informe para que decidas. Ubicación: España 5 · México 2 · Portugal 1 · resto LATAM 1 · otros 0. Desglose guardado con el valor que genera cada bloque.
- **Engagement:** señales por contacto → decaimiento `0,5^(días/30)` → multiplicador por cargo (CEO ×1,5 · COO/logística ×1,3 · informática ×1,2 · resto ×1,0) → amplitud (1 → ×1,0 · 2 → ×1,3 · 3+ → ×1,6) → normalizar 0–100 con tope. Mismo contenido y acción: una vez al día.
- **Intención:** igual con semivida 14 días; bonus y reglas de congelación. `vt_intent_velocity` = hoy − hace 7 días (de las fotos diarias).
- **Persona:** cargo hasta 40 + engagement personal hasta 40 + contactabilidad hasta 20. Buyer persona no puntúa.
- **Matriz (ajustada 2026-10-02):** código = fit + intención. A1, A2, B1 → llamar. B2, C1, C2 → llamar con movimiento (hay intención real aunque el perfil sea flojo). A3 → relleno sin intención: solo cubre huecos del reparto, marcado como tal. B3 → espera. C3 → fuera. Orden: A1, A2, B1, B2, C1, C2, A3; dentro de cada código, por velocidad de intención. Motivo: la web recibe pocas visitas (35 empresas con señal en 30 días), así que solo con A1/A2/B1 saldrían unas 4 cuentas a la semana.

Los topes y el método de normalización a 0–100 (p. ej. valor de saturación) se fijan en los YAML. **Los valores concretos de saturación no los dijiste:** propongo calibrarlos con los datos reales de la Fase 1 y enseñártelos antes de congelarlos.

## 6. Calendario de crons (UTC, con doble hora para el cambio horario)

| Trabajo | España | Cron verano (CEST, UTC+2) | Cron invierno (CET, UTC+1) |
|---|---|---|---|
| Recálculo diario | 03:00 | `0 1 * * *` | `0 2 * * *` |
| Borrador semanal (jueves) | 09:00 | `0 7 * * 4` | `0 8 * * 4` |
| Envío semanal (lunes) | 08:00 | `0 6 * * 1` | `0 7 * * 1` |
| Aviso “no validado” | 08:00 lunes | mismo job de envío | mismo job de envío |
| Alertas | cada hora 09:00–18:00 L–V | `0 7-16 * * 1-5` | `0 8-17 * * 1-5` |
| Informe mensual | día 1, 07:00 | `0 5 1 * *` | `0 6 1 * *` |

El código comprueba la hora en `Europe/Madrid` y no hace nada si no corresponde. GitHub puede retrasar los cron unos minutos.

## 7. Fases y entregables

- **Fase 1:** ingesta HubSpot + Venzo, 4 puntuaciones con desglose, matriz, base de datos, escritura `vt_` en dry-run. *Antes:* verificar con el token real las limitaciones del apartado 1 y proponerte el mapeo del CSV de Venzo.
- **Fase 2:** dashboard (Semana siguiente y Cuentas), inicio de sesión con Supabase Auth (un solo usuario). Las tablas llevan RLS que solo permite a ese usuario leer y escribir; el motor usa `DATABASE_URL`.
- **Fase 3:** borrador, validación, capa de Claude, emails.
- **Fase 4:** alertas por hora.
- **Fase 5:** Oportunidades, Tasas, resultado de llamada, informe mensual.

Tests: cada puntuación, normalización de URLs (ya existe `tests/test_url_scoring.py` según tu mensaje; **no está en el repo ni lo encuentro en Drive**; necesito su contenido junto con `config/url_scoring.yaml`), casado con Venzo y reparto equilibrado. README con secretos y cómo subir un CSV nuevo.

## 8. Riesgos

| Riesgo | Mitigación |
|---|---|
| Faltan datos por contacto (visitas, clics) | Verificación en Fase 1; plan B del apartado 1 |
| Casado Venzo con falsos positivos | Orden CIF > dominio > nombre; dudas a informe de revisión, nunca asumidas |
| Datos comerciales en logs | Logs sin nombres ni emails; Actions con `::add-mask::`; repositorio privado; el CSV no se imprime |
| Claude devuelve JSON inválido | Esquema estricto, validación, 2 reintentos; si falla, la cuenta va sin texto y se marca |
| Límites de uso de Claude Pro (ventanas de 5 h y tope semanal compartido con tu uso manual) | La carga es pequeña (20 cuentas/semana + disparadores A/B + clasificaciones puntuales). Un solo proceso por vez, caché por hash de entrada, reintento diferido y aviso por email si se agota. El token OAuth puede caducar o revocarse: aviso por email si falla la autenticación |
| Coste de Claude | Resúmenes solo para el borrador (20 cuentas por semana), disparadores solo A y B una vez por semana, caché por hash de entrada |
| Límites de la API de HubSpot (100 req/10 s) | Lectura por lotes y reintentos con espera |
| Pesos mal calibrados | El informe mensual solo propone; nunca se aplican solos |
| Desborde de una propiedad confirmada | Si un nombre desaparece de la API, el motor se detiene y te avisa; no busca otro |
| Cuentas sin actividad en 6 meses | Asignación aleatoria y grupo de control; la semilla se guarda para reproducirlo |
| Pérdida del envío semanal | Si no está validado el lunes a las 08:00, no se envía y llega un aviso |

## 8b. Claude sin API: cómo se adapta
- `src/vt/claude/` llama a `claude -p --output-format json` con un esquema JSON estricto y valida la salida; si no valida, reintenta (máx. 2).
- Sin herramientas salvo la búsqueda web en los disparadores externos. Si la búsqueda no está disponible con la suscripción, los disparadores externos se desactivan por YAML (los pesos quedan sin usar).
- Las funciones que no necesitan Claude (puntuaciones, reparto, alertas) no dependen de él: si Claude falla, el borrador sale igual, sin resúmenes, y te lo aviso.
- A verificar al empezar la Fase 3: que el uso programado de una suscripción Pro desde Actions esté permitido en sus condiciones y aguante la carga. Si no, plan B: ejecutar la capa de Claude manualmente desde una sesión de Claude Code y guardar el JSON en Supabase.

## 9. Secretos

`HUBSPOT_TOKEN`, `CLAUDE_CODE_OAUTH_TOKEN`, `DATABASE_URL` (usar la cadena del *connection pooler* de Supabase: los runners de GitHub son solo IPv4 y la conexión directa de Supabase es IPv6), `GMAIL_USER` (arivas@visualms.com), `GMAIL_APP_PASSWORD`, `NEXT_PUBLIC_SUPABASE_URL` y `NEXT_PUBLIC_SUPABASE_ANON_KEY` (públicas por diseño) y `SUPABASE_SERVICE_ROLE_KEY` (solo servidor, solo Vercel), en lugar de `DASHBOARD_PASSWORD`.
Para Gmail hay que activar la verificación en dos pasos en la cuenta de envío y crear una contraseña de aplicación.

## 10. Pendiente de ti antes de implementar

1. Aprobar o ajustar este plan y los supuestos de la sección 0 (jueves 09:00, N = 25, alertas 09:00–18:00).
2. Contraseña de aplicación de `arivas@visualms.com` (requiere verificación en dos pasos). Si esa cuenta es Google Workspace, el administrador debe permitirlo.
3. Subir `config/url_scoring.yaml`, `tests/test_url_scoring.py` y el CSV de Venzo (mínimo unas filas anonimizadas).
4. ~~Reconectar HubSpot con `buyer_intent.read`~~ — descartado.
5. Nombres de las propiedades de webinars, descargas, newsletter y ferias (los pregunto una a una en la Fase 1).
6. Identificar a Emma y Laura en HubSpot (owner IDs) para el reparto.
