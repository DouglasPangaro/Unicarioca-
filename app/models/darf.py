from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.core.tipos import DecimalExato


class PagamentoDarf(Base):
    __tablename__ = "pagamentos_darf"
    __table_args__ = (UniqueConstraint("usuario_id", "competencia", name="uq_pagamentos_darf_usuario_competencia"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), index=True)
    competencia: Mapped[str] = mapped_column(String(7))
    valor_principal: Mapped[Decimal] = mapped_column(DecimalExato())
    multa: Mapped[Decimal] = mapped_column(DecimalExato())
    juros: Mapped[Decimal] = mapped_column(DecimalExato())
    valor_total: Mapped[Decimal] = mapped_column(DecimalExato())
    data_pagamento: Mapped[date] = mapped_column(Date)
    registrado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
