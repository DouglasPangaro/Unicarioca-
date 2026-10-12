from datetime import date
from decimal import Decimal

from app.domain.apuracao import apurar
from app.domain.consistencia import verificar_pagamentos
from app.domain.irpf import montar_relatorio
from app.domain.simulacao import simular_venda
from tests.fabricas import REGRAS, compra, nota, saldo, venda


def _cenario_a(preco_venda_janeiro: str):
    return [
        nota("2026-01-12", compra("PETR4", 100, "30.00"), venda("PETR4", 100, preco_venda_janeiro)),
        nota("2026-02-10", compra("VALE3", 100, "60.00"), venda("VALE3", 100, "64.00")),
    ]


def test_cenario_g_alteracao_muda_darf_ja_pago():
    meses = apurar(_cenario_a("28.00"), REGRAS).meses
    (divergencia,) = verificar_pagamentos(meses, {"2026-02": Decimal("56.00")})
    assert (divergencia.valor_recalculado, divergencia.diferenca) == (Decimal("36.00"), Decimal("-20.00"))


def test_sem_divergencia_quando_darf_pago_se_mantem():
    assert verificar_pagamentos(apurar(_cenario_a("29.00"), REGRAS).meses, {"2026-02": Decimal("56.00")}) == []


def test_simulador_avisa_perda_de_isencao():
    inicial = saldo("2026-05-31", ("ITSA4", 1000, "10000"), ("BBAS3", 500, "10000"))
    notas = [nota("2026-06-10", venda("ITSA4", 1000, "11.00"))]
    resultado = simular_venda(notas, REGRAS, inicial, nota("2026-06-15", venda("BBAS3", 500, "22.00")))
    assert resultado.modalidade == "COMUM"
    assert resultado.perde_isencao
    assert resultado.resultado_comum == Decimal("1000")
    assert (resultado.darf_antes, resultado.darf_depois, resultado.diferenca_darf) == (
        0, Decimal("298.90"), Decimal("298.90"),
    )


def test_simulador_separa_day_trade_do_excedente():
    inicial = saldo("2026-05-31", ("PETR4", 100, "2800"))
    notas = [nota("2026-06-15", compra("PETR4", 100, "30.00"))]
    resultado = simular_venda(notas, REGRAS, inicial, nota("2026-06-15", venda("PETR4", 150, "31.00")))
    assert (resultado.modalidade, resultado.quantidade_day_trade, resultado.quantidade_comum) == ("MISTA", 100, 50)
    assert (resultado.resultado_day_trade, resultado.resultado_comum) == (Decimal("100"), Decimal("150"))


def test_relatorio_irpf():
    notas = [nota("2026-05-11", compra("PETR4", 300, "38.00"), venda("PETR4", 200, "38.50"))]
    atual = apurar(notas, REGRAS, ate=date(2026, 12, 31))
    anterior = apurar(notas, REGRAS, ate=date(2025, 12, 31))
    relatorio = montar_relatorio(
        2026, atual.meses, REGRAS, anterior.posicoes, atual.posicoes, {"2026-05": Decimal("19.00")}
    )
    assert len(relatorio.renda_variavel) == 12
    assert relatorio.renda_variavel[0].imposto_devido == 0
    maio = relatorio.renda_variavel[4]
    assert (maio.day_trade.imposto, maio.imposto_a_pagar, maio.imposto_pago) == (
        Decimal("20.00"), Decimal("19.00"), Decimal("19.00"),
    )
    (bem,) = relatorio.bens_e_direitos
    assert (bem.ticker, bem.grupo, bem.codigo, bem.quantidade_atual, bem.situacao_atual) == (
        "PETR4", "03", "01", 100, Decimal("3800.00"),
    )
    assert bem.discriminacao == "100 ações PETR4, custo médio de R$ 38,00."
