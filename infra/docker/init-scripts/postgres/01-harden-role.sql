-- POSTGRES_USER becomes a real Postgres superuser in the official postgres image,
-- which bypasses row-level security unconditionally regardless of
-- FORCE ROW LEVEL SECURITY (see migration 007_force_rls). Production RDS does not
-- have this problem: its master user is rds_superuser, not a true superuser.
-- Strip the attribute here so local dev matches CI and production, and RLS
-- policies are actually exercised rather than silently bypassed.
ALTER ROLE cios_user NOSUPERUSER;
