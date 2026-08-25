"""Add Technical Preview readiness state.

Revision ID: 0009_technical_preview_readiness
Revises: 0008_validated_repair_apply
Create Date: 2026-08-25
"""

import sqlalchemy as sa

from alembic import op

revision = "0009_technical_preview_readiness"
down_revision = "0008_validated_repair_apply"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "onboarding_state",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("completed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("current_step", sa.String(40), nullable=False, server_default="welcome"),
        sa.Column("replay_active", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("selected_path", sa.String(40), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    # Migrations run before a first installation identity is created. Existing data roots already
    # contain an installation row and must not be forced through onboarding after an upgrade.
    op.execute(
        """
        INSERT INTO onboarding_state
          (id, completed, current_step, replay_active, selected_path, completed_at, updated_at)
        SELECT 1, 1, 'complete', 0, 'existing_installation', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
        WHERE EXISTS (SELECT 1 FROM installations)
        """
    )
    op.create_table(
        "technical_preview_preferences",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("activity_mode", sa.String(30), nullable=False, server_default="normal"),
        sa.Column(
            "notification_permission", sa.String(30), nullable=False, server_default="unknown"
        ),
        sa.Column("updater_state", sa.String(40), nullable=False, server_default="not_checked"),
        sa.Column("last_update_check_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "project_location_history",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("action", sa.String(30), nullable=False),
        sa.Column("old_location_alias", sa.String(80), nullable=False),
        sa.Column("new_location_alias", sa.String(80), nullable=True),
        sa.Column("expected_identity_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("observed_identity_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("decision", sa.String(40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
    )
    op.create_index(
        "ix_project_location_history_project",
        "project_location_history",
        ["project_id", "created_at"],
    )
    op.create_table(
        "diagnostic_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("summary_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "support_bundle_records",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("relative_path", sa.Text(), nullable=False),
        sa.Column("manifest_sha256", sa.String(64), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "notification_activation_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), nullable=True),
        sa.Column("route_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("reason", sa.String(80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
    )
    op.create_table(
        "update_validation_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("fixture", sa.String(40), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("details_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "package_acceptance_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("summary_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    for table in [
        "package_acceptance_runs",
        "update_validation_runs",
        "notification_activation_events",
        "support_bundle_records",
        "diagnostic_runs",
        "project_location_history",
        "technical_preview_preferences",
        "onboarding_state",
    ]:
        op.drop_table(table)
