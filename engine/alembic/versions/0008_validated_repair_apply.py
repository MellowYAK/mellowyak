"""Add validated repair, transactional apply, rollback, recovery and demo records.

Revision ID: 0008_validated_repair_apply
Revises: 0007_runtime_snapshot_probe_foundation
Create Date: 2026-08-25
"""

import sqlalchemy as sa

from alembic import op

revision = "0008_validated_repair_apply"
down_revision = "0007_runtime_snapshot_probe_foundation"
branch_labels = None
depends_on = None


def _project_fk() -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(["project_id"], ["projects.id"])


def upgrade() -> None:
    with op.batch_alter_table("repair_workspaces") as batch:
        batch.add_column(sa.Column("base_manifest_digest", sa.String(64), nullable=True))
        batch.add_column(sa.Column("workspace_manifest_digest", sa.String(64), nullable=True))
        batch.add_column(
            sa.Column(
                "runtime_profile_versions_json", sa.Text(), nullable=False, server_default="[]"
            )
        )
        batch.add_column(
            sa.Column("validation_policy_json", sa.Text(), nullable=False, server_default="{}")
        )
        batch.add_column(sa.Column("last_change_at", sa.DateTime(timezone=True), nullable=True))

    op.execute(
        "UPDATE repair_workspaces SET base_manifest_digest = manifest_digest "
        "WHERE base_manifest_digest IS NULL"
    )

    op.create_table(
        "repair_candidates",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("workspace_id", sa.String(36), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(40), nullable=False),
        sa.Column("base_manifest_digest", sa.String(64), nullable=False),
        sa.Column("workspace_manifest_digest", sa.String(64), nullable=False),
        sa.Column("candidate_digest", sa.String(64), nullable=False),
        sa.Column("source_snapshot_id", sa.String(64), nullable=False),
        sa.Column("file_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("logical_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("binary_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("warnings_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("limitations_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        _project_fk(),
        sa.ForeignKeyConstraint(["workspace_id"], ["repair_workspaces.id"]),
        sa.UniqueConstraint("workspace_id", "revision"),
    )
    op.create_table(
        "repair_candidate_files",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("candidate_id", sa.String(36), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("relative_path", sa.Text(), nullable=False),
        sa.Column("operation", sa.String(24), nullable=False),
        sa.Column("base_digest", sa.String(64), nullable=True),
        sa.Column("candidate_digest", sa.String(64), nullable=True),
        sa.Column("expected_live_digest", sa.String(64), nullable=True),
        sa.Column("byte_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("classification", sa.String(20), nullable=False),
        sa.Column("file_mode", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("executable", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("rename_source", sa.Text(), nullable=True),
        sa.Column("rename_destination", sa.Text(), nullable=True),
        sa.Column("validation_eligible", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("apply_eligible", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("exclusion_reason", sa.String(120), nullable=True),
        sa.Column("warning_state", sa.String(120), nullable=True),
        sa.Column("excluded", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.ForeignKeyConstraint(["candidate_id"], ["repair_candidates.id"]),
        sa.UniqueConstraint("candidate_id", "ordinal"),
        sa.UniqueConstraint("candidate_id", "relative_path"),
    )
    op.create_table(
        "repair_candidate_validations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("candidate_id", sa.String(36), nullable=False),
        sa.Column("candidate_digest", sa.String(64), nullable=False),
        sa.Column("workspace_manifest_digest", sa.String(64), nullable=False),
        sa.Column("runtime_profile_versions_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("evidence_digest", sa.String(64), nullable=True),
        sa.Column("limitations_json", sa.Text(), nullable=False, server_default="[]"),
        _project_fk(),
        sa.ForeignKeyConstraint(["candidate_id"], ["repair_candidates.id"]),
    )
    op.create_table(
        "repair_candidate_validation_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("validation_id", sa.String(36), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("check_type", sa.String(40), nullable=False),
        sa.Column("requirement", sa.String(20), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("result", sa.String(40), nullable=False),
        sa.Column("duration_ms", sa.Float(), nullable=False, server_default="0"),
        sa.Column("evidence_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("error_code", sa.String(120), nullable=True),
        sa.ForeignKeyConstraint(["validation_id"], ["repair_candidate_validations.id"]),
        sa.UniqueConstraint("validation_id", "ordinal"),
    )
    op.create_table(
        "apply_transactions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("candidate_id", sa.String(36), nullable=False),
        sa.Column("validation_id", sa.String(36), nullable=False),
        sa.Column("state", sa.String(40), nullable=False),
        sa.Column("expected_source_snapshot_id", sa.String(64), nullable=False),
        sa.Column("expected_source_manifest_digest", sa.String(64), nullable=False),
        sa.Column("safety_snapshot_id", sa.String(64), nullable=True),
        sa.Column("post_apply_snapshot_id", sa.String(64), nullable=True),
        sa.Column("confirmation_digest", sa.String(64), nullable=False),
        sa.Column("confirmation_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confirmation_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("journal_relative_path", sa.Text(), nullable=False),
        sa.Column("error_code", sa.String(120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        _project_fk(),
        sa.ForeignKeyConstraint(["candidate_id"], ["repair_candidates.id"]),
        sa.ForeignKeyConstraint(["validation_id"], ["repair_candidate_validations.id"]),
    )
    op.create_index(
        "ix_apply_transactions_project_state", "apply_transactions", ["project_id", "state"]
    )
    op.create_table(
        "apply_transaction_files",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("transaction_id", sa.String(36), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("relative_path", sa.Text(), nullable=False),
        sa.Column("operation", sa.String(24), nullable=False),
        sa.Column("operation_state", sa.String(40), nullable=False),
        sa.Column("original_digest", sa.String(64), nullable=True),
        sa.Column("candidate_digest", sa.String(64), nullable=True),
        sa.Column("temporary_relative_path", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["transaction_id"], ["apply_transactions.id"]),
        sa.UniqueConstraint("transaction_id", "ordinal"),
    )
    op.create_table(
        "apply_journal_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("transaction_id", sa.String(36), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column("details_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["transaction_id"], ["apply_transactions.id"]),
        sa.UniqueConstraint("transaction_id", "sequence"),
    )
    op.create_table(
        "rollback_records",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("transaction_id", sa.String(36), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("restored_paths_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("unresolved_paths_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("verification_digest", sa.String(64), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["transaction_id"], ["apply_transactions.id"]),
    )
    op.create_table(
        "recovery_bundles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("transaction_id", sa.String(36), nullable=False),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("relative_path", sa.Text(), nullable=False),
        sa.Column("manifest_digest", sa.String(64), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["transaction_id"], ["apply_transactions.id"]),
        _project_fk(),
    )
    op.create_table(
        "demo_lab_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), nullable=True),
        sa.Column("root_relative_path", sa.Text(), nullable=False),
        sa.Column("scenario", sa.String(80), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("state_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "product_self_test_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("steps_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("duration_ms", sa.Float(), nullable=False, server_default="0"),
        sa.Column("report_relative_path", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("product_self_test_runs")
    op.drop_table("demo_lab_runs")
    op.drop_table("recovery_bundles")
    op.drop_table("rollback_records")
    op.drop_table("apply_journal_events")
    op.drop_table("apply_transaction_files")
    op.drop_index("ix_apply_transactions_project_state", table_name="apply_transactions")
    op.drop_table("apply_transactions")
    op.drop_table("repair_candidate_validation_items")
    op.drop_table("repair_candidate_validations")
    op.drop_table("repair_candidate_files")
    op.drop_table("repair_candidates")
    with op.batch_alter_table("repair_workspaces") as batch:
        batch.drop_column("last_change_at")
        batch.drop_column("validation_policy_json")
        batch.drop_column("runtime_profile_versions_json")
        batch.drop_column("workspace_manifest_digest")
        batch.drop_column("base_manifest_digest")
