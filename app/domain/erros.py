from datetime import date


class ErroDominio(Exception):
    """Violação de regra de negócio; a API responde 422."""


class PosicaoInsuficiente(ErroDominio):
    def __init__(self, ticker: str, data: date, disponivel: int, solicitado: int):
        self.ticker = ticker
        self.data = data
        self.disponivel = disponivel
        self.solicitado = solicitado
        super().__init__(
            f"Venda de {solicitado} {ticker} em {data:%d/%m/%Y} sem posição suficiente "
            f"(disponível: {disponivel}). Lance as compras anteriores ou o saldo inicial."
        )


class OperacaoAntesDoSaldoInicial(ErroDominio):
    def __init__(self, data_referencia: date):
        super().__init__(
            f"Há notas com data igual ou anterior ao saldo inicial ({data_referencia:%d/%m/%Y}); "
            "elas já estão refletidas no saldo."
        )


class RegraNaoEncontrada(ErroDominio):
    pass
