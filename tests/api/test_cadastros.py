from tests.api.util import criar_corretora, criar_nota, op
from tests.conftest import registrar


def test_crud_corretora(client, auth):
    corretora_id = criar_corretora(client, auth, "XP")
    assert [c["nome"] for c in client.get("/corretoras", headers=auth).json()] == ["XP"]

    resposta = client.put(f"/corretoras/{corretora_id}", json={"nome": "XP Investimentos"}, headers=auth)
    assert resposta.json()["nome"] == "XP Investimentos"
    assert client.get(f"/corretoras/{corretora_id}", headers=auth).json()["nome"] == "XP Investimentos"

    assert client.delete(f"/corretoras/{corretora_id}", headers=auth).status_code == 204
    assert client.get(f"/corretoras/{corretora_id}", headers=auth).status_code == 404


def test_corretora_duplicada(client, auth):
    criar_corretora(client, auth, "XP")
    assert client.post("/corretoras", json={"nome": "XP"}, headers=auth).status_code == 409


def test_crud_ativo_com_ticker_normalizado(client, auth):
    resposta = client.post("/ativos", json={"ticker": "bova11f", "tipo": "ETF"}, headers=auth)
    assert resposta.status_code == 201
    ativo = resposta.json()
    assert (ativo["ticker"], ativo["tipo"]) == ("BOVA11", "ETF")

    atualizado = client.put(f"/ativos/{ativo['id']}", json={"ticker": "BOVA11", "tipo": "ETF", "nome": "iShares Ibovespa"}, headers=auth)
    assert atualizado.json()["nome"] == "iShares Ibovespa"
    assert client.delete(f"/ativos/{ativo['id']}", headers=auth).status_code == 204


def test_ticker_invalido(client, auth):
    assert client.post("/ativos", json={"ticker": "PETROBRAS"}, headers=auth).status_code == 422


def test_nao_exclui_cadastros_em_uso(client, auth):
    corretora_id = criar_corretora(client, auth)
    criar_nota(client, auth, corretora_id, "2026-03-02", op("PETR4", "C", 100, "30.00"))
    ativo_id = client.get("/ativos", headers=auth).json()[0]["id"]
    assert client.delete(f"/corretoras/{corretora_id}", headers=auth).status_code == 409
    assert client.delete(f"/ativos/{ativo_id}", headers=auth).status_code == 409


def test_isolamento_entre_usuarios(client, auth):
    corretora_id = criar_corretora(client, auth)
    nota_id = criar_nota(client, auth, corretora_id, "2026-03-02", op("PETR4", "C", 100, "30.00")).json()["id"]
    outro = registrar(client, "bia@exemplo.com")

    assert client.get(f"/corretoras/{corretora_id}", headers=outro).status_code == 404
    assert client.get(f"/notas/{nota_id}", headers=outro).status_code == 404
    assert client.delete(f"/notas/{nota_id}", headers=outro).status_code == 404
    assert client.get("/notas", headers=outro).json() == []
    assert criar_nota(client, outro, corretora_id, "2026-03-02", op("PETR4", "C", 1, "30.00")).status_code == 422
