from sqlalchemy.orm import Session

from app.core.erros import Conflito
from app.domain.apuracao import apurar
from app.domain.consistencia import verificar_pagamentos
from app.domain.modelos import q2
from app.services.carregador import carregar


def validar_e_confirmar(db: Session, usuario_id: int) -> None:
    """Confirma a transação só se todo o histórico continuar apurável e os DARFs pagos não mudarem."""
    try:
        db.flush()
        db.expire_all()
        dados = carregar(db, usuario_id)
        resultado = apurar(dados.notas, dados.regras, dados.saldo_inicial)
        divergencias = verificar_pagamentos(
            resultado.meses, {c: p.valor_principal for c, p in dados.pagamentos.items()}
        )
        if divergencias:
            raise Conflito(
                "A alteração muda DARF já pago. Cancele o registro do pagamento ou desfaça a alteração.",
                divergencias=[
                    {
                        "competencia": d.competencia,
                        "valor_pago": str(q2(d.valor_pago)),
                        "valor_recalculado": str(q2(d.valor_recalculado)),
                        "diferenca": str(q2(d.diferenca)),
                    }
                    for d in divergencias
                ],
            )
    except Exception:
        db.rollback()
        raise
    db.commit()
