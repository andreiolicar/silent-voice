-- Preserve original administrator identities and audit ownership. Passwords must be reset.
INSERT INTO auth_user (id, name, email, "emailVerified", "createdAt", "updatedAt", role, banned, "twoFactorEnabled")
SELECT id, 'Administrador', email, FALSE, created_at::timestamptz, created_at::timestamptz, 'admin', FALSE, FALSE
FROM admin_users
ON CONFLICT (id) DO NOTHING;

ALTER TABLE leads DROP CONSTRAINT IF EXISTS leads_status_updated_by_fkey;
ALTER TABLE leads ADD CONSTRAINT leads_status_updated_by_auth_fkey FOREIGN KEY (status_updated_by) REFERENCES auth_user(id);
ALTER TABLE lead_notes DROP CONSTRAINT IF EXISTS lead_notes_author_id_fkey;
ALTER TABLE lead_notes ADD CONSTRAINT lead_notes_author_auth_fkey FOREIGN KEY (author_id) REFERENCES auth_user(id);
DELETE FROM admin_sessions;
