from pydantic import EmailStr, Field

from app.schemas.comum import Esquema


class UsuarioCriar(Esquema):
    email: EmailStr
    senha: str = Field(min_length=8, max_length=128)


class UsuarioSaida(Esquema):
    id: int
    email: str


class Token(Esquema):
    access_token: str
    token_type: str = "bearer"
