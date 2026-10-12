from decimal import Decimal

import pytest

from app.domain.carteira import Carteira
from app.domain.classificador import classificar
from app.domain.custos import ratear_custos
from app.domain.erros import PosicaoInsuficiente
from app.domain.modelos import Lado, TipoAtivo
from app.domain.tickers import normalizar_ticker, tipo_por_ticker
from tests.fabricas import compra, nota, venda


def test_rateio_proporcional_ao_valor():
    n = nota("2026-03-02", compra("ABEV3", 100, "10.00"), venda("ABEV3", 100, "11.00"), custos="10.50")
    assert [custo for _, custo in ratear_custos(n)] == [Decimal("5"), Decimal("5.5")]


def test_compra_300_venda_200_no_mesmo_dia():
    eventos_dt, comuns = classificar(
        [nota("2026-05-11", compra("PETR4", 300, "38.00"), venda("PETR4", 200, "38.50"))]
    )
    (evento,) = eventos_dt
    assert (evento.quantidade, evento.resultado) == (200, Decimal("100"))
    assert [(c.lado, c.quantidade, c.valor_liquido) for c in comuns] == [(Lado.COMPRA, 100, Decimal("3800"))]


def test_corretoras_diferentes_nao_e_day_trade():
    eventos_dt, comuns = classificar([
        nota("2026-03-02", compra("PETR4", 100, "30.00"), corretora="X"),
        nota("2026-03-02", venda("PETR4", 100, "31.00"), corretora="Y"),
    ])
    assert eventos_dt == []
    assert [(c.corretora, c.lado) for c in comuns] == [("X", Lado.COMPRA), ("Y", Lado.VENDA)]


def test_notas_do_mesmo_dia_e_corretora_sao_somadas():
    eventos_dt, comuns = classificar([
        nota("2026-03-02", compra("PETR4", 100, "30.00")),
        nota("2026-03-02", venda("PETR4", 100, "31.00")),
    ])
    assert eventos_dt[0].quantidade == 100
    assert comuns == []


def test_carteira_preco_medio_com_custos_e_venda_parcial():
    _, comuns = classificar([
        nota("2026-03-02", compra("ITSA4", 100, "10.00"), custos="2.00"),
        nota("2026-03-03", compra("ITSA4", 100, "12.00")),
        nota("2026-03-04", venda("ITSA4", 50, "13.00")),
    ])
    carteira = Carteira()
    carteira.comprar(comuns[0])
    carteira.comprar(comuns[1])
    vendida = carteira.vender(comuns[2])
    assert vendida.preco_medio == Decimal("11.01")
    assert vendida.resultado == Decimal("99.50")
    (posicao,) = carteira.posicoes()
    assert (posicao.quantidade, posicao.custo_total) == (150, Decimal("1651.50"))


def test_venda_sem_posicao():
    _, comuns = classificar([nota("2026-03-04", venda("ITSA4", 50, "13.00"))])
    with pytest.raises(PosicaoInsuficiente):
        Carteira().vender(comuns[0])


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [("petr4", "PETR4"), (" PETR4F ", "PETR4"), ("BOVA11", "BOVA11"), ("B3SA3", "B3SA3"), ("taee11f", "TAEE11")],
)
def test_normalizar_ticker(entrada, esperado):
    assert normalizar_ticker(entrada) == esperado


@pytest.mark.parametrize("invalido", ["PETR", "PETR123", "PE TR4", ""])
def test_ticker_invalido(invalido):
    with pytest.raises(ValueError):
        normalizar_ticker(invalido)


def test_tipo_por_ticker():
    assert tipo_por_ticker("PETR4") is TipoAtivo.ACAO
    assert tipo_por_ticker("BOVA11") is None
