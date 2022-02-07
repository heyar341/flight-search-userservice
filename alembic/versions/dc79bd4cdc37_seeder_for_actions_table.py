"""seeder for actions table

Revision ID: dc79bd4cdc37
Revises: 02c8ff673d0d
Create Date: 2022-02-07 08:41:49.279322

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column
from sqlalchemy import String, Integer, Date

# revision identifiers, used by Alembic.
revision = 'dc79bd4cdc37'
down_revision = '02c8ff673d0d'
branch_labels = None
depends_on = None

actions_table = table('actions',
                      column('id', Integer),
                      column('action', String),
                      )

op.bulk_insert(actions_table, [{'id': 1, 'action': 'register'},
                               {'id': 2, 'action': 'update_email'},
                               ]
               )


def upgrade():
    pass


def downgrade():
    pass
