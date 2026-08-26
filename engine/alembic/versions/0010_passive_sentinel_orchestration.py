"""Add persistent Passive Sentinel orchestration and Impact Memory.

Revision ID: 0010_passive_sentinel_orchestration
Revises: 0009_technical_preview_readiness
Create Date: 2026-08-26
"""

import sqlalchemy as sa

from alembic import op

revision = "0010_passive_sentinel_orchestration"
down_revision = "0009_technical_preview_readiness"
branch_labels = None
depends_on = None


def _project_fk() -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(["project_id"], ["projects.id"])


def upgrade() -> None:
    op.create_table(
        "monitoring_policies",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("version", sa.Integer(), nullable=False, unique=True),
        sa.Column("source_observation_enabled", sa.Boolean(), nullable=False),
        sa.Column("automatic_checking_enabled", sa.Boolean(), nullable=False),
        sa.Column("default_project_mode", sa.String(40), nullable=False),
        sa.Column("max_concurrent_projects", sa.Integer(), nullable=False),
        sa.Column("max_concurrent_probes", sa.Integer(), nullable=False),
        sa.Column("max_concurrent_browser_probes", sa.Integer(), nullable=False),
        sa.Column("daily_runtime_budget_seconds", sa.Integer(), nullable=False),
        sa.Column("default_activity_mode", sa.String(30), nullable=False),
        sa.Column("allowed_hours_json", sa.Text(), nullable=False),
        sa.Column("battery_policy_json", sa.Text(), nullable=False),
        sa.Column("quiet_policy_json", sa.Text(), nullable=False),
        sa.Column("runtime_start_default", sa.String(60), nullable=False),
        sa.Column("notification_policy_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "project_monitoring_policies",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("mode", sa.String(40), nullable=False),
        sa.Column("settle_seconds", sa.Float(), nullable=False),
        sa.Column("max_episode_seconds", sa.Integer(), nullable=False),
        sa.Column("max_checks_per_episode", sa.Integer(), nullable=False),
        sa.Column("max_automatic_duration_seconds", sa.Integer(), nullable=False),
        sa.Column("runtime_start_policy", sa.String(60), nullable=False),
        sa.Column("network_policy", sa.String(40), nullable=False),
        sa.Column("resource_budget_json", sa.Text(), nullable=False),
        sa.Column("notification_policy_json", sa.Text(), nullable=False),
        sa.Column("allowed_hours_json", sa.Text(), nullable=False),
        sa.Column("muted", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        _project_fk(),
        sa.UniqueConstraint("project_id", "version"),
    )
    op.create_table(
        "behavior_monitoring_policies",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("behavior_id", sa.String(36), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("mode", sa.String(40), nullable=False),
        sa.Column("retry_policy_json", sa.Text(), nullable=False),
        sa.Column("max_duration_seconds", sa.Integer(), nullable=False),
        sa.Column("automatic_runtime_eligible", sa.Boolean(), nullable=False),
        sa.Column("sentinel", sa.Boolean(), nullable=False),
        sa.Column("notification_escalation", sa.String(40), nullable=False),
        sa.Column("flaky_handling", sa.String(40), nullable=False),
        sa.Column("resolution_policy", sa.String(40), nullable=False),
        sa.Column("muted", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        _project_fk(),
        sa.ForeignKeyConstraint(["behavior_id"], ["protected_behaviors.id"]),
        sa.UniqueConstraint("behavior_id", "version"),
    )
    op.create_table(
        "orchestration_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("episode_id", sa.String(36), nullable=False, unique=True),
        sa.Column("base_snapshot_id", sa.String(64), nullable=True),
        sa.Column("resulting_snapshot_id", sa.String(64), nullable=False),
        sa.Column("source_identity_json", sa.Text(), nullable=False),
        sa.Column("runtime_profile_versions_json", sa.Text(), nullable=False),
        sa.Column("selected_behaviors_json", sa.Text(), nullable=False),
        sa.Column("omitted_behaviors_json", sa.Text(), nullable=False),
        sa.Column("selected_probe_versions_json", sa.Text(), nullable=False),
        sa.Column("policy_versions_json", sa.Text(), nullable=False),
        sa.Column("scheduler_budget_json", sa.Text(), nullable=False),
        sa.Column("eligibility_json", sa.Text(), nullable=False),
        sa.Column("evidence_references_json", sa.Text(), nullable=False),
        sa.Column("state", sa.String(40), nullable=False),
        sa.Column("terminal_status", sa.String(40), nullable=True),
        sa.Column("error_code", sa.String(120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        _project_fk(),
        sa.ForeignKeyConstraint(["episode_id"], ["source_episodes.id"]),
    )
    op.create_table(
        "orchestration_jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("orchestration_run_id", sa.String(36), nullable=False),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("behavior_id", sa.String(36), nullable=True),
        sa.Column("probe_id", sa.String(36), nullable=False),
        sa.Column("probe_version_id", sa.String(36), nullable=False),
        sa.Column("runtime_profile_version_id", sa.String(36), nullable=True),
        sa.Column("snapshot_id", sa.String(64), nullable=False),
        sa.Column("source_identity_digest", sa.String(64), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("job_type", sa.String(40), nullable=False),
        sa.Column("idempotence", sa.String(40), nullable=False),
        sa.Column("state", sa.String(40), nullable=False),
        sa.Column("reason_code", sa.String(120), nullable=False),
        sa.Column("defer_reason", sa.String(120), nullable=True),
        sa.Column("probe_run_id", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        _project_fk(),
        sa.ForeignKeyConstraint(["orchestration_run_id"], ["orchestration_runs.id"]),
        sa.ForeignKeyConstraint(["probe_id"], ["probe_definitions.id"]),
        sa.ForeignKeyConstraint(["probe_version_id"], ["probe_versions.id"]),
        sa.UniqueConstraint("probe_version_id", "source_identity_digest"),
    )
    op.create_index(
        "ix_orchestration_jobs_queue", "orchestration_jobs", ["state", "priority", "created_at"]
    )
    op.create_table(
        "orchestration_job_attempts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("job_id", sa.String(36), nullable=False),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(120), nullable=False),
        sa.Column("result", sa.String(40), nullable=False),
        sa.Column("classification", sa.String(40), nullable=False),
        sa.Column("details_json", sa.Text(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        _project_fk(),
        sa.ForeignKeyConstraint(["job_id"], ["orchestration_jobs.id"]),
        sa.UniqueConstraint("job_id", "attempt_number"),
    )
    op.create_table(
        "scheduler_recovery_records",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("engine_run_id", sa.String(36), nullable=False),
        sa.Column("recovered_count", sa.Integer(), nullable=False),
        sa.Column("stale_count", sa.Integer(), nullable=False),
        sa.Column("interrupted_count", sa.Integer(), nullable=False),
        sa.Column("details_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "impact_memory_relations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("source_key", sa.Text(), nullable=False),
        sa.Column("behavior_id", sa.String(36), nullable=False),
        sa.Column("provenance", sa.String(40), nullable=False),
        sa.Column("source_identity_digest", sa.String(64), nullable=False),
        sa.Column("runtime_version_scope", sa.String(36), nullable=True),
        sa.Column("evidence_reference", sa.Text(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("stale_reason", sa.String(120), nullable=True),
        sa.Column("reason", sa.String(240), nullable=False),
        sa.Column("first_observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_observed_at", sa.DateTime(timezone=True), nullable=False),
        _project_fk(),
        sa.ForeignKeyConstraint(["behavior_id"], ["protected_behaviors.id"]),
        sa.UniqueConstraint(
            "project_id", "source_key", "behavior_id", "provenance", "source_identity_digest"
        ),
    )
    op.create_table(
        "probe_flakiness_records",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("probe_id", sa.String(36), nullable=False),
        sa.Column("source_identity_digest", sa.String(64), nullable=False),
        sa.Column("classification", sa.String(40), nullable=False),
        sa.Column("consecutive_flaky_count", sa.Integer(), nullable=False),
        sa.Column("quarantined", sa.Boolean(), nullable=False),
        sa.Column("last_attempts_json", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        _project_fk(),
        sa.ForeignKeyConstraint(["probe_id"], ["probe_definitions.id"]),
        sa.UniqueConstraint("probe_id", "source_identity_digest"),
    )
    op.create_table(
        "alert_deduplication_records",
        sa.Column("deduplication_key", sa.String(255), primary_key=True),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("behavior_id", sa.String(36), nullable=True),
        sa.Column("baseline_identity", sa.String(64), nullable=True),
        sa.Column("source_identity_digest", sa.String(64), nullable=False),
        sa.Column("signal_category", sa.String(40), nullable=False),
        sa.Column("alert_id", sa.String(36), nullable=True),
        sa.Column("delivery_status", sa.String(40), nullable=False),
        sa.Column("occurrence_count", sa.Integer(), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        _project_fk(),
    )


def downgrade() -> None:
    for table in [
        "alert_deduplication_records",
        "probe_flakiness_records",
        "impact_memory_relations",
        "scheduler_recovery_records",
        "orchestration_job_attempts",
        "orchestration_jobs",
        "orchestration_runs",
        "behavior_monitoring_policies",
        "project_monitoring_policies",
        "monitoring_policies",
    ]:
        op.drop_table(table)
