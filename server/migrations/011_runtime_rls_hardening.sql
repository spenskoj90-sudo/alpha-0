-- Service-only RLS invariant for runtime tables that were added outside the
-- original P1 rollout. Every application database connection must explicitly
-- opt in with app.service_role=true; table owners remain subject to FORCE RLS.

DO $$
DECLARE
    table_name text;
    policy_name text;
    protected_tables text[] := ARRAY[
        'roles',
        'permissions',
        'role_permissions',
        'scopes',
        'games',
        'billing_customers',
        'billing_subscriptions',
        'knowledge_items',
        'outbox_events',
        'worker_jobs',
        'wow_patches',
        'wow_realms',
        'wow_realm_observations',
        'device_challenges',
        'idempotency_keys',
        'proof_request_ids',
        'security_failures',
        'users',
        'companion_telemetry_events',
        'quality_reports',
        'quality_issue_clusters',
        'quality_cluster_users',
        'quality_cluster_devices',
        'quality_cluster_versions'
    ];
BEGIN
    FOREACH table_name IN ARRAY protected_tables LOOP
        policy_name := table_name || '_service_policy';
        EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', table_name);
        EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY', table_name);
        EXECUTE format('DROP POLICY IF EXISTS %I ON %I', policy_name, table_name);
        EXECUTE format(
            'CREATE POLICY %I ON %I USING (current_setting(''app.service_role'', true) = ''true'') WITH CHECK (current_setting(''app.service_role'', true) = ''true'')',
            policy_name,
            table_name
        );
    END LOOP;
END $$;
