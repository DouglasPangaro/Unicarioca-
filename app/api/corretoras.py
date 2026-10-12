from fastapi import APIRouter, status
from sqlalchemy import select

from app.api.deps import DbDep, Deslocamento, Limite, UsuarioDep
from app.core.erros import Conflito
from app.models import Corretora
from app.repositories.consultas import buscar_corretora_por_nome, corretora_em_uso, obter
from app.schemas.cadastros import CorretoraEntrada, CorretoraSaida

router = APIRouter(prefix="/corretoras", tags=["Corretoras"])


def _garantir_nome_livre(db: DbDep, usuario_id: int, nome: str) -> None:
    if buscar_corretora_por_nome(db, usuario_id, nome) is not None:
        raise Conflito(f"Já existe a corretora {nome!r}.")


@router.get("", response_model=list[CorretoraSaida])
def listar(usuario: UsuarioDep, db: DbDep, limit: Limite = 50, offset: Deslocamento = 0) -> list[Corretora]:
    consulta = (
        select(Corretora).where(Corretora.usuario_id == usuario.id).order_by(Corretora.nome).limit(limit).offset(offset)
    )
    return list(db.scalars(consulta))


@router.post("", status_code=status.HTTP_201_CREATED, response_model=CorretoraSaida)
def criar(dados: CorretoraEntrada, usuario: UsuarioDep, db: DbDep) -> Corretora:
    _garantir_nome_livre(db, usuario.id, dados.nome)
    corretora = Corretora(usuario_id=usuario.id, **dados.model_dump())
    db.add(corretora)
    db.commit()
    return corretora


@router.get("/{corretora_id}", response_model=CorretoraSaida)
def detalhar(corretora_id: int, usuario: UsuarioDep, db: DbDep) -> Corretora:
    return obter(db, Corretora, corretora_id, usuario.id)


@router.put("/{corretora_id}", response_model=CorretoraSaida)
def atualizar(corretora_id: int, dados: CorretoraEntrada, usuario: UsuarioDep, db: DbDep) -> Corretora:
    corretora = obter(db, Corretora, corretora_id, usuario.id)
    if dados.nome != corretora.nome:
        _garantir_nome_livre(db, usuario.id, dados.nome)
    corretora.nome, corretora.cnpj = dados.nome, dados.cnpj
    db.commit()
    return corretora


@router.delete("/{corretora_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir(corretora_id: int, usuario: UsuarioDep, db: DbDep) -> None:
    corretora = obter(db, Corretora, corretora_id, usuario.id)
    if corretora_em_uso(db, corretora.id):
        raise Conflito("A corretora possui notas; exclua-as antes.")
    db.delete(corretora)
    db.commit()
