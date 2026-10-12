from fastapi import APIRouter, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import DbDep, UsuarioDep
from app.core.erros import NaoEncontrado
from app.models import PosicaoInicial, SaldoInicial
from app.repositories.consultas import obter_ou_criar_ativo
from app.schemas.saldo_inicial import SaldoInicialEntrada, SaldoInicialSaida
from app.services.escrita import validar_e_confirmar

router = APIRouter(prefix="/saldo-inicial", tags=["Saldo inicial"])


def _buscar(db: Session, usuario_id: int) -> SaldoInicial | None:
    return db.scalar(select(SaldoInicial).where(SaldoInicial.usuario_id == usuario_id))


@router.get("", response_model=SaldoInicialSaida)
def detalhar(usuario: UsuarioDep, db: DbDep) -> SaldoInicialSaida:
    saldo = _buscar(db, usuario.id)
    if saldo is None:
        raise NaoEncontrado("Saldo inicial não cadastrado.")
    return SaldoInicialSaida.model_validate(saldo)


@router.put("", response_model=SaldoInicialSaida)
def definir(dados: SaldoInicialEntrada, usuario: UsuarioDep, db: DbDep) -> SaldoInicialSaida:
    """Posições e prejuízos anteriores ao uso do sistema; as notas devem ser posteriores à data de referência."""
    ativos = [obter_ou_criar_ativo(db, usuario.id, p.ticker) for p in dados.posicoes]
    saldo = _buscar(db, usuario.id)
    if saldo is None:
        saldo = SaldoInicial(usuario_id=usuario.id)
        db.add(saldo)
    else:
        # remove as posições antigas antes de inserir as novas (restrição única por ativo)
        saldo.posicoes.clear()
        db.flush()
    saldo.data_referencia = dados.data_referencia
    saldo.prejuizo_day_trade = dados.prejuizo_day_trade
    saldo.prejuizo_comum = dados.prejuizo_comum
    saldo.imposto_pendente = dados.imposto_pendente
    saldo.posicoes.extend(
        PosicaoInicial(ativo=ativo, quantidade=p.quantidade, custo_total=p.custo_total)
        for ativo, p in zip(ativos, dados.posicoes, strict=True)
    )
    validar_e_confirmar(db, usuario.id)
    return SaldoInicialSaida.model_validate(saldo)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def remover(usuario: UsuarioDep, db: DbDep) -> None:
    saldo = _buscar(db, usuario.id)
    if saldo is None:
        raise NaoEncontrado("Saldo inicial não cadastrado.")
    db.delete(saldo)
    validar_e_confirmar(db, usuario.id)
