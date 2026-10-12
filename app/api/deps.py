from typing import Annotated

from fastapi import Depends, HTTPException, Path, Query, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import ler_token
from app.models import Usuario

DbDep = Annotated[Session, Depends(get_db)]
_oauth2 = OAuth2PasswordBearer(tokenUrl="/auth/token")


def get_usuario_atual(token: Annotated[str, Depends(_oauth2)], db: DbDep) -> Usuario:
    usuario_id = ler_token(token)
    usuario = db.get(Usuario, usuario_id) if usuario_id is not None else None
    if usuario is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Credenciais inválidas ou expiradas.", headers={"WWW-Authenticate": "Bearer"}
        )
    return usuario


UsuarioDep = Annotated[Usuario, Depends(get_usuario_atual)]
Limite = Annotated[int, Query(ge=1, le=500)]
Deslocamento = Annotated[int, Query(ge=0)]
Ano = Annotated[int, Path(ge=2005, le=2100)]
Mes = Annotated[int, Path(ge=1, le=12)]
CompetenciaPath = Annotated[str, Path(pattern=r"^\d{4}-(0[1-9]|1[0-2])$", examples=["2026-02"])]
