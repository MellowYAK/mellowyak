"""Add protected behaviors, evidence lineage, and browser capture.

Revision ID: 0004_behavior_evidence_browser
Revises: 0003_reverse_impact_context
Create Date: 2026-08-24
"""

import sqlalchemy as sa

from alembic import op

revision = "0004_behavior_evidence_browser"
down_revision = "0003_reverse_impact_context"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "protected_behaviors",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("stable_key", sa.String(120), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("lifecycle_state", sa.String(40), nullable=False, server_default="DRAFT"),
        sa.Column("current_version_id", sa.String(36), nullable=False),
        sa.Column("last_accepted_baseline_id", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.UniqueConstraint("project_id", "stable_key"),
    )
    op.create_index(
        "ix_protected_behaviors_project_state",
        "protected_behaviors",
        ["project_id", "lifecycle_state"],
    )
    op.create_table(
        "behavior_versions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("behavior_id", sa.String(36), nullable=False),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("expected_outcome", sa.Text(), nullable=False),
        sa.Column("criticality", sa.String(20), nullable=False, server_default="MEDIUM"),
        sa.Column("preconditions", sa.Text(), nullable=False, server_default=""),
        sa.Column("starting_state", sa.Text(), nullable=False, server_default=""),
        sa.Column("environment_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("persona", sa.Text(), nullable=False, server_default=""),
        sa.Column("runtime_configuration_id", sa.String(36), nullable=True),
        sa.Column("expected_assertions_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("limitations_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("verification_not_configured", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by_type", sa.String(40), nullable=False, server_default="HUMAN"),
        sa.Column("source_candidate_id", sa.String(36), nullable=True),
        sa.Column("content_digest", sa.String(64), nullable=False),
        sa.Column("supersedes_version_id", sa.String(36), nullable=True),
        sa.Column("source_revision_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["behavior_id"], ["protected_behaviors.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.UniqueConstraint("behavior_id", "version_number"),
    )
    op.create_table(
        "behavior_links",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("behavior_id", sa.String(36), nullable=False),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("link_type", sa.String(40), nullable=False),
        sa.Column("link_key", sa.Text(), nullable=False),
        sa.Column("provenance", sa.String(40), nullable=False, server_default="HUMAN_CONFIRMED"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["behavior_id"], ["protected_behaviors.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.UniqueConstraint("behavior_id", "link_type", "link_key"),
    )
    op.create_table(
        "runtime_configurations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("base_url", sa.Text(), nullable=False),
        sa.Column("allowed_origin", sa.Text(), nullable=False),
        sa.Column("starting_path", sa.Text(), nullable=False, server_default="/"),
        sa.Column("viewport_width", sa.Integer(), nullable=False, server_default="1280"),
        sa.Column("viewport_height", sa.Integer(), nullable=False, server_default="800"),
        sa.Column("locale", sa.String(40), nullable=False, server_default="en-US"),
        sa.Column("timezone", sa.String(80), nullable=False, server_default="UTC"),
        sa.Column("browser_type", sa.String(40), nullable=False, server_default="chromium"),
        sa.Column("capture_screenshots", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("capture_trace", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("capture_video", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("capture_network", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.UniqueConstraint("project_id", "allowed_origin"),
    )
    op.create_table(
        "browser_capture_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("behavior_id", sa.String(36), nullable=False),
        sa.Column("behavior_version_id", sa.String(36), nullable=False),
        sa.Column("runtime_configuration_id", sa.String(36), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("entry_url", sa.Text(), nullable=False),
        sa.Column("source_revision_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("stopped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("error_code", sa.String(120), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("paused", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("browser_version", sa.String(120), nullable=True),
        sa.Column("runtime_identity_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("expected_assertions_json", sa.Text(), nullable=False, server_default="[]"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["behavior_id"], ["protected_behaviors.id"]),
        sa.ForeignKeyConstraint(["behavior_version_id"], ["behavior_versions.id"]),
        sa.ForeignKeyConstraint(["runtime_configuration_id"], ["runtime_configurations.id"]),
    )
    op.create_index(
        "ix_browser_captures_project_status",
        "browser_capture_sessions",
        ["project_id", "status"],
    )
    op.create_table(
        "browser_capture_steps",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("capture_id", sa.String(36), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(40), nullable=False),
        sa.Column("page_url", sa.Text(), nullable=False),
        sa.Column("selector", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("included", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("label", sa.Text(), nullable=False, server_default=""),
        sa.ForeignKeyConstraint(["capture_id"], ["browser_capture_sessions.id"]),
        sa.UniqueConstraint("capture_id", "ordinal"),
    )
    op.create_table(
        "runtime_observations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("capture_id", sa.String(36), nullable=False),
        sa.Column("observation_type", sa.String(40), nullable=False),
        sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("included", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["capture_id"], ["browser_capture_sessions.id"]),
    )
    op.create_table(
        "evidence_artifacts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("media_type", sa.String(120), nullable=False),
        sa.Column("object_key", sa.Text(), nullable=False),
        sa.Column("redaction_state", sa.String(40), nullable=False),
        sa.Column("capture_id", sa.String(36), nullable=True),
        sa.Column("behavior_id", sa.String(36), nullable=True),
        sa.Column("behavior_version_id", sa.String(36), nullable=True),
        sa.Column("source_identity_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("runtime_identity_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("trust_source", sa.String(40), nullable=False, server_default="LOCAL_CAPTURE"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.UniqueConstraint("project_id", "sha256"),
    )
    op.create_table(
        "evidence_bundles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("capture_id", sa.String(36), nullable=False, unique=True),
        sa.Column("manifest_sha256", sa.String(64), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["capture_id"], ["browser_capture_sessions.id"]),
    )
    op.create_table(
        "evidence_bundle_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("bundle_id", sa.String(36), nullable=False),
        sa.Column("artifact_id", sa.String(36), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("item_type", sa.String(40), nullable=False),
        sa.ForeignKeyConstraint(["bundle_id"], ["evidence_bundles.id"]),
        sa.ForeignKeyConstraint(["artifact_id"], ["evidence_artifacts.id"]),
        sa.UniqueConstraint("bundle_id", "ordinal"),
    )
    op.create_table(
        "baseline_attestations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("capture_id", sa.String(36), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("reviewer", sa.Text(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["capture_id"], ["browser_capture_sessions.id"]),
    )
    op.create_table(
        "behavior_baselines",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("behavior_id", sa.String(36), nullable=False),
        sa.Column("behavior_version_id", sa.String(36), nullable=False),
        sa.Column("evidence_bundle_id", sa.String(36), nullable=False),
        sa.Column("attestation_id", sa.String(36), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("source_revision_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["behavior_id"], ["protected_behaviors.id"]),
        sa.ForeignKeyConstraint(["behavior_version_id"], ["behavior_versions.id"]),
        sa.ForeignKeyConstraint(["evidence_bundle_id"], ["evidence_bundles.id"]),
        sa.ForeignKeyConstraint(["attestation_id"], ["baseline_attestations.id"]),
    )
    op.create_table(
        "evidence_audit_events",
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
        "evidence_audit_events",
        "behavior_baselines",
        "baseline_attestations",
        "evidence_bundle_items",
        "evidence_bundles",
        "evidence_artifacts",
        "runtime_observations",
        "browser_capture_steps",
        "browser_capture_sessions",
        "runtime_configurations",
        "behavior_links",
        "behavior_versions",
        "protected_behaviors",
    ):
        op.drop_table(table)
