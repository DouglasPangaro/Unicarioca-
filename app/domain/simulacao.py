from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from app.domain.apuracao import apuracao_vazia, apurar
from app.domain.calendario import ultimo_dia
from app.domain.modelos import ZERO, ApuracaoMensal, Nota, Regra, SaldoInicial


@dataclass(frozen=True)
class ResultadoSimulacao:
    competencia: str
    quantidade_day_trade: int
    quantidade_comum: int
    resultado_day_trade: Decimal
    resultado_comum: Decimal
    vendas_acoes_antes: Decimal
    vendas_acoes_depois: Decimal
    isento_antes: bool
    isento_depois: bool
    imposto_devido_antes: Decimal
    imposto_devido_depois: Decimal
    darf_antes: Decimal
    darf_depois: Decimal

    @property
    def modalidade(self) -> str:
        if not self.quantidade_comum:
            return "DAY_TRADE"
        return "COMUM" if not self.quantidade_day_trade else "MISTA"

    @property
    def perde_isencao(self) -> bool:
        return self.isento_antes and not self.isento_depois

    @property
    def diferenca_darf(self) -> Decimal:
        return self.darf_depois - self.darf_antes


def _resultado_comum_total(mes: ApuracaoMensal) -> Decimal:
    return mes.comum.resultado_liquido + mes.isencao.lucro_isento


def simular_venda(
    notas: Sequence[Nota], regras: Sequence[Regra], saldo_inicial: SaldoInicial | None, venda: Nota
) -> ResultadoSimulacao:
    """Compara o mês da venda hipotética com e sem ela; nada é gravado."""
    ano, mes = venda.data.year, venda.data.month
    ate = ultimo_dia(ano, mes)
    antes = apurar(notas, regras, saldo_inicial, ate=ate).mes(ano, mes) or apuracao_vazia(ano, mes, regras)
    depois = apurar([*notas, venda], regras, saldo_inicial, ate=ate).mes(ano, mes) or apuracao_vazia(
        ano, mes, regras
    )

    negocio = venda.negocios[0]
    chave = (venda.data, venda.corretora, negocio.ticker)

    def qtd_day_trade(apuracao: ApuracaoMensal) -> int:
        return sum(e.quantidade for e in apuracao.eventos_day_trade if (e.data, e.corretora, e.ticker) == chave)

    qtd_dt = qtd_day_trade(depois) - qtd_day_trade(antes)
    return ResultadoSimulacao(
        competencia=depois.competencia,
        quantidade_day_trade=qtd_dt,
        quantidade_comum=negocio.quantidade - qtd_dt,
        resultado_day_trade=depois.day_trade.resultado_liquido - antes.day_trade.resultado_liquido,
        resultado_comum=_resultado_comum_total(depois) - _resultado_comum_total(antes),
        vendas_acoes_antes=antes.isencao.vendas_acoes,
        vendas_acoes_depois=depois.isencao.vendas_acoes,
        isento_antes=antes.isencao.isento,
        isento_depois=depois.isencao.isento,
        imposto_devido_antes=antes.imposto_devido,
        imposto_devido_depois=depois.imposto_devido,
        darf_antes=antes.darf.valor if antes.darf else ZERO,
        darf_depois=depois.darf.valor if depois.darf else ZERO,
    )
