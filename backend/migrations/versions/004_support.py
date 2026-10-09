from alembic import op
import sqlalchemy as sa
revision="004"
down_revision="003"
branch_labels=None
depends_on=None

def upgrade():
    op.add_column("users",sa.Column("disabled",sa.Boolean(),nullable=False,server_default=sa.false()))
    op.add_column("feedback",sa.Column("status",sa.String(),nullable=False,server_default="new"))
    op.add_column("feedback",sa.Column("reply",sa.String(),nullable=False,server_default=""))
    op.add_column("feedback",sa.Column("replied_at",sa.Float(),nullable=True))

def downgrade():
    with op.batch_alter_table("users") as batch:
        batch.drop_column("disabled")
    with op.batch_alter_table("feedback") as batch:
        for name in ["status","reply","replied_at"]:batch.drop_column(name)
