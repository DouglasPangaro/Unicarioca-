import re

from app.domain.modelos import TipoAtivo

# 4 caracteres + 1-2 dígitos; o "F" final é o mesmo ativo negociado no mercado fracionário
_PADRAO = re.compile(r"([A-Z0-9]{4})(\d{1,2})F?")


def normalizar_ticker(ticker: str) -> str:
    texto = ticker.strip().upper()
    encontrado = _PADRAO.fullmatch(texto)
    if not encontrado:
        raise ValueError(f"Ticker inválido: {ticker!r}")
    return encontrado.group(1) + encontrado.group(2)


def tipo_por_ticker(ticker: str) -> TipoAtivo | None:
    """Final 3 a 8 é ação; final 11 pode ser ETF, FII ou unit, então exige cadastro manual."""
    sufixo = int(_PADRAO.fullmatch(ticker).group(2))
    return TipoAtivo.ACAO if 3 <= sufixo <= 8 else None
