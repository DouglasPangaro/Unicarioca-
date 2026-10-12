from datetime import date

from sqlalchemy.orm import Session

from app.core import tempo
from app.core.erros import Invalido
from app.domain import modelos as dom
from app.domain.apuracao import apurar
from app.domain.irpf import RelatorioIRPF, montar_relatorio
from app.domain.simulacao import ResultadoSimulacao, simular_venda
from app.models import Corretora
from app.repositories.consultas import buscar_ativo, obter
from app.schemas.apuracao import SimulacaoEntrada
from app.services.carregador import carregar


def simular(db: Session, usuario_id: int, entrada: SimulacaoEntrada) -> ResultadoSimulacao:
    corretora = obter(db, Corretora, entrada.corretora_id, usuario_id, erro=Invalido)
    ativo = buscar_ativo(db, usuario_id, entrada.ticker)
    if ativo is None:
        raise Invalido(f"Ativo {entrada.ticker} não cadastrado.")
    dados = carregar(db, usuario_id)
    negocio = dom.Negocio(ativo.ticker, dom.TipoAtivo(ativo.tipo), dom.Lado.VENDA, entrada.quantidade, entrada.preco)
    venda = dom.Nota(entrada.data or tempo.hoje(), corretora.nome, (negocio,), entrada.custos)
    return simular_venda(dados.notas, dados.regras, dados.saldo_inicial, venda)


def relatorio_irpf(db: Session, usuario_id: int, ano: int) -> RelatorioIRPF:
    dados = carregar(db, usuario_id)
    atual = apurar(dados.notas, dados.regras, dados.saldo_inicial, ate=date(ano, 12, 31))
    anterior = apurar(dados.notas, dados.regras, dados.saldo_inicial, ate=date(ano - 1, 12, 31))
    pagos = {c: p.valor_principal for c, p in dados.pagamentos.items()}
    return montar_relatorio(ano, atual.meses, dados.regras, anterior.posicoes, atual.posicoes, pagos)
