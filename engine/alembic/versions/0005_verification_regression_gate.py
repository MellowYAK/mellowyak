"""Add selective verification, regression, gate, and repair context.

Revision ID: 0005_verification_regression_gate
Revises: 0004_behavior_evidence_browser
Create Date: 2026-08-24
"""

import sqlalchemy as sa

from alembic import op

revision = "0005_verification_regression_gate"
down_revision = "0004_behavior_evidence_browser"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "protected_behaviors",
        sa.Column("always_recheck", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "evidence_bundles",
        sa.Column("bundle_type", sa.String(40), nullable=False, server_default="BASELINE_CAPTURE"),
    )
    op.add_column(
        "evidence_bundles", sa.Column("verification_run_id", sa.String(36), nullable=True)
    )
    op.create_table(
        "protection_plans",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("change_id", sa.String(64), nullable=False),
        sa.Column("impact_analysis_id", sa.String(36), nullable=False),
        sa.Column("source_identity_json", sa.Text(), nullable=False),
        sa.Column("binding_digest", sa.String(64), nullable=False),
        sa.Column("algorithm_version", sa.String(40), nullable=False),
        sa.Column("policy_version", sa.String(40), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("stale_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("required_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("suggested_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("skipped_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("needs_review_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unknown_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("truncated", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["change_id"], ["project_changes.id"]),
        sa.ForeignKeyConstraint(["impact_analysis_id"], ["impact_analyses.id"]),
    )
    op.create_index(
        "ix_protection_plans_change", "protection_plans", ["project_id", "change_id", "created_at"]
    )
    op.create_table(
        "protection_plan_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("plan_id", sa.String(36), nullable=False),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("behavior_id", sa.String(36), nullable=False),
        sa.Column("behavior_version_id", sa.String(36), nullable=False),
        sa.Column("baseline_id", sa.String(36), nullable=True),
        sa.Column("selection_class", sa.String(40), nullable=False),
        sa.Column("selection_reason", sa.Text(), nullable=False),
        sa.Column("impact_path_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("strongest_provenance", sa.String(40), nullable=False),
        sa.Column("relation_depth", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("stale_relation", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("unknown_boundary", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("criticality", sa.String(20), nullable=False),
        sa.Column("verification_method", sa.String(40), nullable=False),
        sa.Column("current_result_id", sa.String(36), nullable=True),
        sa.ForeignKeyConstraint(["plan_id"], ["protection_plans.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["behavior_id"], ["protected_behaviors.id"]),
        sa.ForeignKeyConstraint(["behavior_version_id"], ["behavior_versions.id"]),
        sa.UniqueConstraint("plan_id", "behavior_id"),
    )
    op.create_table(
        "verification_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("change_id", sa.String(64), nullable=False),
        sa.Column("plan_id", sa.String(36), nullable=False),
        sa.Column("source_identity_json", sa.Text(), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_code", sa.String(120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["change_id"], ["project_changes.id"]),
        sa.ForeignKeyConstraint(["plan_id"], ["protection_plans.id"]),
    )
    op.create_table(
        "verification_run_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("run_id", sa.String(36), nullable=False),
        sa.Column("plan_item_id", sa.String(36), nullable=False),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("behavior_id", sa.String(36), nullable=False),
        sa.Column("behavior_version_id", sa.String(36), nullable=False),
        sa.Column("result", sa.String(40), nullable=False, server_default="NOT_RUN"),
        sa.Column("adapter", sa.String(80), nullable=False),
        sa.Column("adapter_version", sa.String(40), nullable=False),
        sa.Column("evidence_bundle_id", sa.String(36), nullable=True),
        sa.Column("duration_ms", sa.Float(), nullable=False, server_default="0"),
        sa.Column("limitations_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["run_id"], ["verification_runs.id"]),
        sa.ForeignKeyConstraint(["plan_item_id"], ["protection_plan_items.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["behavior_id"], ["protected_behaviors.id"]),
        sa.ForeignKeyConstraint(["behavior_version_id"], ["behavior_versions.id"]),
        sa.UniqueConstraint("run_id", "plan_item_id"),
    )
    op.create_table(
        "assertion_results",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("verification_run_item_id", sa.String(36), nullable=False),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("assertion_type", sa.String(40), nullable=False),
        sa.Column("expected_json", sa.Text(), nullable=False),
        sa.Column("observed_json", sa.Text(), nullable=False),
        sa.Column("result", sa.String(40), nullable=False),
        sa.Column("evidence_references_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("adapter_version", sa.String(40), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["verification_run_item_id"], ["verification_run_items.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.UniqueConstraint("verification_run_item_id", "ordinal"),
    )
    op.create_table(
        "human_verification_attestations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("verification_run_item_id", sa.String(36), nullable=False, unique=True),
        sa.Column("installation_id", sa.String(36), nullable=False),
        sa.Column("result", sa.String(40), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("evidence_reference", sa.Text(), nullable=True),
        sa.Column("confirmed", sa.Boolean(), nullable=False),
        sa.Column("source_identity_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["verification_run_item_id"], ["verification_run_items.id"]),
        sa.ForeignKeyConstraint(["installation_id"], ["installations.id"]),
    )
    op.create_table(
        "regression_findings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("change_id", sa.String(64), nullable=False),
        sa.Column("behavior_id", sa.String(36), nullable=False),
        sa.Column("behavior_version_id", sa.String(36), nullable=False),
        sa.Column("baseline_id", sa.String(36), nullable=True),
        sa.Column("verification_run_item_id", sa.String(36), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("decision_reason", sa.Text(), nullable=False),
        sa.Column("source_identity_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolving_run_item_id", sa.String(36), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["change_id"], ["project_changes.id"]),
        sa.ForeignKeyConstraint(["behavior_id"], ["protected_behaviors.id"]),
        sa.ForeignKeyConstraint(["behavior_version_id"], ["behavior_versions.id"]),
        sa.ForeignKeyConstraint(["verification_run_item_id"], ["verification_run_items.id"]),
    )
    op.create_table(
        "completion_gate_decisions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("change_id", sa.String(64), nullable=False),
        sa.Column("plan_id", sa.String(36), nullable=False),
        sa.Column("verification_run_id", sa.String(36), nullable=True),
        sa.Column("state", sa.String(40), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("source_identity_json", sa.Text(), nullable=False),
        sa.Column("limitations_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("decision_digest", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["change_id"], ["project_changes.id"]),
        sa.ForeignKeyConstraint(["plan_id"], ["protection_plans.id"]),
    )
    op.create_table(
        "repair_contexts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("change_id", sa.String(64), nullable=False),
        sa.Column("regression_id", sa.String(36), nullable=False),
        sa.Column("schema_version", sa.String(80), nullable=False),
        sa.Column("source_identity_json", sa.Text(), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("digest", sa.String(64), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("saved_relative_path", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["change_id"], ["project_changes.id"]),
        sa.ForeignKeyConstraint(["regression_id"], ["regression_findings.id"]),
    )
    op.create_table(
        "repair_context_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("repair_context_id", sa.String(36), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("item_type", sa.String(40), nullable=False),
        sa.Column("relative_reference", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["repair_context_id"], ["repair_contexts.id"]),
    )
    op.create_table(
        "reverification_links",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("regression_id", sa.String(36), nullable=False),
        sa.Column("previous_run_id", sa.String(36), nullable=False),
        sa.Column("current_run_id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["regression_id"], ["regression_findings.id"]),
        sa.ForeignKeyConstraint(["previous_run_id"], ["verification_runs.id"]),
        sa.ForeignKeyConstraint(["current_run_id"], ["verification_runs.id"]),
    )
    op.create_table(
        "verification_audit_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("event_type", sa.String(120), nullable=False),
        sa.Column("subject_type", sa.String(40), nullable=False),
        sa.Column("subject_id", sa.String(36), nullable=False),
        sa.Column("details_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
    )


def downgrade() -> None:
    for table in (
        "verification_audit_events",
        "reverification_links",
        "repair_context_items",
        "repair_contexts",
        "completion_gate_decisions",
        "regression_findings",
        "human_verification_attestations",
        "assertion_results",
        "verification_run_items",
        "verification_runs",
        "protection_plan_items",
        "protection_plans",
    ):
        op.drop_table(table)
    op.drop_column("evidence_bundles", "verification_run_id")
    op.drop_column("evidence_bundles", "bundle_type")
    op.drop_column("protected_behaviors", "always_recheck")
