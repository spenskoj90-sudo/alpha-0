-- P1 RLS hardening: preserve migration 002 checksum and force policies
-- even for table-owner application roles. The application connection must
-- still set app.service_role=true to obtain access.

ALTER TABLE identities FORCE ROW LEVEL SECURITY;
ALTER TABLE device_bindings FORCE ROW LEVEL SECURITY;
ALTER TABLE sessions FORCE ROW LEVEL SECURITY;
ALTER TABLE entitlements FORCE ROW LEVEL SECURITY;
ALTER TABLE characters FORCE ROW LEVEL SECURITY;
ALTER TABLE game_events FORCE ROW LEVEL SECURITY;
ALTER TABLE audit_events FORCE ROW LEVEL SECURITY;
