from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select

from app.api.deps import DbDep, UsuarioDep
from app.core.erros import Conflito
from app.core.security import criar_token, gerar_hash, verificar_senha
from app.models import Usuario
from app.schemas.auth import Token, UsuarioCriar, UsuarioSaida

router = APIRouter(tags=["Autenticação"])


@router.post("/auth/registrar", status_code=status.HTTP_201_CREATED, response_model=UsuarioSaida)
def registrar(dados: UsuarioCriar, db: DbDep) -> Usuario:
    email = dados.email.lower()
    if db.scalar(select(Usuario.id).where(Usuario.email == email)) is not None:
        raise Conflito("E-mail já cadastrado.")
    usuario = Usuario(email=email, senha_hash=gerar_hash(dados.senha))
    db.add(usuario)
    db.commit()
    return usuario


@router.post("/auth/token", response_model=Token)
def entrar(form: Annotated[OAuth2PasswordRequestForm, Depends()], db: DbDep) -> Token:
    """Login com e-mail no campo `username` (botão Authorize do Swagger)."""
    usuario = db.scalar(select(Usuario).where(Usuario.email == form.username.strip().lower()))
    if not verificar_senha(form.password, usuario.senha_hash if usuario else None):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "E-mail ou senha incorretos.", headers={"WWW-Authenticate": "Bearer"}
        )
    return Token(access_token=criar_token(usuario.id))


@router.get("/usuarios/me", response_model=UsuarioSaida)
def eu(usuario: UsuarioDep) -> Usuario:
    return usuario
