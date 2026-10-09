from alembic import op
revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None

def upgrade():
    op.create_index("ix_assets_created", "assets", ["created"])
    op.create_index("ix_tasks_created", "tasks", ["created"])
    op.create_index("ix_tasks_status", "tasks", ["status"])

def downgrade():
    op.drop_index("ix_tasks_status", table_name="tasks")
    op.drop_index("ix_tasks_created", table_name="tasks")
    op.drop_index("ix_assets_created", table_name="assets")
