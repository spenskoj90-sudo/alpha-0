-- P1 RLS runtime activation: make the persistence role's service-policy
-- opt-in deterministic for every new PostgreSQL session.
--
-- Migration 002 deliberately fails closed when app.service_role is unset.
-- PostgresStore also supplies the setting at connection time, but a role-level
-- default protects pooled/CI connections from environment-specific startup
-- option loss. CURRENT_USER scopes this change to the role executing the
-- migration; it does not grant BYPASSRLS or change table policies.
ALTER ROLE CURRENT_USER SET app.service_role = 'true';
