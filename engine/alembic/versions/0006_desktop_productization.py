"""Add desktop lifecycle, alerts, notifications, and quiet mode.

Revision ID: 0006_desktop_productization
Revises: 0005_verification_regression_gate
Create Date: 2026-08-24
"""

import sqlalchemy as sa

from alembic import op

revision = "0006_desktop_productization"
down_revision = "0005_verification_regression_gate"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "projects", sa.Column("disconnected_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "projects",
        sa.Column("source_available", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "projects",
        sa.Column("notifications_muted", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_table(
        "alerts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), nullable=True),
        sa.Column("change_id", sa.String(64), nullable=True),
        sa.Column("behavior_id", sa.String(36), nullable=True),
        sa.Column("regression_id", sa.String(36), nullable=True),
        sa.Column("gate_id", sa.String(36), nullable=True),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("category", sa.String(30), nullable=False),
        sa.Column("title_key", sa.String(160), nullable=False),
        sa.Column("summary_key", sa.String(160), nullable=False),
        sa.Column("parameters_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("route_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("deduplication_key", sa.String(255), nullable=False, unique=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
    )
    op.create_index("ix_alerts_attention", "alerts", ["resolved_at", "read_at", "updated_at"])
    op.create_table(
        "notification_preferences",
        sa.Column("id", sa.Integer(), primary_key=True),
        *[
            sa.Column(name, sa.Boolean(), nullable=False, server_default=sa.true())
            for name in [
                "native_enabled",
                "regression_enabled",
                "blocked_gate_enabled",
                "needs_review_enabled",
                "project_errors_enabled",
                "show_behavior_name",
                "show_project_name",
            ]
        ],
        *[
            sa.Column(name, sa.Boolean(), nullable=False, server_default=sa.false())
            for name in [
                "verified_complete_enabled",
                "regression_resolved_enabled",
                "hide_details",
                "critical_override",
            ]
        ],
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "project_notification_preferences",
        sa.Column("project_id", sa.String(36), primary_key=True),
        sa.Column("muted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
    )
    op.create_table(
        "quiet_mode_state",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("until_turned_off", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("allow_critical", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "application_preferences",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("keep_running_on_close", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("start_at_login", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "project_lifecycle_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column("details_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "project_disconnection_records",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("display_name", sa.String(240), nullable=False),
        sa.Column("repository_identity_json", sa.Text(), nullable=False),
        sa.Column("disconnected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reconnected_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    for table in [
        "project_disconnection_records",
        "project_lifecycle_events",
        "application_preferences",
        "quiet_mode_state",
        "project_notification_preferences",
        "notification_preferences",
        "alerts",
    ]:
        op.drop_table(table)
    op.drop_column("projects", "notifications_muted")
    op.drop_column("projects", "source_available")
    op.drop_column("projects", "disconnected_at")
