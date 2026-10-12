from datetime import date

from fastapi import APIRouter, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import DbDep, Deslocamento, Limite, UsuarioDep
from app.core.erros import Invalido, NaoEncontrado
from app.models import Corretora, NotaCorretagem, Operacao
from app.repositories.consultas import obter, obter_ou_criar_ativo
from app.schemas.notas import NotaAtualizar, NotaCriar, NotaSaida, OperacaoEntrada, OperacaoSaida
from app.services.escrita import validar_e_confirmar

router = APIRouter(prefix="/notas", tags=["Notas de corretagem"])


def _nova_operacao(db: Session, usuario_id: int, dados: OperacaoEntrada) -> Operacao:
    return Operacao(
        ativo=obter_ou_criar_ativo(db, usuario_id, dados.ticker),
        lado=dados.lado,
        quantidade=dados.quantidade,
        preco=dados.preco,
    )


def _obter_operacao(nota: NotaCorretagem, operacao_id: int) -> Operacao:
    operacao = next((op for op in nota.operacoes if op.id == operacao_id), None)
    if operacao is None:
        raise NaoEncontrado(f"Operacao {operacao_id} não encontrado.")
    return operacao


@router.get("", response_model=list[NotaSaida])
def listar(
    usuario: UsuarioDep,
    db: DbDep,
    inicio: date | None = None,
    fim: date | None = None,
    corretora_id: int | None = None,
    limit: Limite = 50,
    offset: Deslocamento = 0,
) -> list[NotaSaida]:
    consulta = (
        select(NotaCorretagem)
        .where(NotaCorretagem.usuario_id == usuario.id)
        .options(selectinload(NotaCorretagem.operacoes))
    )
    if inicio:
        consulta = consulta.where(NotaCorretagem.data_pregao >= inicio)
    if fim:
        consulta = consulta.where(NotaCorretagem.data_pregao <= fim)
    if corretora_id:
        consulta = consulta.where(NotaCorretagem.corretora_id == corretora_id)
    consulta = consulta.order_by(NotaCorretagem.data_pregao.desc(), NotaCorretagem.id.desc()).limit(limit).offset(offset)
    return [NotaSaida.model_validate(nota) for nota in db.scalars(consulta).unique()]


@router.post("", status_code=status.HTTP_201_CREATED, response_model=NotaSaida)
def criar(dados: NotaCriar, usuario: UsuarioDep, db: DbDep) -> NotaSaida:
    """Cria a nota com suas operações; o ativo é cadastrado automaticamente se o ticker for de ação."""
    corretora = obter(db, Corretora, dados.corretora_id, usuario.id, erro=Invalido)
    nota = NotaCorretagem(
        usuario_id=usuario.id,
        corretora=corretora,
        operacoes=[_nova_operacao(db, usuario.id, op) for op in dados.operacoes],
        **dados.model_dump(exclude={"corretora_id", "operacoes"}),
    )
    db.add(nota)
    validar_e_confirmar(db, usuario.id)
    return NotaSaida.model_validate(nota)


@router.get("/{nota_id}", response_model=NotaSaida)
def detalhar(nota_id: int, usuario: UsuarioDep, db: DbDep) -> NotaSaida:
    return NotaSaida.model_validate(obter(db, NotaCorretagem, nota_id, usuario.id))


@router.put("/{nota_id}", response_model=NotaSaida)
def atualizar(nota_id: int, dados: NotaAtualizar, usuario: UsuarioDep, db: DbDep) -> NotaSaida:
    """Atualiza cabeçalho e custos; as operações têm rotas próprias."""
    nota = obter(db, NotaCorretagem, nota_id, usuario.id)
    nota.corretora = obter(db, Corretora, dados.corretora_id, usuario.id, erro=Invalido)
    for campo, valor in dados.model_dump(exclude={"corretora_id"}).items():
        setattr(nota, campo, valor)
    nota.custos_pendentes = False
    validar_e_confirmar(db, usuario.id)
    return NotaSaida.model_validate(nota)


@router.delete("/{nota_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir(nota_id: int, usuario: UsuarioDep, db: DbDep) -> None:
    db.delete(obter(db, NotaCorretagem, nota_id, usuario.id))
    validar_e_confirmar(db, usuario.id)


@router.post("/{nota_id}/operacoes", status_code=status.HTTP_201_CREATED, response_model=OperacaoSaida)
def adicionar_operacao(nota_id: int, dados: OperacaoEntrada, usuario: UsuarioDep, db: DbDep) -> OperacaoSaida:
    nota = obter(db, NotaCorretagem, nota_id, usuario.id)
    operacao = _nova_operacao(db, usuario.id, dados)
    nota.operacoes.append(operacao)
    validar_e_confirmar(db, usuario.id)
    return OperacaoSaida.model_validate(operacao)


@router.put("/{nota_id}/operacoes/{operacao_id}", response_model=OperacaoSaida)
def atualizar_operacao(
    nota_id: int, operacao_id: int, dados: OperacaoEntrada, usuario: UsuarioDep, db: DbDep
) -> OperacaoSaida:
    operacao = _obter_operacao(obter(db, NotaCorretagem, nota_id, usuario.id), operacao_id)
    operacao.ativo = obter_ou_criar_ativo(db, usuario.id, dados.ticker)
    operacao.lado, operacao.quantidade, operacao.preco = dados.lado, dados.quantidade, dados.preco
    validar_e_confirmar(db, usuario.id)
    return OperacaoSaida.model_validate(operacao)


@router.delete("/{nota_id}/operacoes/{operacao_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_operacao(nota_id: int, operacao_id: int, usuario: UsuarioDep, db: DbDep) -> None:
    nota = obter(db, NotaCorretagem, nota_id, usuario.id)
    operacao = _obter_operacao(nota, operacao_id)
    if len(nota.operacoes) == 1:
        raise Invalido("A nota precisa de ao menos uma operação; exclua a nota inteira.")
    nota.operacoes.remove(operacao)
    validar_e_confirmar(db, usuario.id)
