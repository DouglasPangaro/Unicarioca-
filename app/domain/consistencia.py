from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from decimal import Decimal

from app.domain.modelos import ZERO, ApuracaoMensal


@dataclass(frozen=True)
class Divergencia:
    competencia: str
    valor_pago: Decimal
    valor_recalculado: Decimal

    @property
    def diferenca(self) -> Decimal:
        return self.valor_recalculado - self.valor_pago


def verificar_pagamentos(meses: Iterable[ApuracaoMensal], pagos: Mapping[str, Decimal]) -> list[Divergencia]:
    """Competências pagas cujo DARF recalculado não bate mais com o valor principal pago."""
    darfs = {m.competencia: m.darf.valor for m in meses if m.darf}
    return [
        Divergencia(comp, pago, darfs.get(comp, ZERO))
        for comp, pago in sorted(pagos.items())
        if darfs.get(comp, ZERO) != pago
    ]
