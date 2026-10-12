from datetime import UTC, datetime, timedelta

import jwt
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash

from app.core.config import get_settings

ALGORITMO = "HS256"
_hasher = PasswordHash.recommended()
# conferido quando o e-mail não existe, para o tempo de resposta não revelar quais e-mails estão cadastrados
_HASH_FICTICIO = _hasher.hash("senha-ficticia")


def gerar_hash(senha: str) -> str:
    return _hasher.hash(senha)


def verificar_senha(senha: str, senha_hash: str | None) -> bool:
    if senha_hash is None:
        _hasher.verify(senha, _HASH_FICTICIO)
        return False
    return _hasher.verify(senha, senha_hash)


def criar_token(usuario_id: int) -> str:
    settings = get_settings()
    expira = datetime.now(UTC) + timedelta(minutes=settings.jwt_expira_minutos)
    return jwt.encode({"sub": str(usuario_id), "exp": expira}, settings.secret_key, algorithm=ALGORITMO)


def ler_token(token: str) -> int | None:
    try:
        payload = jwt.decode(
            token, get_settings().secret_key, algorithms=[ALGORITMO], options={"require": ["exp", "sub"]}
        )
        return int(payload["sub"])
    except (InvalidTokenError, ValueError):
        return None
