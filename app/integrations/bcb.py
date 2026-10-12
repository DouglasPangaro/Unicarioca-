from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from functools import lru_cache

import httpx

from app.core import tempo
from app.core.config import get_settings
from app.core.erros import ServicoIndisponivel
from app.domain.calendario import ultimo_dia
from app.domain.modelos import competencia

URL_SELIC_MENSAL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.4390/dados"


class SelicIndisponivel(ServicoIndisponivel):
    pass


class ClienteSelic:
    """Selic acumulada no mês (série SGS 4390, em % ao mês) do Banco Central."""

    def __init__(self, http: httpx.Client | None = None, timeout: float = 10.0):
        self._http = http or httpx.Client(timeout=timeout)
        self._cache: dict[tuple[int, int], Decimal] = {}

    def selic_mensal(self, meses: Sequence[tuple[int, int]]) -> dict[tuple[int, int], Decimal]:
        hoje = tempo.hoje()
        mes_atual = (hoje.year, hoje.month)
        if any(m >= mes_atual for m in meses):
            raise SelicIndisponivel("A Selic do mês corrente ainda não está fechada.")
        faltando = [m for m in meses if m not in self._cache]
        if faltando:
            self._buscar(min(faltando), max(faltando), mes_atual)
        ausentes = [m for m in meses if m not in self._cache]
        if ausentes:
            raise SelicIndisponivel(
                f"Selic ainda não publicada para {', '.join(competencia(*m) for m in ausentes)}."
            )
        return {m: self._cache[m] for m in meses}

    def _buscar(self, inicio: tuple[int, int], fim: tuple[int, int], mes_atual: tuple[int, int]) -> None:
        params = {
            "formato": "json",
            "dataInicial": f"01/{inicio[1]:02d}/{inicio[0]}",
            "dataFinal": f"{ultimo_dia(*fim):%d/%m/%Y}",
        }
        try:
            resposta = self._http.get(URL_SELIC_MENSAL, params=params)
            resposta.raise_for_status()
            for item in resposta.json():
                dia = datetime.strptime(item["data"], "%d/%m/%Y").date()
                # o valor do mês corrente é parcial e não pode ir para o cache
                if (dia.year, dia.month) < mes_atual:
                    self._cache[(dia.year, dia.month)] = Decimal(item["valor"])
        except (httpx.HTTPError, ValueError, KeyError, TypeError, ArithmeticError) as erro:
            raise SelicIndisponivel("Não foi possível consultar a Selic no Banco Central.") from erro


@lru_cache
def get_cliente_selic() -> ClienteSelic:
    return ClienteSelic(timeout=get_settings().bcb_timeout_segundos)
