from alembic import op
import sqlalchemy as sa
revision = "001"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("assets", sa.Column("id", sa.String(), primary_key=True),
                    sa.Column("kind", sa.String(), nullable=False), sa.Column("source", sa.String(), nullable=False),
                    sa.Column("name", sa.String(), nullable=False), sa.Column("profile", sa.JSON(), nullable=False),
                    sa.Column("created", sa.Float(), nullable=False))
    op.create_table("tasks", sa.Column("id", sa.String(), primary_key=True),
                    sa.Column("kind", sa.String(), nullable=False), sa.Column("status", sa.String(), nullable=False),
                    sa.Column("snapshot", sa.JSON(), nullable=False), sa.Column("provider_id", sa.String()),
                    sa.Column("result_id", sa.String()), sa.Column("error", sa.String()),
                    sa.Column("created", sa.Float(), nullable=False), sa.Column("output_url", sa.String()))

def downgrade():
    op.drop_table("tasks")
    op.drop_table("assets")
