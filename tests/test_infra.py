from datetime import date
from decimal import Decimal

import httpx
import pytest
from sqlalchemy import create_engine, inspect, text

from app.core import tempo
from app.integrations.bcb import ClienteSelic, SelicIndisponivel


def test_migracoes_criam_tabelas_e_regras(banco_migrado):
    engine = create_engine(f"sqlite:///{banco_migrado.as_posix()}")
    tabelas = set(inspect(engine).get_table_names())
    assert {"usuarios", "corretoras", "ativos", "notas", "operacoes", "pagamentos_darf", "regras_fiscais"} <= tabelas
    with engine.connect() as conexao:
        assert conexao.execute(text("SELECT COUNT(*) FROM regras_fiscais")).scalar() == 2
    engine.dispose()


def _cliente(responder) -> ClienteSelic:
    return ClienteSelic(http=httpx.Client(transport=httpx.MockTransport(responder)))


def test_cliente_selic_usa_meses_fechados_e_cache(monkeypatch):
    monkeypatch.setattr(tempo, "hoje", lambda: date(2026, 10, 12))
    chamadas = []

    def responder(requisicao: httpx.Request) -> httpx.Response:
        chamadas.append(dict(requisicao.url.params))
        return httpx.Response(200, json=[
            {"data": "01/03/2026", "valor": "1.10"},
            {"data": "01/04/2026", "valor": "1.05"},
            {"data": "01/10/2026", "valor": "0.36"},
        ])

    cliente = _cliente(responder)
    assert cliente.selic_mensal([(2026, 3), (2026, 4)]) == {(2026, 3): Decimal("1.10"), (2026, 4): Decimal("1.05")}
    assert cliente.selic_mensal([(2026, 4)]) == {(2026, 4): Decimal("1.05")}
    assert chamadas == [{"formato": "json", "dataInicial": "01/03/2026", "dataFinal": "30/04/2026"}]


def test_cliente_selic_rejeita_mes_corrente(monkeypatch):
    monkeypatch.setattr(tempo, "hoje", lambda: date(2026, 10, 12))
    with pytest.raises(SelicIndisponivel):
        _cliente(lambda _: httpx.Response(200, json=[])).selic_mensal([(2026, 10)])


@pytest.mark.parametrize("resposta", [httpx.Response(500), httpx.Response(200, text="<html>"), httpx.Response(200, json=[])])
def test_cliente_selic_falhas_viram_indisponivel(monkeypatch, resposta):
    monkeypatch.setattr(tempo, "hoje", lambda: date(2026, 10, 12))
    with pytest.raises(SelicIndisponivel):
        _cliente(lambda _: resposta).selic_mensal([(2026, 4)])
