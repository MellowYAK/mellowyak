"""Add project, Git, scan, impact, and monitoring foundations.

Revision ID: 0002_project_git_impact
Revises: 0001_local_core
Create Date: 2026-08-23
"""

import sqlalchemy as sa

from alembic import op

revision = "0002_project_git_impact"
down_revision = "0001_local_core"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("projects") as batch:
        batch.add_column(sa.Column("installation_id", sa.String(36), nullable=True))
        batch.add_column(sa.Column("canonical_root_path", sa.Text(), nullable=True))
        batch.add_column(sa.Column("repository_root_path", sa.Text(), nullable=True))
        batch.add_column(sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(
            sa.Column("monitoring_mode", sa.String(40), nullable=False, server_default="passive")
        )
        batch.add_column(
            sa.Column("monitoring_status", sa.String(40), nullable=False, server_default="active")
        )
        batch.add_column(sa.Column("active_scan_id", sa.String(36), nullable=True))
        batch.add_column(sa.Column("last_scan_status", sa.String(40), nullable=True))
        batch.add_column(sa.Column("last_scan_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("current_branch", sa.String(240), nullable=True))
        batch.add_column(sa.Column("current_head_sha", sa.String(64), nullable=True))
        batch.add_column(sa.Column("current_worktree_fingerprint", sa.String(64), nullable=True))
        batch.add_column(
            sa.Column("detection_payload_json", sa.Text(), nullable=False, server_default="{}")
        )
        batch.add_column(sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))
        batch.create_foreign_key(
            "fk_projects_installation_id", "installations", ["installation_id"], ["id"]
        )

    op.execute(
        "UPDATE projects SET canonical_root_path = root_path WHERE canonical_root_path IS NULL"
    )
    op.execute(
        "UPDATE projects SET repository_root_path = root_path WHERE repository_root_path IS NULL"
    )
    op.execute("UPDATE projects SET updated_at = created_at WHERE updated_at IS NULL")
    op.execute(
        "UPDATE projects SET installation_id = (SELECT id FROM installations LIMIT 1) "
        "WHERE installation_id IS NULL"
    )
    op.create_index(
        "uq_projects_canonical_root_path", "projects", ["canonical_root_path"], unique=True
    )

    op.create_table(
        "project_git_snapshots",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("branch", sa.String(240), nullable=True),
        sa.Column("head_sha", sa.String(64), nullable=True),
        sa.Column("is_detached", sa.Boolean(), nullable=False),
        sa.Column("is_dirty", sa.Boolean(), nullable=False),
        sa.Column("staged_count", sa.Integer(), nullable=False),
        sa.Column("unstaged_count", sa.Integer(), nullable=False),
        sa.Column("untracked_count", sa.Integer(), nullable=False),
        sa.Column("ignored_count", sa.Integer(), nullable=False),
        sa.Column("worktree_fingerprint", sa.String(64), nullable=False),
        sa.Column("status_payload", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
    )
    op.create_index(
        "ix_project_git_snapshots_project_observed",
        "project_git_snapshots",
        ["project_id", "observed_at"],
    )

    op.create_table(
        "project_change_observations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("previous_fingerprint", sa.String(64), nullable=True),
        sa.Column("worktree_fingerprint", sa.String(64), nullable=False),
        sa.Column("changed_paths_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("git_snapshot_id", sa.String(36), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["git_snapshot_id"], ["project_git_snapshots.id"]),
        sa.UniqueConstraint("project_id", "worktree_fingerprint"),
    )

    op.create_table(
        "project_scan_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("scan_version", sa.String(40), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_candidates", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("processed_files", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("included_files", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("excluded_files", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("binary_files", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sensitive_files", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_files", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unknown_items", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unsupported_files", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("test_files", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("relationship_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
    )

    op.create_table(
        "project_files",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("relative_path", sa.Text(), nullable=False),
        sa.Column("normalized_path", sa.Text(), nullable=False),
        sa.Column("language", sa.String(80), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("content_sha256", sa.String(64), nullable=True),
        sa.Column("is_test", sa.Boolean(), nullable=False),
        sa.Column("is_generated", sa.Boolean(), nullable=False),
        sa.Column("is_binary", sa.Boolean(), nullable=False),
        sa.Column("is_sensitive", sa.Boolean(), nullable=False),
        sa.Column("indexing_mode", sa.String(40), nullable=False),
        sa.Column("parser_adapter", sa.String(80), nullable=True),
        sa.Column("last_seen_scan_id", sa.String(36), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["last_seen_scan_id"], ["project_scan_runs.id"]),
        sa.UniqueConstraint("project_id", "normalized_path"),
    )

    op.create_table(
        "impact_nodes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("node_type", sa.String(40), nullable=False),
        sa.Column("stable_key", sa.Text(), nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("relative_path", sa.Text(), nullable=True),
        sa.Column("last_seen_scan_id", sa.String(36), nullable=False),
        sa.Column("stale", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["last_seen_scan_id"], ["project_scan_runs.id"]),
        sa.UniqueConstraint("project_id", "node_type", "stable_key"),
    )

    op.create_table(
        "impact_edges",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("source_node_id", sa.String(36), nullable=False),
        sa.Column("target_node_id", sa.String(36), nullable=False),
        sa.Column("edge_type", sa.String(40), nullable=False),
        sa.Column("provenance", sa.String(40), nullable=False),
        sa.Column("confidence_class", sa.String(40), nullable=False),
        sa.Column("parser_adapter", sa.String(80), nullable=False),
        sa.Column("source_scan_revision", sa.String(36), nullable=False),
        sa.Column("first_observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("stale", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["source_node_id"], ["impact_nodes.id"]),
        sa.ForeignKeyConstraint(["target_node_id"], ["impact_nodes.id"]),
        sa.UniqueConstraint("project_id", "source_node_id", "target_node_id", "edge_type"),
    )

    op.create_table(
        "scan_findings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("scan_id", sa.String(36), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("code", sa.String(80), nullable=False),
        sa.Column("relative_path", sa.Text(), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["scan_id"], ["project_scan_runs.id"]),
    )


def downgrade() -> None:
    op.drop_table("scan_findings")
    op.drop_table("impact_edges")
    op.drop_table("impact_nodes")
    op.drop_table("project_files")
    op.drop_table("project_scan_runs")
    op.drop_table("project_change_observations")
    op.drop_table("project_git_snapshots")
    op.drop_index("uq_projects_canonical_root_path", table_name="projects")
    with op.batch_alter_table("projects") as batch:
        batch.drop_constraint("fk_projects_installation_id", type_="foreignkey")
        for column in (
            "archived_at",
            "detection_payload_json",
            "current_worktree_fingerprint",
            "current_head_sha",
            "current_branch",
            "last_scan_at",
            "last_scan_status",
            "active_scan_id",
            "monitoring_status",
            "monitoring_mode",
            "updated_at",
            "repository_root_path",
            "canonical_root_path",
            "installation_id",
        ):
            batch.drop_column(column)
