"""validate certain documents boolean

Revision ID: 5ae64b3fd058
Revises: 8634863f8e1
Create Date: 2013-10-08 16:00:28.392843

"""

# revision identifiers, used by Alembic.
revision = '5ae64b3fd058'
down_revision = '8634863f8e1'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('document', sa.Column('validate', sa.Boolean(), nullable=True))
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('document', 'validate')
    ### end Alembic commands ###
