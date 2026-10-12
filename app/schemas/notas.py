from datetime import date
from typing import Annotated

from pydantic import Field, StringConstraints

from app.domain.modelos import ZERO, Lado
from app.models.nota import OrigemNota
from app.schemas.comum import DataPregao, Dinheiro, Esquema, Preco, Quantidade, Ticker, Valor

NumeroNota = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=30)]


class OperacaoEntrada(Esquema):
    ticker: Ticker
    lado: Lado
    quantidade: Quantidade
    preco: Preco


class NotaAtualizar(Esquema):
    corretora_id: int
    data_pregao: DataPregao
    numero: NumeroNota | None = None
    corretagem: Dinheiro = ZERO
    emolumentos: Dinheiro = ZERO
    taxa_liquidacao: Dinheiro = ZERO
    iss: Dinheiro = ZERO
    outras_taxas: Dinheiro = ZERO


class NotaCriar(NotaAtualizar):
    operacoes: list[OperacaoEntrada] = Field(min_length=1, max_length=500)


class OperacaoSaida(Esquema):
    id: int
    ticker: str
    lado: Lado
    quantidade: int
    preco: Valor


class NotaSaida(Esquema):
    id: int
    corretora_id: int
    corretora_nome: str
    data_pregao: date
    numero: str | None
    corretagem: Valor
    emolumentos: Valor
    taxa_liquidacao: Valor
    iss: Valor
    outras_taxas: Valor
    custos_totais: Valor
    origem: OrigemNota
    custos_pendentes: bool
    operacoes: list[OperacaoSaida]
