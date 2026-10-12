from decimal import Decimal

from app.integrations.bcb import SelicIndisponivel
from tests.api.util import cenario_a, criar_corretora, criar_nota, op


def test_cenario_a_ponta_a_ponta(client, auth):
    cenario_a(client, auth)
    fevereiro = client.get("/apuracoes/2026/2", headers=auth).json()
    assert fevereiro["day_trade"]["prejuizo_compensado"] == "100.00"
    assert fevereiro["day_trade"]["imposto"] == "60.00"
    assert fevereiro["day_trade"]["aliquota"] == "0.2"
    assert fevereiro["irrf_day_trade"]["compensado"] == "4.00"
    assert fevereiro["darf"] == {"competencia": "2026-02", "codigo": "6015", "valor": "56.00", "vencimento": "2026-03-31"}
    (evento,) = fevereiro["eventos_day_trade"]
    assert (evento["ticker"], evento["preco_medio_compra"], evento["resultado"]) == ("VALE3", "60.0000", "400.00")


def test_mes_sem_operacoes_retorna_apuracao_zerada(client, auth):
    mes = client.get("/apuracoes/2026/1", headers=auth).json()
    assert (mes["imposto_devido"], mes["darf"], mes["comum"]["aliquota"]) == ("0.00", None, "0.15")


def test_resumo_anual_e_lista_de_darfs(client, auth):
    cenario_a(client, auth)
    anual = client.get("/apuracoes/2026", headers=auth).json()
    assert len(anual["meses"]) == 12
    assert (anual["total_darfs"], anual["total_imposto_devido"]) == ("56.00", "60.00")

    (darf,) = client.get("/darfs", headers=auth).json()
    assert (darf["competencia"], darf["valor"], darf["status"]) == ("2026-02", "56.00", "VENCIDO")
    assert client.get("/darfs", params={"status": "PAGO"}, headers=auth).json() == []


def test_cenario_g_pagamento_trava_alteracao_que_muda_o_darf(client, auth):
    _, nota_janeiro = cenario_a(client, auth)
    pago = client.post("/darfs/2026-02/pagamento", json={"data_pagamento": "2026-03-20"}, headers=auth)
    assert pago.status_code == 201
    assert (pago.json()["valor_total"], pago.json()["multa"]) == ("56.00", "0.00")
    assert client.get("/darfs", params={"status": "PAGO"}, headers=auth).json()[0]["pagamento"]["valor_principal"] == "56.00"

    venda_id = client.get(f"/notas/{nota_janeiro}", headers=auth).json()["operacoes"][1]["id"]
    alteracao = op("PETR4", "V", 100, "28.00")
    conflito = client.put(f"/notas/{nota_janeiro}/operacoes/{venda_id}", json=alteracao, headers=auth)
    assert conflito.status_code == 409
    assert conflito.json()["divergencias"] == [
        {"competencia": "2026-02", "valor_pago": "56.00", "valor_recalculado": "36.00", "diferenca": "-20.00"}
    ]
    assert client.get(f"/notas/{nota_janeiro}", headers=auth).json()["operacoes"][1]["preco"] == "29.00"

    assert client.delete("/darfs/2026-02/pagamento", headers=auth).status_code == 204
    assert client.put(f"/notas/{nota_janeiro}/operacoes/{venda_id}", json=alteracao, headers=auth).status_code == 200
    assert client.get("/apuracoes/2026/2", headers=auth).json()["darf"]["valor"] == "36.00"


def test_cenario_h_pagamento_atrasado_com_selic(client, auth, selic):
    cenario_a(client, auth)
    selic.valores = {(2026, 4): Decimal("1.00")}
    atualizado = client.get("/darfs/2026-02/atualizado", params={"data_pagamento": "2026-05-15"}, headers=auth).json()
    assert (atualizado["dias_atraso"], atualizado["multa_percentual"]) == (45, "14.85")
    assert (atualizado["multa"], atualizado["juros"], atualizado["valor_total"]) == ("8.32", "1.12", "65.44")

    pago = client.post("/darfs/2026-02/pagamento", json={"data_pagamento": "2026-05-15"}, headers=auth)
    assert pago.json()["valor_total"] == "65.44"
    assert client.post("/darfs/2026-02/pagamento", json={"data_pagamento": "2026-05-15"}, headers=auth).status_code == 409


def test_selic_indisponivel_retorna_503(client, auth, selic):
    cenario_a(client, auth)
    selic.erro = SelicIndisponivel("Banco Central fora do ar.")
    resposta = client.get("/darfs/2026-02/atualizado", params={"data_pagamento": "2026-05-15"}, headers=auth)
    assert resposta.status_code == 503


def test_pagamento_invalido(client, auth):
    cenario_a(client, auth)
    assert client.post("/darfs/2026-01/pagamento", json={"data_pagamento": "2026-02-10"}, headers=auth).status_code == 422
    assert client.post("/darfs/2026-02/pagamento", json={"data_pagamento": "2026-02-27"}, headers=auth).status_code == 422
    assert client.get("/darfs/2026-02/atualizado", params={"data_pagamento": "2099-01-01"}, headers=auth).status_code == 422
    assert client.delete("/darfs/2026-02/pagamento", headers=auth).status_code == 404
    assert client.get("/darfs/2026-13/atualizado", headers=auth).status_code == 422


def test_carteira(client, auth):
    corretora_id = criar_corretora(client, auth)
    criar_nota(client, auth, corretora_id, "2026-05-11", op("PETR4", "C", 300, "38.00"), op("PETR4", "V", 200, "38.50"))
    (posicao,) = client.get("/carteira", headers=auth).json()
    assert (posicao["ticker"], posicao["quantidade"], posicao["preco_medio"], posicao["custo_total"]) == (
        "PETR4", 100, "38.0000", "3800.00",
    )
    assert client.get("/carteira", params={"data": "2026-05-08"}, headers=auth).json() == []
