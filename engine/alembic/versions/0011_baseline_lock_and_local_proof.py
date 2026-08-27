"""Add immutable Known Good lineage, Expected Change decisions, and Yak Receipts.

Revision ID: 0011_baseline_lock_and_local_proof
Revises: 0010_passive_sentinel_orchestration
Create Date: 2026-08-27
"""

import sqlalchemy as sa

from alembic import op

revision = "0011_baseline_lock_and_local_proof"
down_revision = "0010_passive_sentinel_orchestration"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("behavior_baselines") as batch:
        batch.add_column(sa.Column("supersedes_baseline_id", sa.String(36), nullable=True))
        batch.add_column(sa.Column("promotion_reason", sa.Text(), nullable=True))
        batch.add_column(sa.Column("promotion_decision_id", sa.String(36), nullable=True))
        batch.add_column(sa.Column("promotion_verification_run_id", sa.String(36), nullable=True))
        batch.add_column(sa.Column("promotion_runtime_identity_json", sa.Text(), nullable=True))
        batch.add_column(
            sa.Column("promotion_confirmed_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch.add_column(sa.Column("promotion_actor", sa.String(80), nullable=True))

    op.create_table(
        "behavior_change_decisions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("behavior_id", sa.String(36), nullable=False),
        sa.Column("previous_baseline_id", sa.String(36), nullable=False),
        sa.Column("decision", sa.String(40), nullable=False),
        sa.Column("state", sa.String(60), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("source_identity_json", sa.Text(), nullable=False),
        sa.Column("runtime_identity_json", sa.Text(), nullable=False),
        sa.Column("capture_id", sa.String(36), nullable=True),
        sa.Column("verification_run_id", sa.String(36), nullable=True),
        sa.Column("confirmation_digest", sa.String(64), nullable=True),
        sa.Column("confirmation_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirmation_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("promoted_baseline_id", sa.String(36), nullable=True),
        sa.Column("actor", sa.String(80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["behavior_id"], ["protected_behaviors.id"]),
        sa.ForeignKeyConstraint(["previous_baseline_id"], ["behavior_baselines.id"]),
    )
    op.create_index(
        "ix_behavior_change_decisions_active",
        "behavior_change_decisions",
        ["project_id", "behavior_id", "state", "created_at"],
    )
    op.create_table(
        "yak_receipts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("episode_id", sa.String(36), nullable=False, unique=True),
        sa.Column("snapshot_id", sa.String(64), nullable=True),
        sa.Column("source_identity_json", sa.Text(), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("digest", sa.String(64), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["episode_id"], ["source_episodes.id"]),
    )


def downgrade() -> None:
    op.drop_table("yak_receipts")
    op.drop_index("ix_behavior_change_decisions_active", table_name="behavior_change_decisions")
    op.drop_table("behavior_change_decisions")
    with op.batch_alter_table("behavior_baselines") as batch:
        batch.drop_column("promotion_actor")
        batch.drop_column("promotion_confirmed_at")
        batch.drop_column("promotion_runtime_identity_json")
        batch.drop_column("promotion_verification_run_id")
        batch.drop_column("promotion_decision_id")
        batch.drop_column("promotion_reason")
        batch.drop_column("supersedes_baseline_id")
