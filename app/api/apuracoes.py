from datetime import date

from fastapi import APIRouter

from app.api.deps import Ano, DbDep, Mes, UsuarioDep
from app.core import tempo
from app.domain.apuracao import apuracao_vazia
from app.domain.calendario import ultimo_dia
from app.domain.modelos import ZERO
from app.schemas.apuracao import ApuracaoAnualSaida, ApuracaoMensalSaida, PosicaoSaida, ResumoMensal
from app.services.carregador import apurar_usuario

router = APIRouter(tags=["Apuração"])


@router.get("/apuracoes/{ano}/{mes}", response_model=ApuracaoMensalSaida)
def mensal(ano: Ano, mes: Mes, usuario: UsuarioDep, db: DbDep) -> ApuracaoMensalSaida:
    """Memória de cálculo do mês: day trade, vendas comuns, isenção, compensação, IRRF e DARF."""
    dados, resultado = apurar_usuario(db, usuario.id, ate=ultimo_dia(ano, mes))
    apuracao = resultado.mes(ano, mes) or apuracao_vazia(ano, mes, dados.regras)
    return ApuracaoMensalSaida.model_validate(apuracao)


@router.get("/apuracoes/{ano}", response_model=ApuracaoAnualSaida)
def anual(ano: Ano, usuario: UsuarioDep, db: DbDep) -> ApuracaoAnualSaida:
    dados, resultado = apurar_usuario(db, usuario.id, ate=date(ano, 12, 31))
    meses = [resultado.mes(ano, m) or apuracao_vazia(ano, m, dados.regras) for m in range(1, 13)]
    return ApuracaoAnualSaida(
        ano=ano,
        meses=[
            ResumoMensal(
                competencia=m.competencia,
                resultado_day_trade=m.day_trade.resultado_liquido,
                resultado_comum=m.comum.resultado_liquido,
                lucro_isento=m.isencao.lucro_isento,
                imposto_devido=m.imposto_devido,
                darf=m.darf,
            )
            for m in meses
        ],
        total_imposto_devido=sum((m.imposto_devido for m in meses), ZERO),
        total_darfs=sum((m.darf.valor for m in meses if m.darf), ZERO),
        total_lucro_isento=sum((m.isencao.lucro_isento for m in meses), ZERO),
    )


@router.get("/carteira", response_model=list[PosicaoSaida], tags=["Carteira"])
def carteira(usuario: UsuarioDep, db: DbDep, data: date | None = None) -> list[PosicaoSaida]:
    """Posição e preço médio (custos inclusos) na data informada; padrão: hoje."""
    _, resultado = apurar_usuario(db, usuario.id, ate=data or tempo.hoje())
    return [PosicaoSaida.model_validate(p) for p in resultado.posicoes]
