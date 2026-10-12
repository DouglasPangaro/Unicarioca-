from app.domain.modelos import TipoAtivo
from app.schemas.comum import Cnpj, Esquema, Nome, Ticker


class CorretoraEntrada(Esquema):
    nome: Nome
    cnpj: Cnpj | None = None


class CorretoraSaida(Esquema):
    id: int
    nome: str
    cnpj: str | None


class AtivoEntrada(Esquema):
    ticker: Ticker
    tipo: TipoAtivo = TipoAtivo.ACAO
    nome: Nome | None = None
    cnpj: Cnpj | None = None


class AtivoSaida(Esquema):
    id: int
    ticker: str
    tipo: TipoAtivo
    nome: str | None
    cnpj: str | None
