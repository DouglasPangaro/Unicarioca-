from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal

from app.domain.erros import PosicaoInsuficiente
from app.domain.modelos import ZERO, EventoComum, Posicao, PosicaoInicial, TipoAtivo, VendaComum


@dataclass
class _Saldo:
    tipo_ativo: TipoAtivo
    quantidade: int = 0
    custo_total: Decimal = ZERO


class Carteira:
    """Posição e preço médio por ativo, consolidando todas as corretoras."""

    def __init__(self, posicoes: Iterable[PosicaoInicial] = ()):
        self._saldos: dict[str, _Saldo] = {
            p.ticker: _Saldo(p.tipo_ativo, p.quantidade, p.custo_total) for p in posicoes
        }

    def comprar(self, evento: EventoComum) -> None:
        saldo = self._saldos.setdefault(evento.ticker, _Saldo(evento.tipo_ativo))
        saldo.tipo_ativo = evento.tipo_ativo
        saldo.quantidade += evento.quantidade
        saldo.custo_total += evento.valor_liquido

    def vender(self, evento: EventoComum) -> VendaComum:
        saldo = self._saldos.get(evento.ticker) or _Saldo(evento.tipo_ativo)
        if evento.quantidade > saldo.quantidade:
            raise PosicaoInsuficiente(evento.ticker, evento.data, saldo.quantidade, evento.quantidade)
        if evento.quantidade == saldo.quantidade:
            baixa = saldo.custo_total
        else:
            baixa = saldo.custo_total * evento.quantidade / saldo.quantidade
        saldo.quantidade -= evento.quantidade
        saldo.custo_total -= baixa
        return VendaComum(
            evento.data, evento.corretora, evento.ticker, evento.tipo_ativo, evento.quantidade,
            valor_venda=evento.valor_bruto, valor_liquido=evento.valor_liquido, custo_aquisicao=baixa,
        )

    def posicoes(self) -> tuple[Posicao, ...]:
        return tuple(
            Posicao(ticker, s.tipo_ativo, s.quantidade, s.custo_total)
            for ticker, s in sorted(self._saldos.items())
            if s.quantidade
        )
