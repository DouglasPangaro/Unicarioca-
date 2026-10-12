from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.domain.custos import ratear_custos
from app.domain.modelos import ZERO, EventoComum, EventoDayTrade, Lado, Nota, TipoAtivo


@dataclass
class _Acumulado:
    quantidade: int = 0
    valor: Decimal = ZERO
    custos: Decimal = ZERO


def classificar(notas: Iterable[Nota]) -> tuple[list[EventoDayTrade], list[EventoComum]]:
    """Separa day trade (mesmo dia, ativo e corretora) do excedente, que vira operação comum."""
    grupos: dict[tuple[date, str, str], dict[Lado, _Acumulado]] = defaultdict(
        lambda: {Lado.COMPRA: _Acumulado(), Lado.VENDA: _Acumulado()}
    )
    tipos: dict[str, TipoAtivo] = {}
    for nota in notas:
        for negocio, custo in ratear_custos(nota):
            acumulado = grupos[(nota.data, nota.corretora, negocio.ticker)][negocio.lado]
            acumulado.quantidade += negocio.quantidade
            acumulado.valor += negocio.valor
            acumulado.custos += custo
            tipos[negocio.ticker] = negocio.tipo_ativo

    eventos_dt: list[EventoDayTrade] = []
    eventos_comuns: list[EventoComum] = []
    for (data, corretora, ticker), lados in sorted(grupos.items()):
        compra, venda = lados[Lado.COMPRA], lados[Lado.VENDA]
        tipo = tipos[ticker]
        qtd_dt = min(compra.quantidade, venda.quantidade)
        if qtd_dt:
            eventos_dt.append(
                EventoDayTrade(
                    data, corretora, ticker, tipo, qtd_dt,
                    preco_medio_compra=(compra.valor + compra.custos) / compra.quantidade,
                    preco_medio_venda=(venda.valor - venda.custos) / venda.quantidade,
                )
            )
        for lado, acumulado in ((Lado.COMPRA, compra), (Lado.VENDA, venda)):
            sobra = acumulado.quantidade - qtd_dt
            if not sobra:
                continue
            liquido = acumulado.valor + acumulado.custos if lado is Lado.COMPRA else acumulado.valor - acumulado.custos
            eventos_comuns.append(
                EventoComum(
                    data, corretora, ticker, tipo, lado, sobra,
                    valor_bruto=acumulado.valor * sobra / acumulado.quantidade,
                    valor_liquido=liquido * sobra / acumulado.quantidade,
                )
            )
    return eventos_dt, eventos_comuns
