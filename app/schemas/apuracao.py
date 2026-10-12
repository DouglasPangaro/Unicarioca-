from datetime import date
from enum import StrEnum

from app.domain.modelos import ZERO, Modalidade, TipoAtivo
from app.schemas.comum import DataPassada, Dinheiro, Esquema, Preco, PrecoMedio, Quantidade, Taxa, Ticker, Valor


class EventoDayTradeSaida(Esquema):
    data: date
    corretora: str
    ticker: str
    quantidade: int
    preco_medio_compra: PrecoMedio
    preco_medio_venda: PrecoMedio
    resultado: Valor


class VendaComumSaida(Esquema):
    data: date
    corretora: str
    ticker: str
    tipo_ativo: TipoAtivo
    quantidade: int
    valor_venda: Valor
    preco_medio: PrecoMedio
    resultado: Valor


class ResultadoModalidadeSaida(Esquema):
    resultado_liquido: Valor
    prejuizo_anterior: Valor
    prejuizo_compensado: Valor
    base_calculo: Valor
    aliquota: Taxa
    imposto: Valor
    prejuizo_a_compensar: Valor


class IsencaoSaida(Esquema):
    vendas_acoes: Valor
    limite: Valor | None
    isento: bool
    lucro_isento: Valor


class IRRFSaida(Esquema):
    do_mes: Valor
    meses_anteriores: Valor
    compensado: Valor
    a_compensar: Valor


class DarfSaida(Esquema):
    competencia: str
    codigo: str
    valor: Valor
    vencimento: date


class ApuracaoMensalSaida(Esquema):
    competencia: str
    day_trade: ResultadoModalidadeSaida
    comum: ResultadoModalidadeSaida
    isencao: IsencaoSaida
    imposto_devido: Valor
    irrf_day_trade: IRRFSaida
    irrf_comum: IRRFSaida
    imposto_a_pagar: Valor
    imposto_pendente_anterior: Valor
    imposto_pendente: Valor
    darf: DarfSaida | None
    eventos_day_trade: list[EventoDayTradeSaida]
    vendas_comuns: list[VendaComumSaida]


class ResumoMensal(Esquema):
    competencia: str
    resultado_day_trade: Valor
    resultado_comum: Valor
    lucro_isento: Valor
    imposto_devido: Valor
    darf: DarfSaida | None


class ApuracaoAnualSaida(Esquema):
    ano: int
    meses: list[ResumoMensal]
    total_imposto_devido: Valor
    total_darfs: Valor
    total_lucro_isento: Valor


class PosicaoSaida(Esquema):
    ticker: str
    tipo_ativo: TipoAtivo
    quantidade: int
    preco_medio: PrecoMedio
    custo_total: Valor


class StatusDarf(StrEnum):
    PENDENTE = "PENDENTE"
    VENCIDO = "VENCIDO"
    PAGO = "PAGO"


class PagamentoEntrada(Esquema):
    data_pagamento: DataPassada


class PagamentoSaida(Esquema):
    competencia: str
    valor_principal: Valor
    multa: Valor
    juros: Valor
    valor_total: Valor
    data_pagamento: date


class DarfItem(Esquema):
    competencia: str
    codigo: str
    valor: Valor
    vencimento: date
    status: StatusDarf
    pagamento: PagamentoSaida | None


class DarfAtualizadoSaida(Esquema):
    competencia: str
    codigo: str
    valor_principal: Valor
    vencimento: date
    data_pagamento: date
    dias_atraso: int
    multa_percentual: Valor
    multa: Valor
    juros_percentual: Valor
    juros: Valor
    valor_total: Valor


class RegraSaida(Esquema):
    id: int
    modalidade: Modalidade
    aliquota: Taxa
    aliquota_irrf: Taxa
    limite_isencao_acoes: Valor | None
    vigencia_inicio: date
    vigencia_fim: date | None


class SimulacaoEntrada(Esquema):
    ticker: Ticker
    quantidade: Quantidade
    preco: Preco
    corretora_id: int
    data: date | None = None
    custos: Dinheiro = ZERO


class SimulacaoSaida(Esquema):
    competencia: str
    modalidade: str
    quantidade_day_trade: int
    quantidade_comum: int
    resultado_day_trade: Valor
    resultado_comum: Valor
    vendas_acoes_antes: Valor
    vendas_acoes_depois: Valor
    isento_antes: bool
    isento_depois: bool
    perde_isencao: bool
    imposto_devido_antes: Valor
    imposto_devido_depois: Valor
    darf_antes: Valor
    darf_depois: Valor
    diferenca_darf: Valor
