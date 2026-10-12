import calendar
from datetime import date, timedelta
from functools import lru_cache

import holidays
from dateutil.easter import easter


@lru_cache(maxsize=64)
def _dias_sem_expediente(ano: int) -> frozenset[date]:
    pascoa = easter(ano)
    # Carnaval (seg/ter), Sexta-feira Santa e Corpus Christi não têm expediente bancário
    moveis = {
        pascoa - timedelta(days=48),
        pascoa - timedelta(days=47),
        pascoa - timedelta(days=2),
        pascoa + timedelta(days=60),
    }
    # 31/12 não tem atendimento bancário ao público
    return frozenset(holidays.country_holidays("BR", years=ano)) | moveis | {date(ano, 12, 31)}


def eh_dia_util(dia: date) -> bool:
    return dia.weekday() < 5 and dia not in _dias_sem_expediente(dia.year)


def ultimo_dia(ano: int, mes: int) -> date:
    return date(ano, mes, calendar.monthrange(ano, mes)[1])


def ultimo_dia_util(ano: int, mes: int) -> date:
    dia = ultimo_dia(ano, mes)
    while not eh_dia_util(dia):
        dia -= timedelta(days=1)
    return dia


def mes_seguinte(ano: int, mes: int) -> tuple[int, int]:
    return (ano + 1, 1) if mes == 12 else (ano, mes + 1)


def mes_anterior(ano: int, mes: int) -> tuple[int, int]:
    return (ano - 1, 12) if mes == 1 else (ano, mes - 1)


def meses_entre(inicio: tuple[int, int], fim: tuple[int, int]) -> list[tuple[int, int]]:
    meses = []
    atual = inicio
    while atual <= fim:
        meses.append(atual)
        atual = mes_seguinte(*atual)
    return meses


def vencimento_darf(ano: int, mes: int) -> date:
    """Último dia útil do mês seguinte ao da apuração."""
    return ultimo_dia_util(*mes_seguinte(ano, mes))
