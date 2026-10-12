from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Corretora(Base):
    __tablename__ = "corretoras"
    __table_args__ = (UniqueConstraint("usuario_id", "nome", name="uq_corretoras_usuario_nome"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), index=True)
    nome: Mapped[str] = mapped_column(String(100))
    cnpj: Mapped[str | None] = mapped_column(String(18))


class Ativo(Base):
    __tablename__ = "ativos"
    __table_args__ = (
        UniqueConstraint("usuario_id", "ticker", name="uq_ativos_usuario_ticker"),
        CheckConstraint("tipo IN ('ACAO', 'ETF')", name="ck_ativos_tipo"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), index=True)
    ticker: Mapped[str] = mapped_column(String(12))
    tipo: Mapped[str] = mapped_column(String(10))
    nome: Mapped[str | None] = mapped_column(String(100))
    cnpj: Mapped[str | None] = mapped_column(String(18))
