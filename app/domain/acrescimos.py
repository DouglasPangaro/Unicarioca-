from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.domain.calendario import mes_anterior, mes_seguinte, meses_entre
from app.domain.modelos import ZERO, q2

MULTA_DIARIA = Decimal("0.0033")
MULTA_TETO = Decimal("0.20")
JUROS_MES_PAGAMENTO = Decimal("1")


@dataclass(frozen=True)
class Acrescimos:
    principal: Decimal
    vencimento: date
    data_pagamento: date
    dias_atraso: int
    multa_percentual: Decimal
    multa: Decimal
    juros_percentual: Decimal
    juros: Decimal

    @property
    def total(self) -> Decimal:
        return self.principal + self.multa + self.juros


def meses_selic(vencimento: date, data_pagamento: date) -> list[tuple[int, int]]:
    """Do mês seguinte ao vencimento até o mês anterior ao pagamento."""
    return meses_entre(
        mes_seguinte(vencimento.year, vencimento.month),
        mes_anterior(data_pagamento.year, data_pagamento.month),
    )


def calcular_acrescimos(
    principal: Decimal,
    vencimento: date,
    data_pagamento: date,
    selic_mensal: Mapping[tuple[int, int], Decimal],
) -> Acrescimos:
    """Multa de 0,33% ao dia (teto 20%) e juros Selic acumulada + 1% no mês do pagamento (Lei 9.430/96, art. 61)."""
    if data_pagamento <= vencimento:
        return Acrescimos(principal, vencimento, data_pagamento, 0, ZERO, ZERO, ZERO, ZERO)

    dias = (data_pagamento - vencimento).days
    taxa_multa = min(MULTA_DIARIA * dias, MULTA_TETO)

    juros_percentual = ZERO
    if (data_pagamento.year, data_pagamento.month) > (vencimento.year, vencimento.month):
        meses = meses_selic(vencimento, data_pagamento)
        faltando = [m for m in meses if m not in selic_mensal]
        if faltando:
            raise ValueError(f"Selic ausente para {faltando}")
        juros_percentual = sum((selic_mensal[m] for m in meses), ZERO) + JUROS_MES_PAGAMENTO

    return Acrescimos(
        principal=principal,
        vencimento=vencimento,
        data_pagamento=data_pagamento,
        dias_atraso=dias,
        multa_percentual=taxa_multa * 100,
        multa=q2(principal * taxa_multa),
        juros_percentual=juros_percentual,
        juros=q2(principal * juros_percentual / 100),
    )
