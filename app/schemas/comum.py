from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, PlainSerializer, StringConstraints

from app.core import tempo
from app.domain.modelos import q2
from app.domain.tickers import normalizar_ticker


class Esquema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


def _data_pregao(dia: date) -> date:
    if dia > tempo.hoje():
        raise ValueError("a data do pregão não pode ser futura")
    if dia.weekday() >= 5:
        raise ValueError("não há pregão em fim de semana")
    return dia


def _nao_futura(dia: date) -> date:
    if dia > tempo.hoje():
        raise ValueError("a data não pode ser futura")
    return dia


Ticker = Annotated[str, Field(examples=["PETR4"]), AfterValidator(normalizar_ticker)]
DataPregao = Annotated[date, AfterValidator(_data_pregao)]
DataPassada = Annotated[date, AfterValidator(_nao_futura)]
Nome = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Cnpj = Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}$")]
Dinheiro = Annotated[Decimal, Field(ge=0, max_digits=14, decimal_places=2)]
Preco = Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=2)]
Quantidade = Annotated[int, Field(gt=0, le=100_000_000)]
Competencia = Annotated[str, Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$", examples=["2026-02"])]

Valor = Annotated[Decimal, PlainSerializer(lambda v: str(q2(v)), return_type=str)]
PrecoMedio = Annotated[
    Decimal, PlainSerializer(lambda v: str(v.quantize(Decimal("0.0001"), ROUND_HALF_UP)), return_type=str)
]
Taxa = Annotated[Decimal, PlainSerializer(lambda v: format(v.normalize(), "f"), return_type=str)]
