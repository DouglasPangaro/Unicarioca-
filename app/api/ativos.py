from fastapi import APIRouter, status
from sqlalchemy import select

from app.api.deps import DbDep, Deslocamento, Limite, UsuarioDep
from app.core.erros import Conflito
from app.models import Ativo
from app.repositories.consultas import ativo_em_uso, buscar_ativo, obter
from app.schemas.cadastros import AtivoEntrada, AtivoSaida
from app.services.escrita import validar_e_confirmar

router = APIRouter(prefix="/ativos", tags=["Ativos"])


def _garantir_ticker_livre(db: DbDep, usuario_id: int, ticker: str) -> None:
    if buscar_ativo(db, usuario_id, ticker) is not None:
        raise Conflito(f"O ativo {ticker} já está cadastrado.")


@router.get("", response_model=list[AtivoSaida])
def listar(usuario: UsuarioDep, db: DbDep, limit: Limite = 50, offset: Deslocamento = 0) -> list[Ativo]:
    consulta = select(Ativo).where(Ativo.usuario_id == usuario.id).order_by(Ativo.ticker).limit(limit).offset(offset)
    return list(db.scalars(consulta))


@router.post("", status_code=status.HTTP_201_CREATED, response_model=AtivoSaida)
def criar(dados: AtivoEntrada, usuario: UsuarioDep, db: DbDep) -> Ativo:
    _garantir_ticker_livre(db, usuario.id, dados.ticker)
    ativo = Ativo(usuario_id=usuario.id, **dados.model_dump())
    db.add(ativo)
    db.commit()
    return ativo


@router.get("/{ativo_id}", response_model=AtivoSaida)
def detalhar(ativo_id: int, usuario: UsuarioDep, db: DbDep) -> Ativo:
    return obter(db, Ativo, ativo_id, usuario.id)


@router.put("/{ativo_id}", response_model=AtivoSaida)
def atualizar(ativo_id: int, dados: AtivoEntrada, usuario: UsuarioDep, db: DbDep) -> Ativo:
    """Trocar o tipo muda a isenção; por isso a alteração passa pela revalidação do histórico."""
    ativo = obter(db, Ativo, ativo_id, usuario.id)
    if dados.ticker != ativo.ticker:
        _garantir_ticker_livre(db, usuario.id, dados.ticker)
    for campo, valor in dados.model_dump().items():
        setattr(ativo, campo, valor)
    validar_e_confirmar(db, usuario.id)
    return ativo


@router.delete("/{ativo_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir(ativo_id: int, usuario: UsuarioDep, db: DbDep) -> None:
    ativo = obter(db, Ativo, ativo_id, usuario.id)
    if ativo_em_uso(db, ativo.id):
        raise Conflito("O ativo é usado em operações ou no saldo inicial.")
    db.delete(ativo)
    db.commit()
