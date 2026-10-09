from alembic import op
import sqlalchemy as sa
import time
revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("users", sa.Column("id",sa.String(),primary_key=True),sa.Column("nickname",sa.String(),nullable=False),sa.Column("avatar_id",sa.String()),sa.Column("unionid",sa.String(),unique=True),sa.Column("profile",sa.JSON(),nullable=False),sa.Column("consent_version",sa.String(),nullable=False),sa.Column("deleted",sa.Boolean(),nullable=False),sa.Column("created",sa.Float(),nullable=False))
    users=sa.table("users",sa.column("id",sa.String()),sa.column("nickname",sa.String()),sa.column("profile",sa.JSON()),sa.column("consent_version",sa.String()),sa.column("deleted",sa.Boolean()),sa.column("created",sa.Float()))
    op.bulk_insert(users,[{"id":"local-developer","nickname":"本地开发者","profile":{},"consent_version":"","deleted":False,"created":time.time()}])
    op.create_table("identities",sa.Column("id",sa.String(),primary_key=True),sa.Column("user_id",sa.String(),nullable=False),sa.Column("provider_key",sa.String(),nullable=False,unique=True))
    op.create_index("ix_identities_user_id","identities",["user_id"])
    op.create_table("login_sessions",sa.Column("id",sa.String(),primary_key=True),sa.Column("user_id",sa.String(),nullable=False),sa.Column("token_hash",sa.String(),nullable=False,unique=True),sa.Column("refresh_hash",sa.String(),nullable=False,unique=True),sa.Column("expires",sa.Float(),nullable=False),sa.Column("refresh_expires",sa.Float(),nullable=False),sa.Column("created",sa.Float(),nullable=False))
    op.create_index("ix_login_sessions_user_id","login_sessions",["user_id"])
    op.create_table("oauth_states",sa.Column("state_hash",sa.String(),primary_key=True),sa.Column("channel",sa.String(),nullable=False),sa.Column("challenge",sa.String(),nullable=False),sa.Column("expires",sa.Float(),nullable=False))
    op.create_table("feedback",sa.Column("id",sa.String(),primary_key=True),sa.Column("user_id",sa.String(),nullable=False),sa.Column("content",sa.String(),nullable=False),sa.Column("created",sa.Float(),nullable=False))
    op.create_index("ix_feedback_user_id","feedback",["user_id"])
    op.create_table("usage_events",sa.Column("id",sa.String(),primary_key=True),sa.Column("owner_id",sa.String(),nullable=False),sa.Column("kind",sa.String(),nullable=False),sa.Column("created",sa.Float(),nullable=False))
    op.create_index("ix_usage_events_owner_id","usage_events",["owner_id"])
    op.create_index("ix_usage_events_created","usage_events",["created"])
    op.execute("INSERT INTO usage_events (id, owner_id, kind, created) SELECT id, 'local-developer', kind, created FROM tasks")
    op.add_column("assets",sa.Column("favorite",sa.Boolean(),nullable=False,server_default=sa.false()))
    for table in ["assets","tasks"]:
        with op.batch_alter_table(table) as batch:
            batch.add_column(sa.Column("owner_id",sa.String(),nullable=False,server_default="local-developer"))
            batch.create_index("ix_"+table+"_owner_id",["owner_id"])

def downgrade():
    with op.batch_alter_table("assets") as batch:
        batch.drop_column("favorite")
    for table in ["assets","tasks"]:
        with op.batch_alter_table(table) as batch:
            batch.drop_index("ix_"+table+"_owner_id")
            batch.drop_column("owner_id")
    for table in ["usage_events","feedback","oauth_states","login_sessions","identities","users"]:
        op.drop_table(table)
