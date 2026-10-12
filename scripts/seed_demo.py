"""Cria o usuário de demonstração com os cenários de referência no banco configurado.

Uso (depois de `alembic upgrade head`): python -m scripts.seed_demo
"""
from fastapi.testclient import TestClient

from app.main import app

EMAIL = "demo@exemplo.com"
SENHA = "demo-senha-123"


def _op(ticker: str, lado: str, quantidade: int, preco: str) -> dict:
    return {"ticker": ticker, "lado": lado, "quantidade": quantidade, "preco": preco}


def main() -> None:
    # a própria API é usada em processo, para que os dados passem pelas mesmas validações
    with TestClient(app) as api:
        if api.post("/auth/registrar", json={"email": EMAIL, "senha": SENHA}).status_code == 409:
            print(f"O usuário {EMAIL} já existe; nada foi alterado.")
            return
        token = api.post("/auth/token", data={"username": EMAIL, "password": SENHA}).json()["access_token"]
        cabecalho = {"Authorization": f"Bearer {token}"}

        def enviar(metodo: str, url: str, corpo: dict) -> dict:
            resposta = api.request(metodo, url, json=corpo, headers=cabecalho)
            resposta.raise_for_status()
            return resposta.json()

        enviar("PUT", "/saldo-inicial", {
            "data_referencia": "2025-12-31",
            "posicoes": [
                {"ticker": "ITSA4", "quantidade": 1000, "custo_total": "10000.00"},
                {"ticker": "BBAS3", "quantidade": 500, "custo_total": "10000.00"},
            ],
        })
        xp = enviar("POST", "/corretoras", {"nome": "XP"})["id"]
        rico = enviar("POST", "/corretoras", {"nome": "Rico"})["id"]

        notas = [
            (xp, "2026-01-12", [_op("PETR4", "C", 100, "30.00"), _op("PETR4", "V", 100, "29.00")]),
            (xp, "2026-02-10", [_op("VALE3", "C", 100, "60.00"), _op("VALE3", "V", 100, "64.00")]),
            (xp, "2026-03-05", [_op("ABEV3", "C", 10, "10.00"), _op("ABEV3", "V", 10, "13.00")]),
            (xp, "2026-04-07", [_op("ABEV3", "C", 10, "10.00"), _op("ABEV3", "V", 10, "13.00")]),
            (xp, "2026-05-11", [_op("PETR4", "C", 300, "38.00"), _op("PETR4", "V", 200, "38.50")]),
            (xp, "2026-05-20", [_op("PETR4", "V", 100, "40.00")]),
            (xp, "2026-06-10", [_op("ITSA4", "V", 1000, "11.00"), _op("BBAS3", "V", 500, "22.00")]),
            (rico, "2026-07-01", [_op("PETR4", "C", 100, "30.00")]),
            (xp, "2026-07-01", [_op("PETR4", "V", 100, "31.00")]),
        ]
        for corretora_id, data, operacoes in notas:
            enviar("POST", "/notas", {"corretora_id": corretora_id, "data_pregao": data, "operacoes": operacoes})
        enviar("POST", "/darfs/2026-02/pagamento", {"data_pagamento": "2026-03-20"})

        print(f"Usuário criado: {EMAIL} / senha: {SENHA}")
        for darf in api.get("/darfs", headers=cabecalho).json():
            print(f"DARF {darf['competencia']}: R$ {darf['valor']} vence {darf['vencimento']} ({darf['status']})")


if __name__ == "__main__":
    main()
