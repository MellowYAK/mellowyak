"""Add runtime profiles, snapshot memory, Episodes, probes and repair workspaces.

Revision ID: 0007_runtime_snapshot_probe_foundation
Revises: 0006_desktop_productization
Create Date: 2026-08-24
"""

import sqlalchemy as sa

from alembic import op

revision = "0007_runtime_snapshot_probe_foundation"
down_revision = "0006_desktop_productization"
branch_labels = None
depends_on = None


def _project_fk() -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(["project_id"], ["projects.id"])


def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column("project_type", sa.String(40), nullable=False, server_default="OTHER"),
    )
    op.add_column(
        "projects",
        sa.Column(
            "runtime_setup_status", sa.String(40), nullable=False, server_default="INCOMPLETE"
        ),
    )
    op.add_column(
        "projects",
        sa.Column("observation_level", sa.String(40), nullable=False, server_default="LIGHT"),
    )
    op.add_column(
        "projects",
        sa.Column("snapshot_retention_days", sa.Integer(), nullable=False, server_default="30"),
    )
    op.add_column(
        "projects",
        sa.Column(
            "snapshot_soft_cap_bytes",
            sa.Integer(),
            nullable=False,
            server_default=str(5 * 1024 * 1024 * 1024),
        ),
    )

    op.create_table(
        "runtime_profiles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("display_name", sa.String(240), nullable=False),
        sa.Column("current_version_id", sa.String(36), nullable=False),
        sa.Column("primary", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("status", sa.String(40), nullable=False, server_default="CONFIGURED"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        _project_fk(),
        sa.UniqueConstraint("project_id", "display_name"),
    )
    op.create_table(
        "runtime_profile_versions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("profile_id", sa.String(36), nullable=False),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("runtime_type", sa.String(40), nullable=False),
        sa.Column("adapter_version", sa.String(40), nullable=False),
        sa.Column("execution_mode", sa.String(40), nullable=False),
        sa.Column("executable_reference", sa.Text(), nullable=True),
        sa.Column("argv_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("relative_working_directory", sa.Text(), nullable=False, server_default="."),
        sa.Column("runtime_version", sa.String(120), nullable=True),
        sa.Column("dependency_fingerprint", sa.String(64), nullable=True),
        sa.Column("health_definition_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("expected_ports_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("test_definitions_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("environment_schema_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("network_policy", sa.String(40), nullable=False, server_default="LOOPBACK_ONLY"),
        sa.Column("limitations_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["profile_id"], ["runtime_profiles.id"]),
        _project_fk(),
        sa.UniqueConstraint("profile_id", "version_number"),
    )
    op.create_table(
        "runtime_detections",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("candidates_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_code", sa.String(120), nullable=True),
        _project_fk(),
    )
    op.create_table(
        "runtime_instances",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("profile_id", sa.String(36), nullable=False),
        sa.Column("profile_version_id", sa.String(36), nullable=False),
        sa.Column("correlation_id", sa.String(64), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("process_id", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("stopped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("exit_code", sa.Integer(), nullable=True),
        sa.Column("sanitized_observation_json", sa.Text(), nullable=False, server_default="{}"),
        _project_fk(),
        sa.ForeignKeyConstraint(["profile_id"], ["runtime_profiles.id"]),
        sa.ForeignKeyConstraint(["profile_version_id"], ["runtime_profile_versions.id"]),
    )
    op.create_table(
        "source_episodes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("event_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("added_paths_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("modified_paths_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("deleted_paths_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("renamed_paths_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("dependency_changes_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("runtime_events_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("base_snapshot_id", sa.String(64), nullable=True),
        sa.Column("resulting_snapshot_id", sa.String(64), nullable=True),
        sa.Column("git_anchor_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(40), nullable=False, server_default="OPEN"),
        sa.Column("error_code", sa.String(120), nullable=True),
        _project_fk(),
    )
    op.create_index(
        "ix_source_episodes_project_time",
        "source_episodes",
        ["project_id", "started_at"],
    )
    op.create_table(
        "source_snapshots",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("parent_snapshot_id", sa.String(64), nullable=True),
        sa.Column("episode_id", sa.String(36), nullable=True),
        sa.Column("manifest_digest", sa.String(64), nullable=False),
        sa.Column("creation_reason", sa.String(40), nullable=False),
        sa.Column("source_identity_json", sa.Text(), nullable=False),
        sa.Column("git_anchor_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column(
            "runtime_profile_fingerprints_json",
            sa.Text(),
            nullable=False,
            server_default="[]",
        ),
        sa.Column("included_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("excluded_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sensitive_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unsupported_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("logical_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("physical_bytes_added", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reused_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pinned", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("integrity_status", sa.String(40), nullable=False, server_default="VERIFIED"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        _project_fk(),
        sa.UniqueConstraint("project_id", "manifest_digest"),
    )
    op.create_index(
        "ix_source_snapshots_project_time",
        "source_snapshots",
        ["project_id", "created_at"],
    )
    op.create_table(
        "snapshot_entries",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("snapshot_id", sa.String(64), nullable=False),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("relative_path", sa.Text(), nullable=False),
        sa.Column("blob_digest", sa.String(64), nullable=True),
        sa.Column("byte_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("file_mode", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("executable", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("symlink_target", sa.Text(), nullable=True),
        sa.Column("classification", sa.String(40), nullable=False),
        sa.ForeignKeyConstraint(["snapshot_id"], ["source_snapshots.id"]),
        _project_fk(),
        sa.UniqueConstraint("snapshot_id", "relative_path"),
    )
    op.create_table(
        "snapshot_objects",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("digest", sa.String(64), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("object_relative_path", sa.Text(), nullable=False),
        sa.Column("reference_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("integrity_status", sa.String(40), nullable=False, server_default="VERIFIED"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
        _project_fk(),
        sa.UniqueConstraint("project_id", "digest"),
    )
    op.create_table(
        "snapshot_milestones",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("snapshot_id", sa.String(64), nullable=False),
        sa.Column("display_name", sa.String(240), nullable=False),
        sa.Column("behavior_id", sa.String(36), nullable=True),
        sa.Column("behavior_version_id", sa.String(36), nullable=True),
        sa.Column("probe_version_id", sa.String(36), nullable=True),
        sa.Column("runtime_profile_versions_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("evidence_bundle_id", sa.String(36), nullable=True),
        sa.Column("environment_summary_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("limitations_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("human_attested", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("pinned", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        _project_fk(),
        sa.ForeignKeyConstraint(["snapshot_id"], ["source_snapshots.id"]),
    )
    op.create_table(
        "probe_definitions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("behavior_id", sa.String(36), nullable=True),
        sa.Column("display_name", sa.String(240), nullable=False),
        sa.Column("probe_type", sa.String(40), nullable=False),
        sa.Column("current_version_id", sa.String(36), nullable=False),
        sa.Column("status", sa.String(40), nullable=False, server_default="CONFIGURED"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        _project_fk(),
    )
    op.create_table(
        "probe_versions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("probe_id", sa.String(36), nullable=False),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("runtime_profile_version_id", sa.String(36), nullable=True),
        sa.Column("definition_json", sa.Text(), nullable=False),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("retry_policy_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("expected_result_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("evidence_policy_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("source_links_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("runtime_links_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["probe_id"], ["probe_definitions.id"]),
        _project_fk(),
        sa.UniqueConstraint("probe_id", "version_number"),
    )
    op.create_table(
        "probe_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("probe_id", sa.String(36), nullable=False),
        sa.Column("probe_version_id", sa.String(36), nullable=False),
        sa.Column("snapshot_id", sa.String(64), nullable=False),
        sa.Column("episode_id", sa.String(36), nullable=True),
        sa.Column("runtime_profile_version_id", sa.String(36), nullable=True),
        sa.Column("source_identity_json", sa.Text(), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("result", sa.String(40), nullable=False, server_default="NOT_RUN"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("expected_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("observed_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("evidence_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("limitations_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("reproducible", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        _project_fk(),
        sa.ForeignKeyConstraint(["probe_id"], ["probe_definitions.id"]),
        sa.ForeignKeyConstraint(["probe_version_id"], ["probe_versions.id"]),
    )
    op.create_table(
        "runtime_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("profile_id", sa.String(36), nullable=True),
        sa.Column("instance_id", sa.String(36), nullable=True),
        sa.Column("episode_id", sa.String(36), nullable=True),
        sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("sanitized_details_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        _project_fk(),
    )
    op.create_table(
        "signal_classifications",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("episode_id", sa.String(36), nullable=True),
        sa.Column("snapshot_id", sa.String(64), nullable=True),
        sa.Column("probe_run_id", sa.String(36), nullable=True),
        sa.Column("regression_id", sa.String(36), nullable=True),
        sa.Column("state", sa.String(20), nullable=False),
        sa.Column("reason_codes_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("evidence_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("friendly_key", sa.String(160), nullable=False),
        sa.Column("technical_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        _project_fk(),
    )
    op.create_table(
        "repair_workspaces",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("regression_id", sa.String(36), nullable=True),
        sa.Column("signal_id", sa.String(36), nullable=True),
        sa.Column("snapshot_id", sa.String(64), nullable=False),
        sa.Column("workspace_relative_path", sa.Text(), nullable=False),
        sa.Column("manifest_digest", sa.String(64), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        _project_fk(),
    )
    op.create_table(
        "repair_workspace_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("workspace_id", sa.String(36), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("item_type", sa.String(40), nullable=False),
        sa.Column("relative_reference", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["repair_workspaces.id"]),
        sa.UniqueConstraint("workspace_id", "ordinal"),
    )
    with op.batch_alter_table("regression_findings") as batch:
        batch.alter_column(
            "verification_run_item_id",
            existing_type=sa.String(36),
            nullable=True,
        )
        batch.add_column(sa.Column("probe_run_id", sa.String(36), nullable=True))
        batch.add_column(sa.Column("signal_classification_id", sa.String(36), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("regression_findings") as batch:
        batch.drop_column("signal_classification_id")
        batch.drop_column("probe_run_id")
        batch.alter_column(
            "verification_run_item_id",
            existing_type=sa.String(36),
            nullable=False,
        )
    for table in [
        "repair_workspace_items",
        "repair_workspaces",
        "signal_classifications",
        "runtime_events",
        "probe_runs",
        "probe_versions",
        "probe_definitions",
        "snapshot_milestones",
        "snapshot_objects",
        "snapshot_entries",
        "source_snapshots",
        "source_episodes",
        "runtime_instances",
        "runtime_detections",
        "runtime_profile_versions",
        "runtime_profiles",
    ]:
        op.drop_table(table)
    for column in [
        "snapshot_soft_cap_bytes",
        "snapshot_retention_days",
        "observation_level",
        "runtime_setup_status",
        "project_type",
    ]:
        op.drop_column("projects", column)
