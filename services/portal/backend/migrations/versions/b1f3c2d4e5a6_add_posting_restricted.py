"""add_posting_restricted (H1 민원 도배: 계정별 민원 작성 제한)

Revision ID: b1f3c2d4e5a6
Revises: 7c2e9a41d5b3
Create Date: 2026-11-09 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b1f3c2d4e5a6'
down_revision = '7c2e9a41d5b3'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('users') as batch_op:
        batch_op.add_column(sa.Column('posting_restricted', sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade():
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_column('posting_restricted')
