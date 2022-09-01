"""Add audit rules table

Revision ID: 06bec90ff92c
Revises: 39da2d3fe35e
Create Date: 2022-09-01 16:03:14.377238+00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '06bec90ff92c'
down_revision = '39da2d3fe35e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('audit_rule',
    sa.Column('id', sa.Integer(), sa.Identity(always=True), nullable=False),
    sa.Column('name', sa.String(), nullable=True),
    sa.Column('description', sa.String(), nullable=True),
    sa.Column('status', sa.String(), nullable=True),
    sa.Column('fired_date', sa.String(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('definition', postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=False),
    sa.Column('rule_id', sa.Integer(), nullable=False),
    sa.Column('ruleset_id', sa.Integer(), nullable=False),
    sa.Column('activation_instance_id', sa.Integer(), nullable=False),
    sa.Column('job_instance_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['activation_instance_id'], ['activation_instance.id'], name=op.f('fk_audit_rule_activation_instance_id')),
    sa.ForeignKeyConstraint(['job_instance_id'], ['job_instance.id'], name=op.f('fk_audit_rule_job_instance_id')),
    sa.ForeignKeyConstraint(['rule_id'], ['rule.id'], name=op.f('fk_audit_rule_rule_id')),
    sa.ForeignKeyConstraint(['ruleset_id'], ['ruleset.id'], name=op.f('fk_audit_rule_ruleset_id')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_audit_rule'))
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('audit_rule')
    # ### end Alembic commands ###
