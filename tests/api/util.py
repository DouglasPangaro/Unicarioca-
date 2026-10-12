from fastapi.testclient import TestClient


def op(ticker: str, lado: str, quantidade: int, preco: str) -> dict:
    return {"ticker": ticker, "lado": lado, "quantidade": quantidade, "preco": preco}


def criar_corretora(client: TestClient, auth: dict, nome: str = "XP") -> int:
    resposta = client.post("/corretoras", json={"nome": nome}, headers=auth)
    assert resposta.status_code == 201, resposta.text
    return resposta.json()["id"]


def criar_nota(client: TestClient, auth: dict, corretora_id: int, data: str, *operacoes: dict, **custos):
    corpo = {"corretora_id": corretora_id, "data_pregao": data, "operacoes": list(operacoes), **custos}
    return client.post("/notas", json=corpo, headers=auth)


def cenario_a(client: TestClient, auth: dict) -> tuple[int, int]:
    """Jan: day trade com prejuízo de 100; fev: lucro de 400. Retorna (corretora_id, nota de janeiro)."""
    corretora = criar_corretora(client, auth)
    janeiro = criar_nota(client, auth, corretora, "2026-01-12", op("PETR4", "C", 100, "30.00"), op("PETR4", "V", 100, "29.00"))
    assert janeiro.status_code == 201, janeiro.text
    fevereiro = criar_nota(client, auth, corretora, "2026-02-10", op("VALE3", "C", 100, "60.00"), op("VALE3", "V", 100, "64.00"))
    assert fevereiro.status_code == 201, fevereiro.text
    return corretora, janeiro.json()["id"]
