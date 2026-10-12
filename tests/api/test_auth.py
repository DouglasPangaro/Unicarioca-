from datetime import UTC, datetime, timedelta

import jwt

from app.core.config import get_settings


def test_registro_login_e_me(client):
    resposta = client.post("/auth/registrar", json={"email": "Ana@Exemplo.com", "senha": "senha-segura-123"})
    assert resposta.status_code == 201
    assert resposta.json()["email"] == "ana@exemplo.com"
    assert "senha" not in resposta.text

    token = client.post("/auth/token", data={"username": "ana@exemplo.com", "password": "senha-segura-123"})
    assert token.status_code == 200
    eu = client.get("/usuarios/me", headers={"Authorization": f"Bearer {token.json()['access_token']}"})
    assert eu.json()["email"] == "ana@exemplo.com"


def test_email_duplicado(client):
    corpo = {"email": "ana@exemplo.com", "senha": "senha-segura-123"}
    client.post("/auth/registrar", json=corpo)
    assert client.post("/auth/registrar", json=corpo).status_code == 409


def test_senha_curta_e_email_invalido(client):
    assert client.post("/auth/registrar", json={"email": "ana@exemplo.com", "senha": "123"}).status_code == 422
    assert client.post("/auth/registrar", json={"email": "ana", "senha": "senha-segura-123"}).status_code == 422


def test_login_invalido(client, auth):
    errada = client.post("/auth/token", data={"username": "ana@exemplo.com", "password": "outra-senha"})
    inexistente = client.post("/auth/token", data={"username": "bia@exemplo.com", "password": "senha-segura-123"})
    assert errada.status_code == inexistente.status_code == 401


def test_rotas_protegidas_exigem_token_valido(client):
    assert client.get("/notas").status_code == 401
    assert client.get("/notas", headers={"Authorization": "Bearer invalido"}).status_code == 401


def test_token_expirado(client, auth):
    vencido = jwt.encode(
        {"sub": "1", "exp": datetime.now(UTC) - timedelta(minutes=1)}, get_settings().secret_key, algorithm="HS256"
    )
    assert client.get("/usuarios/me", headers={"Authorization": f"Bearer {vencido}"}).status_code == 401
