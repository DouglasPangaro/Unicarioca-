from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.core.erros import ErroAplicacao
from app.domain.erros import ErroDominio


def registrar_tratadores(app: FastAPI) -> None:
    @app.exception_handler(ErroAplicacao)
    async def _erro_aplicacao(_request: Request, erro: ErroAplicacao) -> JSONResponse:
        return JSONResponse(status_code=erro.status_code, content={"detail": erro.mensagem, **erro.extras})

    @app.exception_handler(ErroDominio)
    async def _erro_dominio(_request: Request, erro: ErroDominio) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(erro)})

    @app.exception_handler(IntegrityError)
    async def _integridade(_request: Request, _erro: IntegrityError) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": "Registro duplicado ou em uso por outros dados."})
