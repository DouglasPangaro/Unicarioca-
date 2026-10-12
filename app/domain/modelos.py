from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum

ZERO = Decimal("0")
CENTAVO = Decimal("0.01")


def q2(valor: Decimal) -> Decimal:
    return valor.quantize(CENTAVO, rounding=ROUND_HALF_UP)


def competencia(ano: int, mes: int) -> str:
    return f"{ano:04d}-{mes:02d}"


def ler_competencia(texto: str) -> tuple[int, int]:
    ano, mes = texto.split("-")
    return int(ano), int(mes)


class Lado(StrEnum):
    COMPRA = "C"
    VENDA = "V"


class TipoAtivo(StrEnum):
    ACAO = "ACAO"
    ETF = "ETF"


class Modalidade(StrEnum):
    DAY_TRADE = "DAY_TRADE"
    COMUM = "COMUM"


@dataclass(frozen=True)
class Regra:
    modalidade: Modalidade
    aliquota: Decimal
    aliquota_irrf: Decimal
    vigencia_inicio: date
    vigencia_fim: date | None = None
    limite_isencao_acoes: Decimal | None = None


@dataclass(frozen=True)
class Negocio:
    ticker: str
    tipo_ativo: TipoAtivo
    lado: Lado
    quantidade: int
    preco: Decimal

    @property
    def valor(self) -> Decimal:
        return self.preco * self.quantidade


@dataclass(frozen=True)
class Nota:
    data: date
    corretora: str
    negocios: tuple[Negocio, ...]
    custos: Decimal = ZERO


@dataclass(frozen=True)
class PosicaoInicial:
    ticker: str
    tipo_ativo: TipoAtivo
    quantidade: int
    custo_total: Decimal


@dataclass(frozen=True)
class SaldoInicial:
    data_referencia: date
    prejuizo_day_trade: Decimal = ZERO
    prejuizo_comum: Decimal = ZERO
    imposto_pendente: Decimal = ZERO
    posicoes: tuple[PosicaoInicial, ...] = ()


@dataclass(frozen=True)
class EventoDayTrade:
    data: date
    corretora: str
    ticker: str
    tipo_ativo: TipoAtivo
    quantidade: int
    preco_medio_compra: Decimal
    preco_medio_venda: Decimal

    @property
    def resultado(self) -> Decimal:
        return (self.preco_medio_venda - self.preco_medio_compra) * self.quantidade


@dataclass(frozen=True)
class EventoComum:
    data: date
    corretora: str
    ticker: str
    tipo_ativo: TipoAtivo
    lado: Lado
    quantidade: int
    valor_bruto: Decimal
    valor_liquido: Decimal


@dataclass(frozen=True)
class VendaComum:
    data: date
    corretora: str
    ticker: str
    tipo_ativo: TipoAtivo
    quantidade: int
    valor_venda: Decimal
    valor_liquido: Decimal
    custo_aquisicao: Decimal

    @property
    def preco_medio(self) -> Decimal:
        return self.custo_aquisicao / self.quantidade

    @property
    def resultado(self) -> Decimal:
        return self.valor_liquido - self.custo_aquisicao


@dataclass(frozen=True)
class Posicao:
    ticker: str
    tipo_ativo: TipoAtivo
    quantidade: int
    custo_total: Decimal

    @property
    def preco_medio(self) -> Decimal:
        return self.custo_total / self.quantidade if self.quantidade else ZERO


@dataclass(frozen=True)
class ResultadoModalidade:
    resultado_liquido: Decimal
    prejuizo_anterior: Decimal
    prejuizo_compensado: Decimal
    base_calculo: Decimal
    prejuizo_a_compensar: Decimal
    aliquota: Decimal
    imposto: Decimal


@dataclass(frozen=True)
class Isencao:
    vendas_acoes: Decimal
    limite: Decimal | None
    isento: bool
    lucro_isento: Decimal


@dataclass(frozen=True)
class SaldoIRRF:
    do_mes: Decimal
    meses_anteriores: Decimal
    compensado: Decimal
    a_compensar: Decimal


@dataclass(frozen=True)
class Darf:
    competencia: str
    codigo: str
    valor: Decimal
    vencimento: date


@dataclass(frozen=True)
class ApuracaoMensal:
    ano: int
    mes: int
    day_trade: ResultadoModalidade
    comum: ResultadoModalidade
    isencao: Isencao
    imposto_devido: Decimal
    irrf_day_trade: SaldoIRRF
    irrf_comum: SaldoIRRF
    imposto_a_pagar: Decimal
    imposto_pendente_anterior: Decimal
    imposto_pendente: Decimal
    darf: Darf | None
    eventos_day_trade: tuple[EventoDayTrade, ...] = ()
    vendas_comuns: tuple[VendaComum, ...] = ()

    @property
    def competencia(self) -> str:
        return competencia(self.ano, self.mes)


@dataclass(frozen=True)
class ResultadoApuracao:
    meses: tuple[ApuracaoMensal, ...]
    posicoes: tuple[Posicao, ...]

    def mes(self, ano: int, mes: int) -> ApuracaoMensal | None:
        return next((m for m in self.meses if (m.ano, m.mes) == (ano, mes)), None)
