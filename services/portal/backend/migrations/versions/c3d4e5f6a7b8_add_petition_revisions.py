"""add immutable petition revisions for H3 restoration

Revision ID: c3d4e5f6a7b8
Revises: b1f3c2d4e5a6
Create Date: 2026-11-11 11:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "c3d4e5f6a7b8"
down_revision = "b1f3c2d4e5a6"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "petition_revisions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("petition_id", sa.Integer(), sa.ForeignKey("petitions.id"), nullable=False),
        sa.Column("actor_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("reply", sa.Text(), nullable=False),
        sa.Column("assignee_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_petition_revisions_petition_id", "petition_revisions", ["petition_id"])


def downgrade():
    op.drop_index("ix_petition_revisions_petition_id", table_name="petition_revisions")
    op.drop_table("petition_revisions")
