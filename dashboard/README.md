# Dashboard de prospección (Visual Trans)

Next.js 14 (App Router, TypeScript) para un único usuario (el dueño). Lee y edita datos de Supabase con la
**sesión del usuario** (Supabase Auth, email + contraseña); nunca usa la service role. Todas las tablas tienen
RLS con política para el rol `authenticated`.

## Variables de entorno

| Variable | Descripción |
|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | URL del proyecto Supabase |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Clave `anon` pública del proyecto |

Local: copia `.env.example` a `.env.local` y rellénalo. Después `npm install`, `npm run dev` (puerto 3000).
Scripts: `npm run build`, `npm test` (vitest, cálculos de tasas), `npm run typecheck`.
Las páginas son dinámicas (`force-dynamic`): el build no se conecta a Supabase.

## Crear el usuario

En Supabase: **Authentication > Users > Add user** (email + contraseña, marca "Auto Confirm User").
Desactiva el registro público (Authentication > Providers > Email > "Allow new users to sign up" = off)
para que solo exista ese usuario.

## Despliegue en Vercel

1. Importa el repositorio en Vercel.
2. **Root Directory = `dashboard`** (Framework: Next.js, detectado solo).
3. Añade las dos variables de entorno anteriores (Production y Preview).
4. Deploy. Entra en `/login` con el usuario creado.

## Secciones

- **Semana siguiente (`/`)**: validación del borrador semanal. Selector de borrador (por defecto el más reciente por `week`), una tabla por SDR (Emma, Laura) sin las cuentas `removed`, y detalle en `/cuenta/[id]?draft=ID`.
- **Cuentas (`/cuentas`)**: buscador por nombre/dominio paginado; ficha `/cuentas/[id]` con desglose, evolución histórica de fit/engagement/intención, asignaciones y llamadas.
- **Oportunidades (`/oportunidades`)**: datos de Venzo (`opportunities`), recuento por etapa, motivos de pérdida y lista filtrable (etapa, SDR, nivel de la matriz, origen).
- **Tasas (`/tasas`)**: tasas de contacto, reunión, oportunidad, ganada y perdida (sobre cuentas asignadas y sobre llamadas), alerta → reunión, tiempos medios, puntuadas vs control (lift) y desgloses por nivel, SDR y target market.

## Cómo funciona la validación

Cada borrador (`weekly_drafts`) nace en `pendiente_validar`. En estado pendiente o validado se puede editar; cada acción se anota en `weekly_assignments.edit_log` como `{at, action, detail}`:

- **Quitar**: `removed = true`.
- **Sustituir**: marca `removed` la cuenta y crea una asignación nueva para el mismo SDR con la siguiente fila de `draft_candidates` (rank mayor, mismo grupo puntuada/control, que no esté ya en el borrador). La nueva no tiene resumen de Claude.
- **Pasar a otro SDR**: cambia `sdr` y guarda `sdr_original` la primera vez.
- **Añadir manualmente**: buscador de empresa; `origin = 'manual'`, `added_manually = true` (si ya estaba quitada, se restaura).
- **Validar semana**: tras confirmar, `status = 'validado'` y `validated_at = now()`.

Si el borrador está `enviado` o `no_enviado`, todo queda en solo lectura. Se avisa si algún SDR no tiene 10 cuentas (`lib/config.ts`, `ACCOUNTS_PER_SDR`).

## Definición de las tasas (`lib/rates.ts`)

- Cuentas asignadas = `weekly_assignments` no `removed` de borradores `enviado`/`validado` con `week` dentro del periodo. El nivel es el `code` de `draft_candidates` (o, si falta, la `priority` de la última foto).
- Solo cuentan eventos dentro del periodo y no anteriores a la semana de asignación.
- Contacto = llamada con resultado distinto de `no_contesta`; reunión = `reunion`; oportunidad = abierta en el periodo; ganada/perdida = cerrada en el periodo.
- Si el denominador es 0 se muestra "—".


## Si Vercel no despliega (Hobby bloquea commits de otro autor)
Opción A (recomendada): workflow `deploy-dashboard.yml` con token. Secretos de GitHub: `VERCEL_TOKEN` (Vercel > Settings > Tokens),
`VERCEL_ORG_ID` y `VERCEL_PROJECT_ID` (en `.vercel/project.json` tras `vercel link`, o Project Settings > General).
En el proyecto de Vercel: Root Directory = `dashboard` y las variables `NEXT_PUBLIC_SUPABASE_URL` / `NEXT_PUBLIC_SUPABASE_ANON_KEY`.
Opción B: desde tu ordenador, en la carpeta `dashboard`: `npx vercel --prod`.
