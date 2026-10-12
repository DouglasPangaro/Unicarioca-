from datetime import date, datetime
from decimal import Decimal

import pytest

from app.core.erros import Invalido
from app.importers.b3 import ler_planilha
from tests.api.test_extras import planilha

VALIDA = ["12/01/2026", "Compra", "Mercado à Vista", "-", "XP", "PETR4", 100, 30.0, 3000.0]


def test_parser_aceita_formatos_variados_e_explica_linhas_ignoradas():
    conteudo = planilha(
        [datetime(2026, 1, 12), "COMPRA", "MERCADO A VISTA", "-", "  XP   INVESTIMENTOS ", "petr4", "100", "R$ 1.234,56", None],
        ["12/01/2026", "Transferência", "Mercado à Vista", "-", "XP", "PETR4", 1, 1.0, 1.0],
        ["12/01/2026", "Venda", "Mercado à Vista", "-", "XP", "PETR4", 1.5, 1.0, 1.0],
        ["12/01/2026", "Venda", "Mercado à Vista", "-", "XP", "PETR4", 1, 0, 0],
        ["12/01/2026", "Venda", "Mercado à Vista", "-", "", "PETR4", 1, 1.0, 1.0],
        ["31/02/2026", "Venda", "Mercado à Vista", "-", "XP", "PETR4", 1, 1.0, 1.0],
        ["", "", "", "", "", "", "", "", ""],
    )
    leitura = ler_planilha(conteudo, max_linhas=100)
    (linha,) = leitura.linhas
    assert (linha.data, linha.instituicao, linha.ticker, linha.quantidade, linha.preco) == (
        date(2026, 1, 12), "XP INVESTIMENTOS", "PETR4", 100, Decimal("1234.56"),
    )
    assert [numero for numero, _ in leitura.ignoradas] == [3, 4, 5, 6, 7]


def test_parser_respeita_limite_de_linhas():
    with pytest.raises(Invalido):
        ler_planilha(planilha(VALIDA, VALIDA, VALIDA), max_linhas=2)
