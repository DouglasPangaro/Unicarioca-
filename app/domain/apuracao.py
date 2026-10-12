from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.domain.calendario import mes_seguinte, meses_entre, vencimento_darf
from app.domain.carteira import Carteira
from app.domain.classificador import classificar
from app.domain.erros import OperacaoAntesDoSaldoInicial, RegraNaoEncontrada
from app.domain.modelos import (
    ZERO,
    ApuracaoMensal,
    Darf,
    EventoComum,
    EventoDayTrade,
    Isencao,
    Lado,
    Modalidade,
    Nota,
    Regra,
    ResultadoApuracao,
    ResultadoModalidade,
    SaldoInicial,
    SaldoIRRF,
    TipoAtivo,
    VendaComum,
    competencia,
    q2,
)

DARF_CODIGO = "6015"
DARF_MINIMO = Decimal("10.00")
IRRF_COMUM_DISPENSA = Decimal("1.00")


def regra_vigente(regras: Iterable[Regra], modalidade: Modalidade, dia: date) -> Regra:
    candidatas = [
        r for r in regras
        if r.modalidade == modalidade
        and r.vigencia_inicio <= dia
        and (r.vigencia_fim is None or dia <= r.vigencia_fim)
    ]
    if not candidatas:
        raise RegraNaoEncontrada(f"Nenhuma regra fiscal de {modalidade.value} vigente em {dia:%m/%Y}.")
    return max(candidatas, key=lambda r: r.vigencia_inicio)


def _compensar(resultado: Decimal, prejuizo_anterior: Decimal, aliquota: Decimal) -> ResultadoModalidade:
    if resultado > 0:
        compensado = min(prejuizo_anterior, resultado)
        base = resultado - compensado
        prejuizo = prejuizo_anterior - compensado
    else:
        compensado, base, prejuizo = ZERO, ZERO, prejuizo_anterior - resultado
    return ResultadoModalidade(
        resultado_liquido=resultado,
        prejuizo_anterior=prejuizo_anterior,
        prejuizo_compensado=compensado,
        base_calculo=base,
        prejuizo_a_compensar=prejuizo,
        aliquota=aliquota,
        imposto=q2(base * aliquota),
    )


def _abater_irrf(imposto: Decimal, saldo_anterior: Decimal, do_mes: Decimal) -> SaldoIRRF:
    disponivel = saldo_anterior + do_mes
    compensado = min(disponivel, imposto)
    return SaldoIRRF(do_mes, saldo_anterior, compensado, disponivel - compensado)


def _irrf_day_trade(eventos: Iterable[EventoDayTrade], aliquota: Decimal) -> Decimal:
    """1% do resultado positivo do dia, por corretora (perdas do mesmo dia e corretora compensam)."""
    por_dia: dict[tuple[date, str], Decimal] = defaultdict(lambda: ZERO)
    for evento in eventos:
        por_dia[(evento.data, evento.corretora)] += evento.resultado
    return sum((q2(max(ZERO, q2(r)) * aliquota) for r in por_dia.values()), ZERO)


def _irrf_comum(vendas: Iterable[VendaComum], aliquota: Decimal) -> Decimal:
    """0,005% das vendas somadas por corretora no mês; até R$ 1,00 a retenção é dispensada."""
    por_corretora: dict[str, Decimal] = defaultdict(lambda: ZERO)
    for venda in vendas:
        por_corretora[venda.corretora] += venda.valor_venda
    total = ZERO
    for valor in por_corretora.values():
        irrf = q2(valor * aliquota)
        if irrf > IRRF_COMUM_DISPENSA:
            total += irrf
    return total


@dataclass
class _Saldos:
    prejuizo_dt: Decimal = ZERO
    prejuizo_comum: Decimal = ZERO
    irrf_dt: Decimal = ZERO
    irrf_comum: Decimal = ZERO
    imposto_pendente: Decimal = ZERO


def _apurar_mes(
    ano: int,
    mes: int,
    eventos_dt: list[EventoDayTrade],
    eventos_comuns: list[EventoComum],
    carteira: Carteira,
    regras: Sequence[Regra],
    saldos: _Saldos,
) -> ApuracaoMensal:
    vendas: list[VendaComum] = []
    # sem horário dos negócios, as compras comuns do dia entram antes das vendas
    for evento in sorted(eventos_comuns, key=lambda e: (e.data, e.lado is Lado.VENDA, e.corretora, e.ticker)):
        if evento.lado is Lado.COMPRA:
            carteira.comprar(evento)
        else:
            vendas.append(carteira.vender(evento))

    primeiro_dia = date(ano, mes, 1)
    regra_dt = regra_vigente(regras, Modalidade.DAY_TRADE, primeiro_dia)
    regra_comum = regra_vigente(regras, Modalidade.COMUM, primeiro_dia)

    resultado_dt = q2(sum((e.resultado for e in eventos_dt), ZERO))

    vendas_acoes = [v for v in vendas if v.tipo_ativo is TipoAtivo.ACAO]
    total_vendas_acoes = q2(sum((v.valor_venda for v in vendas_acoes), ZERO))
    resultado_acoes = q2(sum((v.resultado for v in vendas_acoes), ZERO))
    resultado_outros = q2(sum((v.resultado for v in vendas if v.tipo_ativo is not TipoAtivo.ACAO), ZERO))
    limite = regra_comum.limite_isencao_acoes
    isento = limite is not None and total_vendas_acoes <= limite
    # lucro isento não consome prejuízo; prejuízo de mês isento continua acumulando
    lucro_isento = resultado_acoes if isento and resultado_acoes > 0 else ZERO
    resultado_comum = resultado_acoes - lucro_isento + resultado_outros

    day_trade = _compensar(resultado_dt, saldos.prejuizo_dt, regra_dt.aliquota)
    comum = _compensar(resultado_comum, saldos.prejuizo_comum, regra_comum.aliquota)
    imposto_devido = day_trade.imposto + comum.imposto

    irrf_dt = _abater_irrf(imposto_devido, saldos.irrf_dt, _irrf_day_trade(eventos_dt, regra_dt.aliquota_irrf))
    irrf_comum = _abater_irrf(
        imposto_devido - irrf_dt.compensado, saldos.irrf_comum, _irrf_comum(vendas, regra_comum.aliquota_irrf)
    )
    imposto_a_pagar = imposto_devido - irrf_dt.compensado - irrf_comum.compensado

    total = imposto_a_pagar + saldos.imposto_pendente
    if total >= DARF_MINIMO:
        darf = Darf(competencia(ano, mes), DARF_CODIGO, total, vencimento_darf(ano, mes))
        pendente = ZERO
    else:
        darf, pendente = None, total

    apuracao = ApuracaoMensal(
        ano=ano,
        mes=mes,
        day_trade=day_trade,
        comum=comum,
        isencao=Isencao(total_vendas_acoes, limite, isento, lucro_isento),
        imposto_devido=imposto_devido,
        irrf_day_trade=irrf_dt,
        irrf_comum=irrf_comum,
        imposto_a_pagar=imposto_a_pagar,
        imposto_pendente_anterior=saldos.imposto_pendente,
        imposto_pendente=pendente,
        darf=darf,
        eventos_day_trade=tuple(eventos_dt),
        vendas_comuns=tuple(vendas),
    )
    saldos.prejuizo_dt = day_trade.prejuizo_a_compensar
    saldos.prejuizo_comum = comum.prejuizo_a_compensar
    saldos.irrf_dt = irrf_dt.a_compensar
    saldos.irrf_comum = irrf_comum.a_compensar
    saldos.imposto_pendente = pendente
    return apuracao


def apurar(
    notas: Iterable[Nota],
    regras: Sequence[Regra],
    saldo_inicial: SaldoInicial | None = None,
    ate: date | None = None,
) -> ResultadoApuracao:
    """Apura mês a mês, do início do histórico até `ate` (ou até o último negócio)."""
    notas = list(notas)
    if saldo_inicial and any(n.data <= saldo_inicial.data_referencia for n in notas):
        raise OperacaoAntesDoSaldoInicial(saldo_inicial.data_referencia)
    if ate is not None:
        notas = [n for n in notas if n.data <= ate]
        if saldo_inicial and ate < saldo_inicial.data_referencia:
            saldo_inicial = None

    eventos_dt, eventos_comuns = classificar(notas)
    carteira = Carteira(saldo_inicial.posicoes if saldo_inicial else ())
    meses_com_eventos = {(e.data.year, e.data.month) for e in [*eventos_dt, *eventos_comuns]}

    if saldo_inicial:
        inicio = mes_seguinte(saldo_inicial.data_referencia.year, saldo_inicial.data_referencia.month)
    else:
        inicio = min(meses_com_eventos, default=None)
    if ate is not None:
        fim = (ate.year, ate.month)
    else:
        fim = max(meses_com_eventos, default=inicio)
    if inicio is None or inicio > fim:
        return ResultadoApuracao((), carteira.posicoes())

    dt_por_mes: dict[tuple[int, int], list[EventoDayTrade]] = defaultdict(list)
    comuns_por_mes: dict[tuple[int, int], list[EventoComum]] = defaultdict(list)
    for evento in eventos_dt:
        dt_por_mes[(evento.data.year, evento.data.month)].append(evento)
    for evento in eventos_comuns:
        comuns_por_mes[(evento.data.year, evento.data.month)].append(evento)

    saldos = _Saldos()
    if saldo_inicial:
        saldos.prejuizo_dt = saldo_inicial.prejuizo_day_trade
        saldos.prejuizo_comum = saldo_inicial.prejuizo_comum
        saldos.imposto_pendente = saldo_inicial.imposto_pendente

    meses: list[ApuracaoMensal] = []
    for ano, mes in meses_entre(inicio, fim):
        if mes == 1 and meses:
            # sobra de IRRF não passa de um ano para o outro: vai para a declaração anual
            saldos.irrf_dt = saldos.irrf_comum = ZERO
        meses.append(
            _apurar_mes(ano, mes, dt_por_mes[(ano, mes)], comuns_por_mes[(ano, mes)], carteira, regras, saldos)
        )
    return ResultadoApuracao(tuple(meses), carteira.posicoes())


def apuracao_vazia(ano: int, mes: int, regras: Sequence[Regra]) -> ApuracaoMensal:
    primeiro_dia = date(ano, mes, 1)
    regra_dt = regra_vigente(regras, Modalidade.DAY_TRADE, primeiro_dia)
    regra_comum = regra_vigente(regras, Modalidade.COMUM, primeiro_dia)
    irrf = SaldoIRRF(ZERO, ZERO, ZERO, ZERO)
    return ApuracaoMensal(
        ano=ano,
        mes=mes,
        day_trade=_compensar(ZERO, ZERO, regra_dt.aliquota),
        comum=_compensar(ZERO, ZERO, regra_comum.aliquota),
        isencao=Isencao(ZERO, regra_comum.limite_isencao_acoes, regra_comum.limite_isencao_acoes is not None, ZERO),
        imposto_devido=ZERO,
        irrf_day_trade=irrf,
        irrf_comum=irrf,
        imposto_a_pagar=ZERO,
        imposto_pendente_anterior=ZERO,
        imposto_pendente=ZERO,
        darf=None,
    )
