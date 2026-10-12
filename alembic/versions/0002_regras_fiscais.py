"""regras fiscais vigentes (ações e ETFs no mercado à vista)

Revision ID: 0002
Revises: 0001


"""
from collections.abc import Sequence
from datetime import date
from decimal import Decimal

import sqlalchemy as sa
from alembic import op

from app.core.tipos import DecimalExato

revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

INICIO = date(2005, 1, 1)

regras = sa.table(
    "regras_fiscais",
    sa.column("modalidade", sa.String),
    sa.column("aliquota", DecimalExato(10, 6)),
    sa.column("aliquota_irrf", DecimalExato(10, 6)),
    sa.column("limite_isencao_acoes", DecimalExato()),
    sa.column("vigencia_inicio", sa.Date),
    sa.column("vigencia_fim", sa.Date),
)


def upgrade() -> None:
    op.bulk_insert(
        regras,
        [
            {
                "modalidade": "DAY_TRADE",
                "aliquota": Decimal("0.20"),
                "aliquota_irrf": Decimal("0.01"),
                "limite_isencao_acoes": None,
                "vigencia_inicio": INICIO,
                "vigencia_fim": None,
            },
            {
                "modalidade": "COMUM",
                "aliquota": Decimal("0.15"),
                "aliquota_irrf": Decimal("0.00005"),
                "limite_isencao_acoes": Decimal("20000.00"),
                "vigencia_inicio": INICIO,
                "vigencia_fim": None,
            },
        ],
    )


def downgrade() -> None:
    op.execute(regras.delete().where(regras.c.vigencia_inicio == INICIO))
