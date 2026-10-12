from app.domain.modelos import TipoAtivo
from app.schemas.apuracao import IRRFSaida, ResultadoModalidadeSaida
from app.schemas.comum import Esquema, Valor


class LinhaIgnorada(Esquema):
    linha: int
    motivo: str


class RelatorioImportacao(Esquema):
    notas_criadas: int
    operacoes_importadas: int
    duplicadas_ignoradas: int
    ignoradas: list[LinhaIgnorada]
    pendencias: list[str]


class MesIRPFSaida(Esquema):
    mes: int
    comum: ResultadoModalidadeSaida
    day_trade: ResultadoModalidadeSaida
    imposto_devido: Valor
    irrf_day_trade: IRRFSaida
    irrf_comum: IRRFSaida
    imposto_a_pagar: Valor
    imposto_pago: Valor


class BemDireitoSaida(Esquema):
    ticker: str
    tipo_ativo: TipoAtivo
    grupo: str
    codigo: str | None
    quantidade_anterior: int
    situacao_anterior: Valor
    quantidade_atual: int
    situacao_atual: Valor
    discriminacao: str


class RelatorioIRPFSaida(Esquema):
    ano: int
    renda_variavel: list[MesIRPFSaida]
    lucro_isento_acoes: Valor
    bens_e_direitos: list[BemDireitoSaida]
    irrf_a_compensar_na_declaracao: Valor
    prejuizo_day_trade_a_compensar: Valor
    prejuizo_comum_a_compensar: Valor
    observacao: str = "Material de apoio para conferência; não substitui o programa da Receita Federal."
