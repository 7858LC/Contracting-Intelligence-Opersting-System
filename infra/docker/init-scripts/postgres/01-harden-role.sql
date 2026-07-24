-- POSTGRES_USER (cios_user) becomes a real Postgres superuser in the official
-- postgres image, which bypasses row-level security unconditionally regardless
-- of FORCE ROW LEVEL SECURITY (see migration 007_force_rls). Postgres also
-- refuses to let the bootstrap superuser strip its own SUPERUSER attribute via
-- ALTER ROLE, so cios_user can't be fixed in place. Production RDS does not
-- have this problem: its master user is rds_superuser, not a true superuser.
--
-- Instead, cios_user stays superuser for migrations/schema ownership, and the
-- app's runtime connection uses this separate, non-superuser role — the only
-- way RLS policies actually get exercised instead of silently bypassed.
-- Tables don't exist yet when this script runs (it's an initdb hook, before
-- any migration), so grant on future objects cios_user creates rather than
-- current ones.
CREATE ROLE cios_app LOGIN PASSWORD 'cios_app_pass';
ALTER DEFAULT PRIVILEGES FOR ROLE cios_user IN SCHEMA public
    GRANT ALL PRIVILEGES ON TABLES TO cios_app;
ALTER DEFAULT PRIVILEGES FOR ROLE cios_user IN SCHEMA public
    GRANT ALL PRIVILEGES ON SEQUENCES TO cios_app;
