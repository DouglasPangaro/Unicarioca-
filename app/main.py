from fastapi import FastAPI

from app.api import apuracoes, ativos, auth, corretoras, darfs, extras, notas, saldo_inicial
from app.api.erros import registrar_tratadores
from app.core.config import get_settings

DESCRICAO = """
CRUD de notas de corretagem com apuração automática do imposto de renda sobre ações e ETFs na B3.

* Classifica cada operação como **day trade** (mesmo dia, ativo e corretora) ou **operação comum**.
* Apura o mês: custos rateados, compensação de prejuízos, isenção de R$ 20 mil, IRRF e DARF (código 6015).
* Extras: DARF em atraso com Selic do Banco Central, importação da planilha da B3, simulador e relatório para o IRPF.

Use **/auth/registrar**, depois o botão **Authorize** (e-mail no campo *username*).
"""


def criar_app() -> FastAPI:
    if len(get_settings().secret_key) < 32:
        raise RuntimeError(
            "Defina SECRET_KEY com pelo menos 32 caracteres no ambiente ou no arquivo .env (veja .env.example)."
        )
    app = FastAPI(title="API de Tributação de Day Trade (B3)", version="1.0.0", description=DESCRICAO)
    registrar_tratadores(app)
    for modulo in (auth, corretoras, ativos, notas, saldo_inicial, apuracoes, darfs, extras):
        app.include_router(modulo.router)

    @app.get("/health", tags=["Sistema"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = criar_app()
