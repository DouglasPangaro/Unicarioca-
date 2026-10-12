from tests.api.util import criar_corretora, criar_nota, op


def test_criar_nota_cadastra_ativo_e_soma_custos(client, auth):
    corretora_id = criar_corretora(client, auth)
    resposta = criar_nota(
        client, auth, corretora_id, "2026-03-02",
        op("abev3", "C", 100, "10.00"), op("ABEV3", "V", 100, "11.00"),
        corretagem="4.90", emolumentos="0.60", iss="5.00",
    )
    assert resposta.status_code == 201, resposta.text
    nota = resposta.json()
    assert nota["custos_totais"] == "10.50"
    assert nota["corretora_nome"] == "XP"
    assert [(o["ticker"], o["lado"], o["preco"]) for o in nota["operacoes"]] == [("ABEV3", "C", "10.00"), ("ABEV3", "V", "11.00")]
    assert client.get("/ativos", headers=auth).json()[0]["tipo"] == "ACAO"


def test_listar_com_filtros(client, auth):
    xp = criar_corretora(client, auth, "XP")
    rico = criar_corretora(client, auth, "Rico")
    criar_nota(client, auth, xp, "2026-03-02", op("PETR4", "C", 100, "30.00"))
    criar_nota(client, auth, rico, "2026-04-01", op("PETR4", "C", 100, "30.00"))

    assert len(client.get("/notas", headers=auth).json()) == 2
    assert [n["data_pregao"] for n in client.get("/notas", params={"inicio": "2026-04-01"}, headers=auth).json()] == ["2026-04-01"]
    assert [n["corretora_nome"] for n in client.get("/notas", params={"corretora_id": xp}, headers=auth).json()] == ["XP"]
    assert len(client.get("/notas", params={"limit": 1}, headers=auth).json()) == 1


def test_venda_sem_posicao_retorna_422(client, auth):
    corretora_id = criar_corretora(client, auth)
    resposta = criar_nota(client, auth, corretora_id, "2026-03-02", op("PETR4", "V", 100, "30.00"))
    assert resposta.status_code == 422
    assert "sem posição suficiente" in resposta.json()["detail"]
    assert client.get("/notas", headers=auth).json() == []


def test_ticker_final_11_exige_cadastro_do_tipo(client, auth):
    corretora_id = criar_corretora(client, auth)
    assert criar_nota(client, auth, corretora_id, "2026-03-02", op("BOVA11", "C", 10, "100.00")).status_code == 422
    client.post("/ativos", json={"ticker": "BOVA11", "tipo": "ETF"}, headers=auth)
    assert criar_nota(client, auth, corretora_id, "2026-03-02", op("BOVA11", "C", 10, "100.00")).status_code == 201


def test_validacoes_de_entrada(client, auth):
    corretora_id = criar_corretora(client, auth)
    compra = op("PETR4", "C", 100, "30.00")
    assert criar_nota(client, auth, corretora_id, "2099-01-05", compra).status_code == 422
    assert criar_nota(client, auth, corretora_id, "2026-03-07", compra).status_code == 422  # sábado
    assert criar_nota(client, auth, corretora_id, "2026-03-02").status_code == 422
    assert criar_nota(client, auth, corretora_id, "2026-03-02", op("PETR4", "C", 0, "30.00")).status_code == 422
    assert criar_nota(client, auth, corretora_id, "2026-03-02", op("PETR4", "C", 1, "30.001")).status_code == 422
    assert criar_nota(client, auth, corretora_id, "2026-03-02", compra, corretagem="-1").status_code == 422


def test_crud_de_operacoes(client, auth):
    corretora_id = criar_corretora(client, auth)
    nota = criar_nota(client, auth, corretora_id, "2026-03-02", op("PETR4", "C", 100, "30.00")).json()

    nova = client.post(f"/notas/{nota['id']}/operacoes", json=op("PETR4", "V", 50, "31.00"), headers=auth)
    assert nova.status_code == 201
    operacao_id = nova.json()["id"]

    alterada = client.put(f"/notas/{nota['id']}/operacoes/{operacao_id}", json=op("PETR4", "V", 100, "31.00"), headers=auth)
    assert alterada.json()["quantidade"] == 100

    assert client.delete(f"/notas/{nota['id']}/operacoes/{operacao_id}", headers=auth).status_code == 204
    primeira = nota["operacoes"][0]["id"]
    assert client.delete(f"/notas/{nota['id']}/operacoes/{primeira}", headers=auth).status_code == 422
    assert client.delete(f"/notas/{nota['id']}/operacoes/999", headers=auth).status_code == 404


def test_atualizar_cabecalho_e_custos(client, auth):
    corretora_id = criar_corretora(client, auth)
    nota = criar_nota(client, auth, corretora_id, "2026-03-02", op("PETR4", "C", 100, "30.00")).json()
    corpo = {"corretora_id": corretora_id, "data_pregao": "2026-03-03", "numero": "123", "corretagem": "2.50"}
    resposta = client.put(f"/notas/{nota['id']}", json=corpo, headers=auth)
    assert resposta.status_code == 200
    assert (resposta.json()["data_pregao"], resposta.json()["custos_totais"]) == ("2026-03-03", "2.50")


def test_excluir_nota(client, auth):
    corretora_id = criar_corretora(client, auth)
    nota_id = criar_nota(client, auth, corretora_id, "2026-03-02", op("PETR4", "C", 100, "30.00")).json()["id"]
    assert client.delete(f"/notas/{nota_id}", headers=auth).status_code == 204
    assert client.get(f"/notas/{nota_id}", headers=auth).status_code == 404


def test_excluir_compra_que_sustenta_venda_e_bloqueado(client, auth):
    corretora_id = criar_corretora(client, auth)
    compra = criar_nota(client, auth, corretora_id, "2026-03-02", op("PETR4", "C", 100, "30.00")).json()
    criar_nota(client, auth, corretora_id, "2026-03-03", op("PETR4", "V", 100, "31.00"))
    assert client.delete(f"/notas/{compra['id']}", headers=auth).status_code == 422
    assert client.get(f"/notas/{compra['id']}", headers=auth).status_code == 200
