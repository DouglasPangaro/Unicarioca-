from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import CompetenciaPath, DbDep, UsuarioDep
from app.core import tempo
from app.core.erros import Invalido
from app.integrations.bcb import ClienteSelic, get_cliente_selic
from app.schemas.apuracao import DarfAtualizadoSaida, DarfItem, PagamentoEntrada, PagamentoSaida, StatusDarf
from app.services.carregador import apurar_usuario
from app.services.darf_service import calcular_atualizado, cancelar_pagamento, obter_darf, registrar_pagamento

router = APIRouter(prefix="/darfs", tags=["DARF"])
SelicDep = Annotated[ClienteSelic, Depends(get_cliente_selic)]


@router.get("", response_model=list[DarfItem])
def listar(
    usuario: UsuarioDep,
    db: DbDep,
    situacao: Annotated[StatusDarf | None, Query(alias="status")] = None,
    ano: Annotated[int | None, Query(ge=2005, le=2100)] = None,
) -> list[DarfItem]:
    hoje = tempo.hoje()
    dados, resultado = apurar_usuario(db, usuario.id, ate=hoje)
    itens = []
    for mes in resultado.meses:
        if mes.darf is None or (ano and mes.ano != ano):
            continue
        pagamento = dados.pagamentos.get(mes.competencia)
        if pagamento:
            status_darf = StatusDarf.PAGO
        else:
            status_darf = StatusDarf.VENCIDO if hoje > mes.darf.vencimento else StatusDarf.PENDENTE
        if situacao is None or situacao == status_darf:
            itens.append(
                DarfItem(
                    competencia=mes.darf.competencia,
                    codigo=mes.darf.codigo,
                    valor=mes.darf.valor,
                    vencimento=mes.darf.vencimento,
                    status=status_darf,
                    pagamento=pagamento,
                )
            )
    return itens


@router.get("/{competencia}/atualizado", response_model=DarfAtualizadoSaida)
def atualizado(
    competencia: CompetenciaPath,
    usuario: UsuarioDep,
    db: DbDep,
    cliente: SelicDep,
    data_pagamento: date | None = None,
) -> DarfAtualizadoSaida:
    """Valor com multa (0,33% ao dia, até 20%) e juros Selic para pagamento na data informada (padrão: hoje)."""
    pagamento = data_pagamento or tempo.hoje()
    if pagamento > tempo.hoje():
        raise Invalido("A data de pagamento não pode ser futura: a Selic dos próximos meses ainda não existe.")
    darf, _ = obter_darf(db, usuario.id, competencia)
    acrescimos = calcular_atualizado(darf, pagamento, cliente)
    return DarfAtualizadoSaida(
        competencia=competencia,
        codigo=darf.codigo,
        valor_principal=acrescimos.principal,
        vencimento=acrescimos.vencimento,
        data_pagamento=acrescimos.data_pagamento,
        dias_atraso=acrescimos.dias_atraso,
        multa_percentual=acrescimos.multa_percentual,
        multa=acrescimos.multa,
        juros_percentual=acrescimos.juros_percentual,
        juros=acrescimos.juros,
        valor_total=acrescimos.total,
    )


@router.post("/{competencia}/pagamento", status_code=status.HTTP_201_CREATED, response_model=PagamentoSaida)
def pagar(
    competencia: CompetenciaPath, dados: PagamentoEntrada, usuario: UsuarioDep, db: DbDep, cliente: SelicDep
) -> PagamentoSaida:
    """Registra o pagamento; a partir daí alterações que mudem este DARF são bloqueadas (409)."""
    pagamento = registrar_pagamento(db, usuario.id, competencia, dados.data_pagamento, cliente)
    return PagamentoSaida.model_validate(pagamento)


@router.delete("/{competencia}/pagamento", status_code=status.HTTP_204_NO_CONTENT)
def cancelar(competencia: CompetenciaPath, usuario: UsuarioDep, db: DbDep) -> None:
    cancelar_pagamento(db, usuario.id, competencia)
