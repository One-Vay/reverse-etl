"""add destinations, mappings and syncs tables

Revision ID: 7c7c3927e37b
Revises: 15db37e6b047
Create Date: 2026-08-17 13:47:10.440504

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7c7c3927e37b"
down_revision: str | None = "15db37e6b047"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "destinations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("api_url", sa.String(length=255), nullable=False),
        sa.Column("auth_token", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_destinations_id"), "destinations", ["id"], unique=False)
    op.create_index(op.f("ix_destinations_name"), "destinations", ["name"], unique=True)

    op.create_table(
        "mappings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("source_table", sa.String(length=255), nullable=False),
        sa.Column("destination_entity", sa.String(length=255), nullable=False),
        sa.Column("field_mappings", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_mappings_id"), "mappings", ["id"], unique=False)
    op.create_index(
        op.f("ix_mappings_source_id"), "mappings", ["source_id"], unique=False
    )

    op.create_table(
        "syncs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("destination_id", sa.Integer(), nullable=False),
        sa.Column("mapping_id", sa.Integer(), nullable=False),
        sa.Column("schedule", sa.String(length=100), nullable=False),
        sa.Column("incremental_field", sa.String(length=255), nullable=True),
        sa.Column("last_run", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_run", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["destination_id"], ["destinations.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["mapping_id"], ["mappings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_syncs_id"), "syncs", ["id"], unique=False)
    op.create_index(op.f("ix_syncs_source_id"), "syncs", ["source_id"], unique=False)
    op.create_index(
        op.f("ix_syncs_destination_id"), "syncs", ["destination_id"], unique=False
    )
    op.create_index(op.f("ix_syncs_mapping_id"), "syncs", ["mapping_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_syncs_mapping_id"), table_name="syncs")
    op.drop_index(op.f("ix_syncs_destination_id"), table_name="syncs")
    op.drop_index(op.f("ix_syncs_source_id"), table_name="syncs")
    op.drop_index(op.f("ix_syncs_id"), table_name="syncs")
    op.drop_table("syncs")

    op.drop_index(op.f("ix_mappings_source_id"), table_name="mappings")
    op.drop_index(op.f("ix_mappings_id"), table_name="mappings")
    op.drop_table("mappings")

    op.drop_index(op.f("ix_destinations_name"), table_name="destinations")
    op.drop_index(op.f("ix_destinations_id"), table_name="destinations")
    op.drop_table("destinations")
