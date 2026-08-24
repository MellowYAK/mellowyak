"""Add reverse impact, Context Receipt, and behavior candidate foundations.

Revision ID: 0003_reverse_impact_context
Revises: 0002_project_git_impact
Create Date: 2026-08-24
"""

import sqlalchemy as sa

from alembic import op

revision = "0003_reverse_impact_context"
down_revision = "0002_project_git_impact"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "project_changes",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("logical_key", sa.String(64), nullable=False),
        sa.Column("change_kind", sa.String(40), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("base_head_sha", sa.String(64), nullable=True),
        sa.Column("head_sha", sa.String(64), nullable=True),
        sa.Column("worktree_fingerprint", sa.String(64), nullable=False),
        sa.Column("changed_paths_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("task_intent", sa.Text(), nullable=True),
        sa.Column("status", sa.String(40), nullable=False, server_default="change_detected"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.UniqueConstraint("project_id", "logical_key"),
    )
    op.create_index(
        "ix_project_changes_project_updated", "project_changes", ["project_id", "updated_at"]
    )

    op.create_table(
        "impact_analyses",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("change_id", sa.String(64), nullable=False),
        sa.Column("analysis_revision", sa.Integer(), nullable=False),
        sa.Column("base_head_sha", sa.String(64), nullable=True),
        sa.Column("head_sha", sa.String(64), nullable=True),
        sa.Column("worktree_fingerprint", sa.String(64), nullable=False),
        sa.Column("scan_revision", sa.String(36), nullable=True),
        sa.Column("algorithm_version", sa.String(40), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("changed_file_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("impacted_node_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unknown_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("stale_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("heuristic_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("truncated", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("truncation_reasons_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("duration_ms", sa.Float(), nullable=False, server_default="0"),
        sa.Column("stale", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("stale_reasons_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["change_id"], ["project_changes.id"]),
        sa.UniqueConstraint("project_id", "change_id", "analysis_revision"),
    )
    op.create_index(
        "ix_impact_analyses_project_created", "impact_analyses", ["project_id", "created_at"]
    )

    op.create_table(
        "impact_analysis_inputs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("analysis_id", sa.String(36), nullable=False),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("changed_files_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("task_intent", sa.Text(), nullable=True),
        sa.Column("traversal_policy_json", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["analysis_id"], ["impact_analyses.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
    )
    op.create_table(
        "impact_analysis_results",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("analysis_id", sa.String(36), nullable=False),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("node_id", sa.String(36), nullable=True),
        sa.Column("node_type", sa.String(40), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("relative_path", sa.Text(), nullable=True),
        sa.Column("impact_class", sa.String(40), nullable=False),
        sa.Column("minimum_depth", sa.Integer(), nullable=False),
        sa.Column("strongest_provenance", sa.String(40), nullable=False),
        sa.Column("stale", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("unknown", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("path_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ranking_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("ranking_reasons_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("unknown_reason", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["analysis_id"], ["impact_analyses.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["node_id"], ["impact_nodes.id"]),
    )
    op.create_index(
        "ix_impact_results_analysis", "impact_analysis_results", ["analysis_id", "minimum_depth"]
    )
    op.create_table(
        "impact_analysis_paths",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("analysis_id", sa.String(36), nullable=False),
        sa.Column("result_id", sa.String(36), nullable=False),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("depth", sa.Integer(), nullable=False),
        sa.Column("path_json", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["analysis_id"], ["impact_analyses.id"]),
        sa.ForeignKeyConstraint(["result_id"], ["impact_analysis_results.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
    )

    op.create_table(
        "context_receipts",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("change_id", sa.String(64), nullable=False),
        sa.Column("analysis_id", sa.String(36), nullable=False),
        sa.Column("receipt_key", sa.String(64), nullable=False),
        sa.Column("request_text", sa.Text(), nullable=True),
        sa.Column("source_revision_json", sa.Text(), nullable=False),
        sa.Column("constraints_json", sa.Text(), nullable=False),
        sa.Column("unknowns_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("excluded_context_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("relationship_paths_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("size_metrics_json", sa.Text(), nullable=False),
        sa.Column("truncated", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("stale", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["change_id"], ["project_changes.id"]),
        sa.ForeignKeyConstraint(["analysis_id"], ["impact_analyses.id"]),
        sa.UniqueConstraint("project_id", "receipt_key"),
    )
    op.create_table(
        "context_receipt_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("receipt_id", sa.String(64), nullable=False),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("relative_path", sa.Text(), nullable=False),
        sa.Column("item_type", sa.String(40), nullable=False),
        sa.Column("reason_selected", sa.Text(), nullable=False),
        sa.Column("relationship_provenance", sa.String(40), nullable=False),
        sa.Column("relevance_class", sa.String(40), nullable=False),
        sa.Column("stale", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("size_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("content_eligible", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("selection_reasons_json", sa.Text(), nullable=False, server_default="[]"),
        sa.ForeignKeyConstraint(["receipt_id"], ["context_receipts.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
    )

    op.create_table(
        "behavior_candidates",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("source_type", sa.String(40), nullable=False),
        sa.Column("source_key", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("status", sa.String(40), nullable=False, server_default="CANDIDATE"),
        sa.Column("evidence_state", sa.String(40), nullable=False, server_default="none"),
        sa.Column(
            "verification_state", sa.String(40), nullable=False, server_default="not_configured"
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("kept_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.UniqueConstraint("project_id", "source_type", "source_key"),
    )
    op.create_table(
        "behavior_candidate_links",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("behavior_candidate_id", sa.String(36), nullable=False),
        sa.Column("change_id", sa.String(64), nullable=True),
        sa.Column("impact_node_id", sa.String(36), nullable=True),
        sa.Column("relation_type", sa.String(40), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["behavior_candidate_id"], ["behavior_candidates.id"]),
        sa.ForeignKeyConstraint(["change_id"], ["project_changes.id"]),
        sa.ForeignKeyConstraint(["impact_node_id"], ["impact_nodes.id"]),
        sa.UniqueConstraint(
            "project_id", "behavior_candidate_id", "change_id", "impact_node_id", "relation_type"
        ),
    )


def downgrade() -> None:
    for table in (
        "behavior_candidate_links",
        "behavior_candidates",
        "context_receipt_items",
        "context_receipts",
        "impact_analysis_paths",
        "impact_analysis_results",
        "impact_analysis_inputs",
        "impact_analyses",
        "project_changes",
    ):
        op.drop_table(table)
