from datetime import date
from decimal import Decimal

import pytest

from app.domain.apuracao import apuracao_vazia, apurar
from app.domain.erros import OperacaoAntesDoSaldoInicial, PosicaoInsuficiente, RegraNaoEncontrada
from app.domain.modelos import Darf, TipoAtivo
from tests.fabricas import REGRAS, compra, nota, saldo, venda


def test_cenario_a_compensa_prejuizo_e_deduz_irrf():
    jan, fev = apurar([
        nota("2026-01-12", compra("PETR4", 100, "30.00"), venda("PETR4", 100, "29.00")),
        nota("2026-02-10", compra("VALE3", 100, "60.00"), venda("VALE3", 100, "64.00")),
    ], REGRAS).meses
    assert jan.day_trade.resultado_liquido == Decimal("-100")
    assert jan.day_trade.prejuizo_a_compensar == Decimal("100")
    assert jan.darf is None
    assert fev.day_trade.prejuizo_compensado == Decimal("100")
    assert fev.day_trade.base_calculo == Decimal("300")
    assert fev.day_trade.imposto == Decimal("60.00")
    assert fev.irrf_day_trade.compensado == Decimal("4.00")
    assert fev.day_trade.prejuizo_a_compensar == 0
    assert fev.darf == Darf("2026-02", "6015", Decimal("56.00"), date(2026, 3, 31))


def test_cenario_b_darf_abaixo_de_10_acumula():
    mar, abr = apurar([
        nota("2026-03-05", compra("ABEV3", 10, "10.00"), venda("ABEV3", 10, "13.00")),
        nota("2026-04-07", compra("ABEV3", 10, "10.00"), venda("ABEV3", 10, "13.00")),
    ], REGRAS).meses
    assert mar.imposto_a_pagar == Decimal("5.70")
    assert (mar.darf, mar.imposto_pendente) == (None, Decimal("5.70"))
    assert abr.imposto_pendente_anterior == Decimal("5.70")
    assert abr.darf == Darf("2026-04", "6015", Decimal("11.40"), date(2026, 5, 29))
    assert abr.imposto_pendente == 0


def test_cenario_c_day_trade_parcial_e_venda_isenta():
    (mai,) = apurar([
        nota("2026-05-11", compra("PETR4", 300, "38.00"), venda("PETR4", 200, "38.50")),
        nota("2026-05-20", venda("PETR4", 100, "40.00")),
    ], REGRAS).meses
    assert mai.day_trade.resultado_liquido == Decimal("100")
    assert mai.isencao.isento
    assert mai.isencao.lucro_isento == Decimal("200")
    assert mai.comum.resultado_liquido == 0
    assert mai.irrf_comum.do_mes == 0
    assert mai.darf == Darf("2026-05", "6015", Decimal("19.00"), date(2026, 6, 30))


def test_cenario_d_vendas_acima_de_20_mil_perdem_isencao():
    inicial = saldo("2026-05-31", ("ITSA4", 1000, "10000"), ("BBAS3", 500, "10000"))
    (jun,) = apurar(
        [nota("2026-06-10", venda("ITSA4", 1000, "11.00"), venda("BBAS3", 500, "22.00"))], REGRAS, inicial
    ).meses
    assert not jun.isencao.isento
    assert jun.comum.imposto == Decimal("300.00")
    assert jun.irrf_comum.compensado == Decimal("1.10")
    assert jun.darf.valor == Decimal("298.90")


def test_cenario_d_apenas_11_mil_em_vendas_e_isento():
    inicial = saldo("2026-05-31", ("ITSA4", 1000, "10000"))
    (jun,) = apurar([nota("2026-06-10", venda("ITSA4", 1000, "11.00"))], REGRAS, inicial).meses
    assert jun.isencao.isento
    assert jun.isencao.lucro_isento == Decimal("1000")
    assert jun.darf is None


def test_cenario_e_corretoras_diferentes_viram_operacao_comum():
    (mar,) = apurar([
        nota("2026-03-02", compra("PETR4", 100, "30.00"), corretora="X"),
        nota("2026-03-02", venda("PETR4", 100, "31.00"), corretora="Y"),
    ], REGRAS).meses
    assert mar.eventos_day_trade == ()
    assert mar.vendas_comuns[0].resultado == Decimal("100")
    assert mar.isencao.lucro_isento == Decimal("100")


def test_cenario_f_custos_rateados():
    (mar,) = apurar(
        [nota("2026-03-02", compra("ABEV3", 100, "10.00"), venda("ABEV3", 100, "11.00"), custos="10.50")], REGRAS
    ).meses
    assert mar.day_trade.resultado_liquido == Decimal("89.50")
    assert mar.irrf_day_trade.do_mes == Decimal("0.90")


def test_prejuizo_de_day_trade_nao_abate_lucro_comum():
    inicial = saldo("2026-02-28", ("ITSA4", 3000, "30000"))
    (mar,) = apurar([
        nota("2026-03-02", compra("PETR4", 100, "30.00"), venda("PETR4", 100, "25.00")),
        nota("2026-03-03", venda("ITSA4", 3000, "10.50")),
    ], REGRAS, inicial).meses
    assert mar.day_trade.prejuizo_a_compensar == Decimal("500")
    assert mar.comum.imposto == Decimal("225.00")


def test_lucro_isento_nao_consome_prejuizo_e_prejuizo_de_mes_isento_acumula():
    inicial = saldo("2026-02-28", ("ITSA4", 2000, "20000"), prejuizo_comum="300")
    mar, abr = apurar([
        nota("2026-03-02", venda("ITSA4", 1000, "9.00")),
        nota("2026-04-01", venda("ITSA4", 1000, "12.00")),
    ], REGRAS, inicial).meses
    assert mar.comum.prejuizo_a_compensar == Decimal("1300")
    assert abr.isencao.lucro_isento == Decimal("2000")
    assert abr.comum.prejuizo_a_compensar == Decimal("1300")


def test_etf_nao_tem_isencao():
    (mar,) = apurar([
        nota("2026-03-02", compra("BOVA11", 10, "100.00", TipoAtivo.ETF)),
        nota("2026-03-03", venda("BOVA11", 10, "120.00", TipoAtivo.ETF)),
    ], REGRAS).meses
    assert mar.isencao.vendas_acoes == 0
    assert mar.comum.imposto == Decimal("30.00")
    assert mar.darf.valor == Decimal("30.00")


def test_sobra_de_irrf_passa_para_o_mes_seguinte_e_zera_no_ano_novo():
    nov, dez, jan = apurar([
        nota("2026-11-03", compra("PETR4", 100, "30.00"), venda("PETR4", 100, "40.00")),
        nota("2026-11-04", compra("PETR4", 100, "40.00"), venda("PETR4", 100, "30.40")),
        nota("2027-01-05", compra("PETR4", 100, "30.00"), venda("PETR4", 100, "31.00")),
    ], REGRAS).meses
    assert nov.irrf_day_trade.do_mes == Decimal("10.00")
    assert nov.irrf_day_trade.compensado == Decimal("8.00")
    assert nov.irrf_day_trade.a_compensar == Decimal("2.00")
    assert dez.irrf_day_trade.meses_anteriores == Decimal("2.00")
    assert jan.irrf_day_trade.meses_anteriores == 0
    assert jan.darf.valor == Decimal("19.00")


def test_saldo_inicial_traz_prejuizo_e_posicao():
    inicial = saldo("2026-02-28", ("PETR4", 100, "3000"), prejuizo_day_trade="100")
    resultado = apurar(
        [nota("2026-03-02", compra("VALE3", 100, "60.00"), venda("VALE3", 100, "62.00"))], REGRAS, inicial
    )
    (mar,) = resultado.meses
    assert mar.day_trade.prejuizo_compensado == Decimal("100")
    assert mar.darf.valor == Decimal("18.00")
    assert [(p.ticker, p.quantidade) for p in resultado.posicoes] == [("PETR4", 100)]


def test_nota_anterior_ao_saldo_inicial_e_rejeitada():
    with pytest.raises(OperacaoAntesDoSaldoInicial):
        apurar([nota("2026-02-27", compra("PETR4", 1, "10"))], REGRAS, saldo("2026-02-28"))


def test_venda_sem_posicao_e_rejeitada():
    with pytest.raises(PosicaoInsuficiente):
        apurar([nota("2026-03-02", venda("PETR4", 1, "10"))], REGRAS)


def test_ate_limita_o_periodo_e_inclui_meses_sem_negocios():
    resultado = apurar([nota("2026-01-12", compra("PETR4", 100, "30.00"))], REGRAS, ate=date(2026, 3, 31))
    assert [m.competencia for m in resultado.meses] == ["2026-01", "2026-02", "2026-03"]
    assert resultado.posicoes[0].quantidade == 100


def test_apuracao_vazia_usa_aliquotas_vigentes():
    mes = apuracao_vazia(2026, 7, REGRAS)
    assert (mes.day_trade.aliquota, mes.comum.aliquota, mes.darf) == (Decimal("0.20"), Decimal("0.15"), None)


def test_posicao_na_data_do_saldo_inicial_e_a_do_saldo():
    inicial = saldo("2025-12-31", ("PETR4", 100, "3000"))
    resultado = apurar([], REGRAS, inicial, ate=date(2025, 12, 31))
    assert resultado.meses == ()
    assert [(p.ticker, p.quantidade) for p in resultado.posicoes] == [("PETR4", 100)]


def test_periodo_sem_regra_fiscal_e_rejeitado():
    with pytest.raises(RegraNaoEncontrada):
        apurar([nota("2004-06-01", compra("PETR4", 1, "10"))], REGRAS)
