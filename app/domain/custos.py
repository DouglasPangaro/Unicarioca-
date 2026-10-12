from decimal import Decimal

from app.domain.modelos import ZERO, Negocio, Nota


def ratear_custos(nota: Nota) -> list[tuple[Negocio, Decimal]]:
    """Distribui os custos da nota proporcionalmente ao valor de cada negócio, sem arredondar."""
    total = sum((n.valor for n in nota.negocios), ZERO)
    if not nota.custos or not total:
        return [(n, ZERO) for n in nota.negocios]
    return [(n, nota.custos * n.valor / total) for n in nota.negocios]
