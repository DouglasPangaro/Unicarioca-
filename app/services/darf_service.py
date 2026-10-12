from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import tempo
from app.core.erros import Conflito, Invalido, NaoEncontrado
from app.domain.acrescimos import Acrescimos, calcular_acrescimos, meses_selic
from app.domain.calendario import ultimo_dia
from app.domain.modelos import Darf, ler_competencia
from app.integrations.bcb import ClienteSelic
from app.models import PagamentoDarf
from app.services.carregador import apurar_usuario


def obter_darf(db: Session, usuario_id: int, competencia: str) -> tuple[Darf, PagamentoDarf | None]:
    ano, mes = ler_competencia(competencia)
    dados, resultado = apurar_usuario(db, usuario_id, ate=ultimo_dia(ano, mes))
    apuracao = resultado.mes(ano, mes)
    if apuracao is None or apuracao.darf is None:
        raise Invalido(f"Não há DARF a pagar na competência {competencia}.")
    return apuracao.darf, dados.pagamentos.get(competencia)


def calcular_atualizado(darf: Darf, data_pagamento: date, cliente: ClienteSelic) -> Acrescimos:
    meses = meses_selic(darf.vencimento, data_pagamento) if data_pagamento > darf.vencimento else []
    selic = cliente.selic_mensal(meses) if meses else {}
    return calcular_acrescimos(darf.valor, darf.vencimento, data_pagamento, selic)


def registrar_pagamento(
    db: Session, usuario_id: int, competencia: str, data_pagamento: date, cliente: ClienteSelic
) -> PagamentoDarf:
    fim_competencia = ultimo_dia(*ler_competencia(competencia))
    if fim_competencia >= tempo.hoje():
        raise Invalido(f"A competência {competencia} ainda não terminou.")
    if data_pagamento <= fim_competencia:
        raise Invalido("A data de pagamento deve ser posterior ao fim da competência.")
    darf, existente = obter_darf(db, usuario_id, competencia)
    if existente:
        raise Conflito(f"O DARF de {competencia} já está registrado como pago.")
    acrescimos = calcular_atualizado(darf, data_pagamento, cliente)
    pagamento = PagamentoDarf(
        usuario_id=usuario_id,
        competencia=competencia,
        valor_principal=darf.valor,
        multa=acrescimos.multa,
        juros=acrescimos.juros,
        valor_total=acrescimos.total,
        data_pagamento=data_pagamento,
    )
    db.add(pagamento)
    db.commit()
    return pagamento


def cancelar_pagamento(db: Session, usuario_id: int, competencia: str) -> None:
    pagamento = db.scalar(
        select(PagamentoDarf).where(PagamentoDarf.usuario_id == usuario_id, PagamentoDarf.competencia == competencia)
    )
    if pagamento is None:
        raise NaoEncontrado(f"Não há pagamento registrado para {competencia}.")
    db.delete(pagamento)
    db.commit()
