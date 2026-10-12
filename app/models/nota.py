from datetime import date
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import Boolean, CheckConstraint, Date, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.core.tipos import DecimalExato
from app.domain.modelos import ZERO
from app.models.cadastros import Ativo, Corretora


class OrigemNota(StrEnum):
    MANUAL = "MANUAL"
    IMPORTACAO_B3 = "IMPORTACAO_B3"


class NotaCorretagem(Base):
    __tablename__ = "notas"
    __table_args__ = (Index("ix_notas_usuario_data", "usuario_id", "data_pregao"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"))
    corretora_id: Mapped[int] = mapped_column(ForeignKey("corretoras.id"))
    data_pregao: Mapped[date] = mapped_column(Date)
    numero: Mapped[str | None] = mapped_column(String(30))
    corretagem: Mapped[Decimal] = mapped_column(DecimalExato(), default=ZERO)
    emolumentos: Mapped[Decimal] = mapped_column(DecimalExato(), default=ZERO)
    taxa_liquidacao: Mapped[Decimal] = mapped_column(DecimalExato(), default=ZERO)
    iss: Mapped[Decimal] = mapped_column(DecimalExato(), default=ZERO)
    outras_taxas: Mapped[Decimal] = mapped_column(DecimalExato(), default=ZERO)
    origem: Mapped[str] = mapped_column(String(20), default=OrigemNota.MANUAL)
    custos_pendentes: Mapped[bool] = mapped_column(Boolean, default=False)

    corretora: Mapped[Corretora] = relationship(lazy="joined")
    operacoes: Mapped[list["Operacao"]] = relationship(
        back_populates="nota", cascade="all, delete-orphan", order_by="Operacao.id"
    )

    @property
    def custos_totais(self) -> Decimal:
        return self.corretagem + self.emolumentos + self.taxa_liquidacao + self.iss + self.outras_taxas

    @property
    def corretora_nome(self) -> str:
        return self.corretora.nome


class Operacao(Base):
    __tablename__ = "operacoes"
    __table_args__ = (
        UniqueConstraint("chave_importacao", name="uq_operacoes_chave_importacao"),
        CheckConstraint("quantidade > 0", name="ck_operacoes_quantidade"),
        CheckConstraint("lado IN ('C', 'V')", name="ck_operacoes_lado"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    nota_id: Mapped[int] = mapped_column(ForeignKey("notas.id", ondelete="CASCADE"), index=True)
    ativo_id: Mapped[int] = mapped_column(ForeignKey("ativos.id"), index=True)
    lado: Mapped[str] = mapped_column(String(1))
    quantidade: Mapped[int] = mapped_column(Integer)
    preco: Mapped[Decimal] = mapped_column(DecimalExato())
    chave_importacao: Mapped[str | None] = mapped_column(String(64))

    nota: Mapped[NotaCorretagem] = relationship(back_populates="operacoes")
    ativo: Mapped[Ativo] = relationship(lazy="joined")

    @property
    def ticker(self) -> str:
        return self.ativo.ticker
