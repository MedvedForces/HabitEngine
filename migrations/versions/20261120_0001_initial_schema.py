"""Create initial habit tracker schema

Revision ID: 20261120_0001
Revises:
Create Date: 2026-11-20

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261120_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.create_table(
        "users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("hashed_password", sa.Text(), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("length(trim(email)) > 0", name="ck_users_email_not_empty"),
        sa.CheckConstraint("length(trim(timezone)) > 0", name="ck_users_timezone_not_empty"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )

    op.create_table(
        "habits",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("habit_type", sa.String(length=20), nullable=False),
        sa.Column("schedule_type", sa.String(length=20), nullable=False),
        sa.Column("target_value", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("unit", sa.String(length=50), nullable=True),
        sa.Column("weekly_target", sa.SmallInteger(), nullable=True),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("length(trim(name)) > 0", name="ck_habits_name_not_empty"),
        sa.CheckConstraint(
            "habit_type IN ('boolean', 'quantitative')",
            name="ck_habits_habit_type",
        ),
        sa.CheckConstraint(
            "schedule_type IN ('daily', 'weekdays', 'weekly_quota')",
            name="ck_habits_schedule_type",
        ),
        sa.CheckConstraint(
            "(is_archived = false AND archived_at IS NULL)"
            " OR (is_archived = true AND archived_at IS NOT NULL)",
            name="ck_habits_archive_state",
        ),
        sa.CheckConstraint(
            "weekly_target IS NULL OR weekly_target BETWEEN 1 AND 7",
            name="ck_habits_weekly_target",
        ),
        sa.CheckConstraint(
            "(habit_type = 'boolean' AND target_value IS NULL AND unit IS NULL)"
            " OR (habit_type = 'quantitative'"
            " AND target_value > 0 AND unit IS NOT NULL)",
            name="ck_habits_type_fields",
        ),
        sa.CheckConstraint(
            "(schedule_type = 'weekly_quota'"
            " AND weekly_target BETWEEN 1 AND 7)"
            " OR (schedule_type != 'weekly_quota' AND weekly_target IS NULL)",
            name="ck_habits_schedule_fields",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_habits_user_archived_created",
        "habits",
        ["user_id", "is_archived", "created_at"],
    )

    op.create_table(
        "habit_weekdays",
        sa.Column("habit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("weekday", sa.SmallInteger(), nullable=False),
        sa.CheckConstraint("weekday BETWEEN 1 AND 7", name="ck_habit_weekdays_weekday"),
        sa.ForeignKeyConstraint(["habit_id"], ["habits.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("habit_id", "weekday"),
    )

    op.create_table(
        "check_ins",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("habit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("logged_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("local_date", sa.Date(), nullable=False),
        sa.Column("value", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("value > 0", name="ck_check_ins_value_positive"),
        sa.ForeignKeyConstraint(["habit_id"], ["habits.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_check_ins_habit_date_id",
        "check_ins",
        ["habit_id", "local_date", "id"],
        postgresql_ops={
            "local_date": "DESC",
            "id": "DESC",
        },
    )

    op.create_table(
        "habit_freezes",
        sa.Column("habit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("local_date", sa.Date(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["habit_id"], ["habits.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("habit_id", "local_date"),
    )


def downgrade() -> None:
    op.drop_table("habit_freezes")
    op.drop_index("ix_check_ins_habit_date_id", table_name="check_ins")
    op.drop_table("check_ins")
    op.drop_table("habit_weekdays")
    op.drop_index("ix_habits_user_archived_created", table_name="habits")
    op.drop_table("habits")
    op.drop_table("users")
    op.execute("DROP EXTENSION IF EXISTS pgcrypto")
