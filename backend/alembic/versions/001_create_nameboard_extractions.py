"""create nameboard_extractions table

Revision ID: 001
Revises:
Create Date: 2026-03-20
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "nameboard_extractions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column("uploaded_by_customer_id", UUID(as_uuid=True), nullable=True),
        sa.Column("uploaded_by_posp_id", UUID(as_uuid=True), nullable=True),
        sa.Column("imagekit_file_ids", JSONB(), nullable=True),
        sa.Column("images_processed", sa.Integer(), nullable=True),
        sa.Column("overall_confidence", sa.Numeric(4, 3), nullable=True),
        sa.Column("extracted_data", JSONB(), nullable=True),
        sa.Column("pii_data", JSONB(), nullable=True),
        sa.Column("image_quality", JSONB(), nullable=True),
        sa.Column("extraction_warnings", JSONB(), nullable=True),
        sa.Column("geocoding_status", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=True, server_default="PENDING_REVIEW"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()")),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_nameboard_extractions_session_id", "nameboard_extractions", ["session_id"])
    op.create_index("ix_nameboard_extractions_customer_id", "nameboard_extractions", ["uploaded_by_customer_id"])


def downgrade() -> None:
    op.drop_index("ix_nameboard_extractions_customer_id")
    op.drop_index("ix_nameboard_extractions_session_id")
    op.drop_table("nameboard_extractions")
