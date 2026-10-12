from datetime import date
from decimal import Decimal

from app.domain.modelos import Lado, Modalidade, Negocio, Nota, PosicaoInicial, Regra, SaldoInicial, TipoAtivo

REGRAS = (
    Regra(Modalidade.DAY_TRADE, Decimal("0.20"), Decimal("0.01"), date(2005, 1, 1)),
    Regra(
        Modalidade.COMUM, Decimal("0.15"), Decimal("0.00005"), date(2005, 1, 1),
        limite_isencao_acoes=Decimal("20000.00"),
    ),
)


def _data(valor: str | date) -> date:
    return date.fromisoformat(valor) if isinstance(valor, str) else valor


def compra(ticker: str, quantidade: int, preco: str, tipo: TipoAtivo = TipoAtivo.ACAO) -> Negocio:
    return Negocio(ticker, tipo, Lado.COMPRA, quantidade, Decimal(preco))


def venda(ticker: str, quantidade: int, preco: str, tipo: TipoAtivo = TipoAtivo.ACAO) -> Negocio:
    return Negocio(ticker, tipo, Lado.VENDA, quantidade, Decimal(preco))


def nota(data: str | date, *negocios: Negocio, corretora: str = "XP", custos: str = "0") -> Nota:
    return Nota(_data(data), corretora, tuple(negocios), Decimal(custos))


def saldo(data_referencia: str, *posicoes: tuple[str, int, str], **saldos: str) -> SaldoInicial:
    return SaldoInicial(
        _data(data_referencia),
        posicoes=tuple(PosicaoInicial(t, TipoAtivo.ACAO, q, Decimal(c)) for t, q, c in posicoes),
        **{k: Decimal(v) for k, v in saldos.items()},
    )
