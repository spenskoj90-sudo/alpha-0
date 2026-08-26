-- P1: explicit RLS policies. The API persistence role must opt into the
-- service policy with PGOPTIONS=-c app.service_role=true. Without that
-- setting PostgreSQL fails closed at the row-policy layer.

ALTER TABLE identities ENABLE ROW LEVEL SECURITY;
ALTER TABLE device_bindings ENABLE ROW LEVEL SECURITY;
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE entitlements ENABLE ROW LEVEL SECURITY;
ALTER TABLE characters ENABLE ROW LEVEL SECURITY;
ALTER TABLE game_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_events ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS identities_service_policy ON identities;
CREATE POLICY identities_service_policy ON identities
  USING (current_setting('app.service_role', true) = 'true')
  WITH CHECK (current_setting('app.service_role', true) = 'true');

DROP POLICY IF EXISTS device_bindings_service_policy ON device_bindings;
CREATE POLICY device_bindings_service_policy ON device_bindings
  USING (current_setting('app.service_role', true) = 'true')
  WITH CHECK (current_setting('app.service_role', true) = 'true');

DROP POLICY IF EXISTS sessions_service_policy ON sessions;
CREATE POLICY sessions_service_policy ON sessions
  USING (current_setting('app.service_role', true) = 'true')
  WITH CHECK (current_setting('app.service_role', true) = 'true');

DROP POLICY IF EXISTS entitlements_service_policy ON entitlements;
CREATE POLICY entitlements_service_policy ON entitlements
  USING (current_setting('app.service_role', true) = 'true')
  WITH CHECK (current_setting('app.service_role', true) = 'true');

DROP POLICY IF EXISTS characters_service_policy ON characters;
CREATE POLICY characters_service_policy ON characters
  USING (current_setting('app.service_role', true) = 'true')
  WITH CHECK (current_setting('app.service_role', true) = 'true');

DROP POLICY IF EXISTS game_events_service_policy ON game_events;
CREATE POLICY game_events_service_policy ON game_events
  USING (current_setting('app.service_role', true) = 'true')
  WITH CHECK (current_setting('app.service_role', true) = 'true');

DROP POLICY IF EXISTS audit_events_service_policy ON audit_events;
CREATE POLICY audit_events_service_policy ON audit_events
  USING (current_setting('app.service_role', true) = 'true')
  WITH CHECK (current_setting('app.service_role', true) = 'true');

COMMENT ON POLICY identities_service_policy ON identities IS 'P1 explicit fail-closed service policy; application must opt in via app.service_role';
COMMENT ON POLICY device_bindings_service_policy ON device_bindings IS 'P1 explicit fail-closed service policy';
COMMENT ON POLICY sessions_service_policy ON sessions IS 'P1 explicit fail-closed service policy';
COMMENT ON POLICY entitlements_service_policy ON entitlements IS 'P1 explicit fail-closed service policy';
COMMENT ON POLICY characters_service_policy ON characters IS 'P1 explicit fail-closed service policy';
COMMENT ON POLICY game_events_service_policy ON game_events IS 'P1 explicit fail-closed service policy';
COMMENT ON POLICY audit_events_service_policy ON audit_events IS 'P1 explicit fail-closed service policy';
