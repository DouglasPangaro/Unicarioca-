from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal

from app.domain.apuracao import apuracao_vazia
from app.domain.modelos import (
    ZERO,
    ApuracaoMensal,
    Posicao,
    Regra,
    ResultadoModalidade,
    SaldoIRRF,
    TipoAtivo,
    competencia,
    q2,
)

# Bens e Direitos: Ações = grupo 03, código 01; o código de ETF (grupo 07) deve ser conferido na tabela do ano
GRUPO_CODIGO: dict[TipoAtivo, tuple[str, str | None]] = {
    TipoAtivo.ACAO: ("03", "01"),
    TipoAtivo.ETF: ("07", None),
}


@dataclass(frozen=True)
class MesIRPF:
    mes: int
    comum: ResultadoModalidade
    day_trade: ResultadoModalidade
    imposto_devido: Decimal
    irrf_day_trade: SaldoIRRF
    irrf_comum: SaldoIRRF
    imposto_a_pagar: Decimal
    imposto_pago: Decimal


@dataclass(frozen=True)
class BemDireito:
    ticker: str
    tipo_ativo: TipoAtivo
    grupo: str
    codigo: str | None
    quantidade_anterior: int
    situacao_anterior: Decimal
    quantidade_atual: int
    situacao_atual: Decimal
    discriminacao: str


@dataclass(frozen=True)
class RelatorioIRPF:
    ano: int
    renda_variavel: tuple[MesIRPF, ...]
    lucro_isento_acoes: Decimal
    bens_e_direitos: tuple[BemDireito, ...]
    irrf_a_compensar_na_declaracao: Decimal
    prejuizo_day_trade_a_compensar: Decimal
    prejuizo_comum_a_compensar: Decimal


def formatar_brl(valor: Decimal) -> str:
    return f"{q2(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _bens_e_direitos(
    ano: int, anteriores: Iterable[Posicao], atuais: Iterable[Posicao]
) -> tuple[BemDireito, ...]:
    antes = {p.ticker: p for p in anteriores}
    agora = {p.ticker: p for p in atuais}
    bens = []
    for ticker in sorted(antes.keys() | agora.keys()):
        anterior, atual = antes.get(ticker), agora.get(ticker)
        tipo = (atual or anterior).tipo_ativo
        grupo, codigo = GRUPO_CODIGO[tipo]
        if atual:
            unidade = "ações" if tipo is TipoAtivo.ACAO else "cotas"
            texto = f"{atual.quantidade} {unidade} {ticker}, custo médio de R$ {formatar_brl(atual.preco_medio)}."
        else:
            texto = f"{ticker}: posição zerada em 31/12/{ano}."
        bens.append(
            BemDireito(
                ticker=ticker,
                tipo_ativo=tipo,
                grupo=grupo,
                codigo=codigo,
                quantidade_anterior=anterior.quantidade if anterior else 0,
                situacao_anterior=q2(anterior.custo_total) if anterior else ZERO,
                quantidade_atual=atual.quantidade if atual else 0,
                situacao_atual=q2(atual.custo_total) if atual else ZERO,
                discriminacao=texto,
            )
        )
    return tuple(bens)


def montar_relatorio(
    ano: int,
    meses: Iterable[ApuracaoMensal],
    regras: Sequence[Regra],
    posicoes_anteriores: Iterable[Posicao],
    posicoes_atuais: Iterable[Posicao],
    impostos_pagos: Mapping[str, Decimal],
) -> RelatorioIRPF:
    """Monta a ficha Renda Variável mês a mês, os isentos e Bens e Direitos do ano."""
    por_mes = {m.mes: m for m in meses if m.ano == ano}
    linhas = []
    for mes in range(1, 13):
        m = por_mes.get(mes) or apuracao_vazia(ano, mes, regras)
        linhas.append(
            MesIRPF(
                mes=mes,
                comum=m.comum,
                day_trade=m.day_trade,
                imposto_devido=m.imposto_devido,
                irrf_day_trade=m.irrf_day_trade,
                irrf_comum=m.irrf_comum,
                imposto_a_pagar=m.imposto_a_pagar,
                imposto_pago=impostos_pagos.get(competencia(ano, mes), ZERO),
            )
        )
    dezembro = por_mes.get(12)
    return RelatorioIRPF(
        ano=ano,
        renda_variavel=tuple(linhas),
        lucro_isento_acoes=sum((m.isencao.lucro_isento for m in por_mes.values()), ZERO),
        bens_e_direitos=_bens_e_direitos(ano, posicoes_anteriores, posicoes_atuais),
        irrf_a_compensar_na_declaracao=(
            dezembro.irrf_day_trade.a_compensar + dezembro.irrf_comum.a_compensar if dezembro else ZERO
        ),
        prejuizo_day_trade_a_compensar=dezembro.day_trade.prejuizo_a_compensar if dezembro else ZERO,
        prejuizo_comum_a_compensar=dezembro.comum.prejuizo_a_compensar if dezembro else ZERO,
    )
