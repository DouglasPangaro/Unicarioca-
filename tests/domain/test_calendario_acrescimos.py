from datetime import date
from decimal import Decimal

import pytest

from app.domain.acrescimos import calcular_acrescimos, meses_selic
from app.domain.calendario import ultimo_dia_util, vencimento_darf


@pytest.mark.parametrize(
    ("ano", "mes", "esperado"),
    [
        (2017, 2, date(2017, 2, 24)),  # Carnaval em 27 e 28/02
        (2024, 3, date(2024, 3, 28)),  # Sexta-feira Santa em 29/03
        (2026, 12, date(2026, 12, 30)),  # 31/12 sem expediente
        (2026, 5, date(2026, 5, 29)),  # 30 e 31/05 são fim de semana
    ],
)
def test_ultimo_dia_util(ano, mes, esperado):
    assert ultimo_dia_util(ano, mes) == esperado


def test_vencimento_de_dezembro_cai_em_janeiro():
    assert vencimento_darf(2026, 12) == date(2027, 1, 29)


def test_cenario_h_multa_e_juros():
    acrescimos = calcular_acrescimos(
        Decimal("56.00"), date(2026, 3, 31), date(2026, 5, 15), {(2026, 4): Decimal("1.00")}
    )
    assert acrescimos.dias_atraso == 45
    assert acrescimos.multa_percentual == Decimal("14.85")
    assert (acrescimos.multa, acrescimos.juros, acrescimos.total) == (
        Decimal("8.32"), Decimal("1.12"), Decimal("65.44"),
    )


def test_pagamento_em_dia_nao_tem_acrescimos():
    acrescimos = calcular_acrescimos(Decimal("56.00"), date(2026, 3, 31), date(2026, 3, 31), {})
    assert (acrescimos.dias_atraso, acrescimos.total) == (0, Decimal("56.00"))


def test_pagamento_no_mes_seguinte_ao_vencimento_tem_juros_de_1_porcento():
    acrescimos = calcular_acrescimos(Decimal("100"), date(2026, 3, 31), date(2026, 4, 10), {})
    assert (acrescimos.multa, acrescimos.juros) == (Decimal("3.30"), Decimal("1.00"))


def test_multa_limitada_a_20_porcento():
    selic = {(2026, m): Decimal("1") for m in range(2, 6)}
    acrescimos = calcular_acrescimos(Decimal("100"), date(2026, 1, 30), date(2026, 6, 1), selic)
    assert (acrescimos.multa, acrescimos.juros) == (Decimal("20.00"), Decimal("5.00"))


def test_meses_selic():
    assert meses_selic(date(2026, 3, 31), date(2026, 6, 5)) == [(2026, 4), (2026, 5)]
