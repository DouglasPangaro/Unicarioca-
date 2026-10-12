from datetime import date
from decimal import Decimal

from sqlalchemy import Date, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.core.tipos import DecimalExato


class RegraFiscal(Base):
    __tablename__ = "regras_fiscais"

    id: Mapped[int] = mapped_column(primary_key=True)
    modalidade: Mapped[str] = mapped_column(String(20))
    aliquota: Mapped[Decimal] = mapped_column(DecimalExato(10, 6))
    aliquota_irrf: Mapped[Decimal] = mapped_column(DecimalExato(10, 6))
    limite_isencao_acoes: Mapped[Decimal | None] = mapped_column(DecimalExato())
    vigencia_inicio: Mapped[date] = mapped_column(Date)
    vigencia_fim: Mapped[date | None] = mapped_column(Date)
