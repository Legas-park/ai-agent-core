"""initial schema — repository_config, llm_provider_config, system_meta

Revision ID: 001_initial
Revises:
Create Date: 2026-06-29

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "repository_config",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("provider_type", sa.String(length=32), nullable=False),
        sa.Column("base_url", sa.String(length=512), nullable=False, server_default=""),
        sa.Column("access_token_encrypted", sa.Text(), nullable=False, server_default=""),
        sa.Column("default_project", sa.String(length=256), nullable=False, server_default=""),
        sa.Column("webhook_secret_encrypted", sa.Text(), nullable=False, server_default=""),
        sa.Column("configured_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "llm_provider_config",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("provider_type", sa.String(length=32), nullable=False),
        sa.Column("display_name", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("model_name", sa.String(length=128), nullable=False),
        sa.Column("api_key_encrypted", sa.Text(), nullable=False, server_default=""),
        sa.Column("api_base_url", sa.String(length=512), nullable=False, server_default=""),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_llm_provider_config_priority", "llm_provider_config", ["priority"])
    op.create_table(
        "system_meta",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("setup_completed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("setup_version", sa.String(length=32), nullable=False, server_default="1"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(
        sa.text("INSERT INTO system_meta (id, setup_completed, setup_version) VALUES (1, false, '1')")
    )


def downgrade() -> None:
    op.drop_table("system_meta")
    op.drop_index("ix_llm_provider_config_priority", table_name="llm_provider_config")
    op.drop_table("llm_provider_config")
    op.drop_table("repository_config")
