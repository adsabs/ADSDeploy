"""use only version column

Revision ID: 33d955d7196f
Revises: 189fdcb98442
Create Date: 2016-02-22 12:28:41.141411

"""

# revision identifiers, used by Alembic.
revision = '33d955d7196f'
down_revision = '189fdcb98442'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    with op.batch_alter_table('deployment') as t:
        t.alter_column('commit', new_column_name='version')
        t.drop_column('tag')


def downgrade():
    with op.batch_alter_table('deployment') as t:
        t.alter_column('version', new_column_name='commit')
        t.add_column(sa.Column('tag', sa.String(), nullable=True))
