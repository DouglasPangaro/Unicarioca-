import calendar
from datetime import date
from decimal import Decimal
from typing import Annotated

from pydantic import Field, field_validator, model_validator

from app.domain.modelos import ZERO
from app.schemas.comum import DataPassada, Dinheiro, Esquema, Quantidade, Ticker, Valor


class PosicaoInicialEntrada(Esquema):
    ticker: Ticker
    quantidade: Quantidade
    custo_total: Annotated[Decimal, Field(gt=0, max_digits=14, decimal_places=2)]


class SaldoInicialEntrada(Esquema):
    data_referencia: DataPassada = Field(description="Último dia do mês anterior ao primeiro lançamento.")
    prejuizo_day_trade: Dinheiro = ZERO
    prejuizo_comum: Dinheiro = ZERO
    imposto_pendente: Annotated[Decimal, Field(ge=0, lt=10, decimal_places=2)] = Field(
        default=ZERO, description="Imposto abaixo de R$ 10,00 ainda não recolhido."
    )
    posicoes: list[PosicaoInicialEntrada] = Field(default_factory=list, max_length=500)

    @field_validator("data_referencia")
    @classmethod
    def _fim_de_mes(cls, dia: date) -> date:
        if dia.day != calendar.monthrange(dia.year, dia.month)[1]:
            raise ValueError("use o último dia de um mês")
        return dia

    @model_validator(mode="after")
    def _tickers_unicos(self):
        tickers = [p.ticker for p in self.posicoes]
        if len(tickers) != len(set(tickers)):
            raise ValueError("cada ticker deve aparecer uma única vez em posicoes")
        return self


class PosicaoInicialSaida(Esquema):
    ticker: str
    quantidade: int
    custo_total: Valor


class SaldoInicialSaida(Esquema):
    data_referencia: date
    prejuizo_day_trade: Valor
    prejuizo_comum: Valor
    imposto_pendente: Valor
    posicoes: list[PosicaoInicialSaida]
