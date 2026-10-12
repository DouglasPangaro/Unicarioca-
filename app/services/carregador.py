from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.domain import modelos as dom
from app.domain.apuracao import apurar
from app.models import NotaCorretagem, PagamentoDarf, RegraFiscal, SaldoInicial


@dataclass
class DadosUsuario:
    notas: list[dom.Nota]
    regras: list[dom.Regra]
    saldo_inicial: dom.SaldoInicial | None
    pagamentos: dict[str, PagamentoDarf]


def para_nota(nota: NotaCorretagem) -> dom.Nota:
    return dom.Nota(
        data=nota.data_pregao,
        corretora=nota.corretora.nome,
        negocios=tuple(
            dom.Negocio(op.ativo.ticker, dom.TipoAtivo(op.ativo.tipo), dom.Lado(op.lado), op.quantidade, op.preco)
            for op in nota.operacoes
        ),
        custos=nota.custos_totais,
    )


def para_saldo(saldo: SaldoInicial) -> dom.SaldoInicial:
    return dom.SaldoInicial(
        data_referencia=saldo.data_referencia,
        prejuizo_day_trade=saldo.prejuizo_day_trade,
        prejuizo_comum=saldo.prejuizo_comum,
        imposto_pendente=saldo.imposto_pendente,
        posicoes=tuple(
            dom.PosicaoInicial(p.ativo.ticker, dom.TipoAtivo(p.ativo.tipo), p.quantidade, p.custo_total)
            for p in saldo.posicoes
        ),
    )


def carregar_regras(db: Session) -> list[dom.Regra]:
    return [
        dom.Regra(
            dom.Modalidade(r.modalidade), r.aliquota, r.aliquota_irrf, r.vigencia_inicio, r.vigencia_fim,
            r.limite_isencao_acoes,
        )
        for r in db.scalars(select(RegraFiscal))
    ]


def carregar(db: Session, usuario_id: int) -> DadosUsuario:
    notas = db.scalars(
        select(NotaCorretagem)
        .where(NotaCorretagem.usuario_id == usuario_id)
        .options(selectinload(NotaCorretagem.operacoes))
        .order_by(NotaCorretagem.data_pregao, NotaCorretagem.id)
    ).unique().all()
    saldo = db.scalar(
        select(SaldoInicial).where(SaldoInicial.usuario_id == usuario_id).options(selectinload(SaldoInicial.posicoes))
    )
    pagamentos = db.scalars(select(PagamentoDarf).where(PagamentoDarf.usuario_id == usuario_id))
    return DadosUsuario(
        notas=[para_nota(n) for n in notas],
        regras=carregar_regras(db),
        saldo_inicial=para_saldo(saldo) if saldo else None,
        pagamentos={p.competencia: p for p in pagamentos},
    )


def apurar_usuario(db: Session, usuario_id: int, ate: date | None = None) -> tuple[DadosUsuario, dom.ResultadoApuracao]:
    dados = carregar(db, usuario_id)
    return dados, apurar(dados.notas, dados.regras, dados.saldo_inicial, ate)
