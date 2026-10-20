# Silent Voice — PostgreSQL migration and production rollout

User authorized replacing runtime SQLite with Neon PostgreSQL, migrating existing data, and production deployment on free services. Preserve existing UI and unrelated edits. Render account currently wrong; no changes allowed in Alessandra's workspace.

1. Implement async data access, versioned migrations, preserve auth/session/idempotency semantics.
2. Validate against temporary Neon branch; back up local SQLite and import transactionally into production without overwriting conflicts.
3. Verify API end to end, full suite, typecheck, build. Keep local servers available.
4. Prepare free Render deployment; publish only in confirmed correct workspace. Await user account reconnection.

Interfaces: routes/auth/session store must await every database operation; transaction queries must stay on one connection. Existing SQLite fixtures remain regression coverage and import tooling only. Runtime requires DATABASE_URL (no silent SQLite fallback). Deployment uses same-origin API proxy to preserve strict cookies.
