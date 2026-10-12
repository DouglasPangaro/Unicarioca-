from typing import TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.erros import ErroAplicacao, Invalido, NaoEncontrado
from app.domain.tickers import tipo_por_ticker
from app.models import Ativo, Corretora, NotaCorretagem, Operacao, PosicaoInicial

T = TypeVar("T")


def obter(
    db: Session, modelo: type[T], id_: int, usuario_id: int, erro: type[ErroAplicacao] = NaoEncontrado
) -> T:
    """Registro do usuário; o de outro usuário responde como inexistente."""
    objeto = db.get(modelo, id_)
    if objeto is None or objeto.usuario_id != usuario_id:
        raise erro(f"{modelo.__name__} {id_} não encontrado.")
    return objeto


def buscar_ativo(db: Session, usuario_id: int, ticker: str) -> Ativo | None:
    return db.scalar(select(Ativo).where(Ativo.usuario_id == usuario_id, Ativo.ticker == ticker))


def criar_ativo_automatico(db: Session, usuario_id: int, ticker: str) -> Ativo | None:
    tipo = tipo_por_ticker(ticker)
    if tipo is None:
        return None
    ativo = Ativo(usuario_id=usuario_id, ticker=ticker, tipo=tipo)
    db.add(ativo)
    db.flush()
    return ativo


def obter_ou_criar_ativo(db: Session, usuario_id: int, ticker: str) -> Ativo:
    ativo = buscar_ativo(db, usuario_id, ticker) or criar_ativo_automatico(db, usuario_id, ticker)
    if ativo is None:
        raise Invalido(
            f"Ativo {ticker} não cadastrado. Cadastre-o em /ativos informando o tipo (ACAO ou ETF)."
        )
    return ativo


def corretora_em_uso(db: Session, corretora_id: int) -> bool:
    consulta = select(NotaCorretagem.id).where(NotaCorretagem.corretora_id == corretora_id).limit(1)
    return db.scalar(consulta) is not None


def ativo_em_uso(db: Session, ativo_id: int) -> bool:
    em_operacao = db.scalar(select(Operacao.id).where(Operacao.ativo_id == ativo_id).limit(1))
    em_saldo = db.scalar(select(PosicaoInicial.id).where(PosicaoInicial.ativo_id == ativo_id).limit(1))
    return em_operacao is not None or em_saldo is not None


def buscar_corretora_por_nome(db: Session, usuario_id: int, nome: str) -> Corretora | None:
    return db.scalar(select(Corretora).where(Corretora.usuario_id == usuario_id, Corretora.nome == nome))
