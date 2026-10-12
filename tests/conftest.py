import os
import shutil
from decimal import Decimal
from pathlib import Path

os.environ["SECRET_KEY"] = "chave-de-teste-" + "0" * 50
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.db import criar_fabrica, get_db  # noqa: E402
from app.integrations.bcb import SelicIndisponivel, get_cliente_selic  # noqa: E402
from app.main import app  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent


class SelicFake:
    def __init__(self):
        self.valores: dict[tuple[int, int], Decimal] = {}
        self.erro: Exception | None = None

    def selic_mensal(self, meses):
        if self.erro:
            raise self.erro
        ausentes = [m for m in meses if m not in self.valores]
        if ausentes:
            raise SelicIndisponivel(f"Selic ausente: {ausentes}")
        return {m: self.valores[m] for m in meses}


@pytest.fixture(scope="session")
def banco_migrado(tmp_path_factory) -> Path:
    caminho = tmp_path_factory.mktemp("banco") / "modelo.db"
    config = Config(str(RAIZ / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{caminho.as_posix()}")
    command.upgrade(config, "head")
    return caminho


@pytest.fixture
def fabrica(banco_migrado, tmp_path):
    destino = tmp_path / "teste.db"
    shutil.copyfile(banco_migrado, destino)
    fabrica = criar_fabrica(f"sqlite:///{destino.as_posix()}")
    yield fabrica
    fabrica.kw["bind"].dispose()


@pytest.fixture
def selic() -> SelicFake:
    return SelicFake()


@pytest.fixture
def client(fabrica, selic):
    def _get_db():
        with fabrica() as sessao:
            yield sessao

    app.dependency_overrides[get_db] = _get_db
    app.dependency_overrides[get_cliente_selic] = lambda: selic
    with TestClient(app) as cliente:
        yield cliente
    app.dependency_overrides.clear()


def registrar(client: TestClient, email: str = "ana@exemplo.com", senha: str = "senha-segura-123") -> dict:
    client.post("/auth/registrar", json={"email": email, "senha": senha})
    resposta = client.post("/auth/token", data={"username": email, "password": senha})
    return {"Authorization": f"Bearer {resposta.json()['access_token']}"}


@pytest.fixture
def auth(client) -> dict:
    return registrar(client)
