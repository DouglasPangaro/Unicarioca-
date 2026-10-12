"""esquema inicial

Revision ID: 0001

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from app.core.tipos import DecimalExato

revision: str = "0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _dinheiro(nome: str, nullable: bool = False) -> sa.Column:
    return sa.Column(nome, DecimalExato(), nullable=nullable)


def _usuario_id() -> sa.Column:
    return sa.Column("usuario_id", sa.Integer(), sa.ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False)


def upgrade() -> None:
    op.create_table(
        "usuarios",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("senha_hash", sa.String(255), nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("email", name="uq_usuarios_email"),
    )

    op.create_table(
        "corretoras",
        sa.Column("id", sa.Integer(), primary_key=True),
        _usuario_id(),
        sa.Column("nome", sa.String(100), nullable=False),
        sa.Column("cnpj", sa.String(18), nullable=True),
        sa.UniqueConstraint("usuario_id", "nome", name="uq_corretoras_usuario_nome"),
    )
    op.create_index("ix_corretoras_usuario_id", "corretoras", ["usuario_id"])

    op.create_table(
        "ativos",
        sa.Column("id", sa.Integer(), primary_key=True),
        _usuario_id(),
        sa.Column("ticker", sa.String(12), nullable=False),
        sa.Column("tipo", sa.String(10), nullable=False),
        sa.Column("nome", sa.String(100), nullable=True),
        sa.Column("cnpj", sa.String(18), nullable=True),
        sa.UniqueConstraint("usuario_id", "ticker", name="uq_ativos_usuario_ticker"),
        sa.CheckConstraint("tipo IN ('ACAO', 'ETF')", name="ck_ativos_tipo"),
    )
    op.create_index("ix_ativos_usuario_id", "ativos", ["usuario_id"])

    op.create_table(
        "notas",
        sa.Column("id", sa.Integer(), primary_key=True),
        _usuario_id(),
        sa.Column("corretora_id", sa.Integer(), sa.ForeignKey("corretoras.id"), nullable=False),
        sa.Column("data_pregao", sa.Date(), nullable=False),
        sa.Column("numero", sa.String(30), nullable=True),
        _dinheiro("corretagem"),
        _dinheiro("emolumentos"),
        _dinheiro("taxa_liquidacao"),
        _dinheiro("iss"),
        _dinheiro("outras_taxas"),
        sa.Column("origem", sa.String(20), nullable=False),
        sa.Column("custos_pendentes", sa.Boolean(), nullable=False),
    )
    op.create_index("ix_notas_usuario_data", "notas", ["usuario_id", "data_pregao"])

    op.create_table(
        "operacoes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nota_id", sa.Integer(), sa.ForeignKey("notas.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ativo_id", sa.Integer(), sa.ForeignKey("ativos.id"), nullable=False),
        sa.Column("lado", sa.String(1), nullable=False),
        sa.Column("quantidade", sa.Integer(), nullable=False),
        _dinheiro("preco"),
        sa.Column("chave_importacao", sa.String(64), nullable=True),
        sa.UniqueConstraint("chave_importacao", name="uq_operacoes_chave_importacao"),
        sa.CheckConstraint("quantidade > 0", name="ck_operacoes_quantidade"),
        sa.CheckConstraint("lado IN ('C', 'V')", name="ck_operacoes_lado"),
    )
    op.create_index("ix_operacoes_nota_id", "operacoes", ["nota_id"])
    op.create_index("ix_operacoes_ativo_id", "operacoes", ["ativo_id"])

    op.create_table(
        "pagamentos_darf",
        sa.Column("id", sa.Integer(), primary_key=True),
        _usuario_id(),
        sa.Column("competencia", sa.String(7), nullable=False),
        _dinheiro("valor_principal"),
        _dinheiro("multa"),
        _dinheiro("juros"),
        _dinheiro("valor_total"),
        sa.Column("data_pagamento", sa.Date(), nullable=False),
        sa.Column("registrado_em", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("usuario_id", "competencia", name="uq_pagamentos_darf_usuario_competencia"),
    )
    op.create_index("ix_pagamentos_darf_usuario_id", "pagamentos_darf", ["usuario_id"])

    op.create_table(
        "regras_fiscais",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("modalidade", sa.String(20), nullable=False),
        sa.Column("aliquota", DecimalExato(10, 6), nullable=False),
        sa.Column("aliquota_irrf", DecimalExato(10, 6), nullable=False),
        _dinheiro("limite_isencao_acoes", nullable=True),
        sa.Column("vigencia_inicio", sa.Date(), nullable=False),
        sa.Column("vigencia_fim", sa.Date(), nullable=True),
    )

    op.create_table(
        "saldos_iniciais",
        sa.Column("id", sa.Integer(), primary_key=True),
        _usuario_id(),
        sa.Column("data_referencia", sa.Date(), nullable=False),
        _dinheiro("prejuizo_day_trade"),
        _dinheiro("prejuizo_comum"),
        _dinheiro("imposto_pendente"),
        sa.UniqueConstraint("usuario_id", name="uq_saldos_iniciais_usuario"),
    )

    op.create_table(
        "posicoes_iniciais",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "saldo_inicial_id", sa.Integer(), sa.ForeignKey("saldos_iniciais.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("ativo_id", sa.Integer(), sa.ForeignKey("ativos.id"), nullable=False),
        sa.Column("quantidade", sa.Integer(), nullable=False),
        _dinheiro("custo_total"),
        sa.UniqueConstraint("saldo_inicial_id", "ativo_id", name="uq_posicoes_iniciais_saldo_ativo"),
        sa.CheckConstraint("quantidade > 0", name="ck_posicoes_iniciais_quantidade"),
    )
    op.create_index("ix_posicoes_iniciais_ativo_id", "posicoes_iniciais", ["ativo_id"])


def downgrade() -> None:
    for tabela in (
        "posicoes_iniciais",
        "saldos_iniciais",
        "regras_fiscais",
        "pagamentos_darf",
        "operacoes",
        "notas",
        "ativos",
        "corretoras",
        "usuarios",
    ):
        op.drop_table(tabela)
