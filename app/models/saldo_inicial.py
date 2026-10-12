from datetime import date
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.core.tipos import DecimalExato
from app.domain.modelos import ZERO
from app.models.cadastros import Ativo


class SaldoInicial(Base):
    __tablename__ = "saldos_iniciais"
    __table_args__ = (UniqueConstraint("usuario_id", name="uq_saldos_iniciais_usuario"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"))
    data_referencia: Mapped[date] = mapped_column(Date)
    prejuizo_day_trade: Mapped[Decimal] = mapped_column(DecimalExato(), default=ZERO)
    prejuizo_comum: Mapped[Decimal] = mapped_column(DecimalExato(), default=ZERO)
    imposto_pendente: Mapped[Decimal] = mapped_column(DecimalExato(), default=ZERO)

    posicoes: Mapped[list["PosicaoInicial"]] = relationship(
        cascade="all, delete-orphan", order_by="PosicaoInicial.id"
    )


class PosicaoInicial(Base):
    __tablename__ = "posicoes_iniciais"
    __table_args__ = (
        UniqueConstraint("saldo_inicial_id", "ativo_id", name="uq_posicoes_iniciais_saldo_ativo"),
        CheckConstraint("quantidade > 0", name="ck_posicoes_iniciais_quantidade"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    saldo_inicial_id: Mapped[int] = mapped_column(ForeignKey("saldos_iniciais.id", ondelete="CASCADE"))
    ativo_id: Mapped[int] = mapped_column(ForeignKey("ativos.id"), index=True)
    quantidade: Mapped[int] = mapped_column(Integer)
    custo_total: Mapped[Decimal] = mapped_column(DecimalExato())

    ativo: Mapped[Ativo] = relationship(lazy="joined")

    @property
    def ticker(self) -> str:
        return self.ativo.ticker
