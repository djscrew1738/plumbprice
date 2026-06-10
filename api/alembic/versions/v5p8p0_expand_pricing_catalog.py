"""v5_8_0_expand_pricing_catalog

Expands the pricing catalog to support 500+ SKUs and automated price feeds:
 - Adds in_stock, lead_time, manufacturer, msrp, category, sub_category, tags to supplier_products
 - Adds tags, difficulty_rating, required_certifications to labor_templates
 - Creates material_categories taxonomy table

Revision ID: v5p8p0_expand_pricing_catalog
Revises: v4p1p1_blueprint_additions
Create Date: 2026-06-08
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "v5p8p0_expand_pricing_catalog"
down_revision: Union[str, Sequence[str], None] = "v4p1p1_blueprint_additions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # -- supplier_products additions ------------------------------------------
    existing_cols = {c["name"] for c in inspector.get_columns("supplier_products")}

    if "in_stock" not in existing_cols:
        op.add_column("supplier_products", sa.Column("in_stock", sa.Boolean(), server_default="true", nullable=False))
    if "lead_time" not in existing_cols:
        op.add_column("supplier_products", sa.Column("lead_time", sa.String(50), nullable=True))
    if "manufacturer" not in existing_cols:
        op.add_column("supplier_products", sa.Column("manufacturer", sa.String(100), nullable=True))
    if "msrp" not in existing_cols:
        op.add_column("supplier_products", sa.Column("msrp", sa.Float(), nullable=True))
    if "category" not in existing_cols:
        op.add_column("supplier_products", sa.Column("category", sa.String(100), nullable=True))
    if "sub_category" not in existing_cols:
        op.add_column("supplier_products", sa.Column("sub_category", sa.String(100), nullable=True))
    if "tags" not in existing_cols:
        op.add_column("supplier_products", sa.Column("tags", sa.JSON(), nullable=True))

    op.create_index("ix_supplier_products_category", "supplier_products", ["category"], if_not_exists=True)
    op.create_index("ix_supplier_products_manufacturer", "supplier_products", ["manufacturer"], if_not_exists=True)
    op.create_index("ix_supplier_products_in_stock", "supplier_products", ["in_stock"], if_not_exists=True)

    # -- labor_templates additions --------------------------------------------
    existing_cols = {c["name"] for c in inspector.get_columns("labor_templates")}

    if "tags" not in existing_cols:
        op.add_column("labor_templates", sa.Column("tags", sa.JSON(), nullable=True))
    if "difficulty_rating" not in existing_cols:
        op.add_column("labor_templates", sa.Column("difficulty_rating", sa.Integer(), nullable=True))
    if "required_certifications" not in existing_cols:
        op.add_column("labor_templates", sa.Column("required_certifications", sa.JSON(), nullable=True))

    # -- material_categories table --------------------------------------------
    if "material_categories" not in inspector.get_table_names():
        op.create_table(
            "material_categories",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("name", sa.String(100), nullable=False, unique=True),
            sa.Column("slug", sa.String(100), nullable=False, unique=True),
            sa.Column("parent_id", sa.Integer(), sa.ForeignKey("material_categories.id", ondelete="SET NULL"), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
            sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
        )
        op.create_index("ix_material_categories_slug", "material_categories", ["slug"])
        op.create_index("ix_material_categories_parent", "material_categories", ["parent_id"])


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if "material_categories" in inspector.get_table_names():
        op.drop_table("material_categories")

    existing_cols = {c["name"] for c in inspector.get_columns("labor_templates")}
    if "required_certifications" in existing_cols:
        op.drop_column("labor_templates", "required_certifications")
    if "difficulty_rating" in existing_cols:
        op.drop_column("labor_templates", "difficulty_rating")
    if "tags" in existing_cols:
        op.drop_column("labor_templates", "tags")

    existing_cols = {c["name"] for c in inspector.get_columns("supplier_products")}
    existing_indexes = {idx["name"] for idx in inspector.get_indexes("supplier_products")}

    if "ix_supplier_products_in_stock" in existing_indexes:
        op.drop_index("ix_supplier_products_in_stock", table_name="supplier_products")
    if "ix_supplier_products_manufacturer" in existing_indexes:
        op.drop_index("ix_supplier_products_manufacturer", table_name="supplier_products")
    if "ix_supplier_products_category" in existing_indexes:
        op.drop_index("ix_supplier_products_category", table_name="supplier_products")

    if "tags" in existing_cols:
        op.drop_column("supplier_products", "tags")
    if "sub_category" in existing_cols:
        op.drop_column("supplier_products", "sub_category")
    if "category" in existing_cols:
        op.drop_column("supplier_products", "category")
    if "msrp" in existing_cols:
        op.drop_column("supplier_products", "msrp")
    if "manufacturer" in existing_cols:
        op.drop_column("supplier_products", "manufacturer")
    if "lead_time" in existing_cols:
        op.drop_column("supplier_products", "lead_time")
    if "in_stock" in existing_cols:
        op.drop_column("supplier_products", "in_stock")
