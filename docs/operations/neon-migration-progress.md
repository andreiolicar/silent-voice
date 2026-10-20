# Silent Voice — Neon and Render production rollout

## Architecture

- Frontend: Render Static Site `silent-voice-site`, branch `deploy/static-frontend`.
- API: Render Free Node service `silent-voice-api`, Oregon, health check `/api/health`.
- Database: Neon Free project `Silent Voice` (`steep-boat-84776146`), production branch, Ohio.
- Public URL: https://www.silentvoice.com.br; administration at `/admin`.
- Static-site rewrite `/api/*` → `https://silent-voice-api.onrender.com/api/*`, before the SPA rewrite. Verified with GET, POST, PATCH, session cookies and SSE. No third-party cookie dependency or additional custom domain.
- Backend secrets exist only in Render environment. Pooled PostgreSQL connection for runtime; direct connection for advisory-locked, checksum-verified migrations.

## Migration completed 2026-10-20

A consistent private SQLite backup was created before import. Imported 1 admin, 1 lead and 1 idempotent submission. All original row fields, IDs, dates and password hashes compared equal afterward. No existing data was overwritten; old sessions intentionally require login again. SQLite remains only in legacy backup/import tooling and regression fixtures. Production uses PostgreSQL exclusively.

## Validation

- Temporary Neon branch: migrations twice, all four imported tables, repeat-safe import, conflict rollback, sessions across server recreation, concurrent receipts/status changes, filters and notes passed.
- Local suite: 83 Node tests passed, 1 external-database test explicitly skipped in the ordinary offline suite; 89 UI tests passed. The skipped integration test passed separately against real Neon.
- `npm run typecheck` and `npm run build`: passed.
- Production through the actual domain: health 200, login/secure cookie/CSRF, existing contact visible, lead capture and duplicate retry, status change, note, real GLM-4.5-Flash streaming response, and logout invalidation passed.
- Safari: login and dashboard at the public domain passed with a temporary validation account. Original administrator credentials remain unchanged.
- Production test rows and temporary account are removed after verification; original rows are retained.

## Operations

Render Free sleeps when idle; the first request can take 50 seconds or more. Neon may also suspend idle compute. No paid instance, disk or Render Postgres was created. Data persists independently of backend restarts in Neon. Startup failures are sanitized so connection strings and provider credentials are not logged.

Deploys follow commits on `deploy/static-frontend`. The checked-in render.yaml mirrors both services; it is not a newly applied duplicate Blueprint. Existing UI and the mobile work are preserved. For recovery, use Neon restore within the plan's retention or a private PostgreSQL dump; never copy live SQLite files as a PostgreSQL backup.
