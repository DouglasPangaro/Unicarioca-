import hashlib
from collections import Counter, defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.importers.b3 import LinhaB3, ler_planilha, normalizar_texto
from app.models import Ativo, Corretora, NotaCorretagem, Operacao, OrigemNota
from app.repositories.consultas import buscar_ativo, criar_ativo_automatico
from app.schemas.relatorios import LinhaIgnorada, RelatorioImportacao
from app.services.escrita import validar_e_confirmar


def _chave(usuario_id: int, linha: LinhaB3, ocorrencia: int) -> str:
    # a ocorrência diferencia negócios idênticos no mesmo dia, que são legítimos
    texto = "|".join(
        map(str, (usuario_id, linha.data, normalizar_texto(linha.instituicao), linha.ticker, linha.lado,
                  linha.quantidade, linha.preco, ocorrencia))
    )
    return hashlib.sha256(texto.encode()).hexdigest()


def importar_b3(db: Session, usuario_id: int, conteudo: bytes) -> RelatorioImportacao:
    leitura = ler_planilha(conteudo, get_settings().importacao_max_linhas)

    ativos: dict[str, Ativo | None] = {}
    pendencias: set[str] = set()
    ocorrencias: Counter = Counter()
    candidatas: list[tuple[LinhaB3, str]] = []
    for linha in leitura.linhas:
        if linha.ticker not in ativos:
            ativos[linha.ticker] = buscar_ativo(db, usuario_id, linha.ticker) or criar_ativo_automatico(
                db, usuario_id, linha.ticker
            )
        if ativos[linha.ticker] is None:
            pendencias.add(linha.ticker)
            continue
        identidade = (linha.data, normalizar_texto(linha.instituicao), linha.ticker, linha.lado,
                      linha.quantidade, linha.preco)
        ocorrencias[identidade] += 1
        candidatas.append((linha, _chave(usuario_id, linha, ocorrencias[identidade])))

    existentes = set(
        db.scalars(
            select(Operacao.chave_importacao)
            .join(NotaCorretagem)
            .where(NotaCorretagem.usuario_id == usuario_id, Operacao.chave_importacao.is_not(None))
        )
    )
    novas = [(linha, chave) for linha, chave in candidatas if chave not in existentes]

    corretoras = {
        normalizar_texto(c.nome): c for c in db.scalars(select(Corretora).where(Corretora.usuario_id == usuario_id))
    }
    grupos: dict[tuple, list[tuple[LinhaB3, str]]] = defaultdict(list)
    for linha, chave in novas:
        grupos[(linha.data, normalizar_texto(linha.instituicao))].append((linha, chave))

    for (data, nome_normalizado), itens in sorted(grupos.items()):
        corretora = corretoras.get(nome_normalizado)
        if corretora is None:
            corretora = Corretora(usuario_id=usuario_id, nome=itens[0][0].instituicao)
            db.add(corretora)
            corretoras[nome_normalizado] = corretora
        db.add(
            NotaCorretagem(
                usuario_id=usuario_id,
                corretora=corretora,
                data_pregao=data,
                origem=OrigemNota.IMPORTACAO_B3,
                custos_pendentes=True,
                operacoes=[
                    Operacao(
                        ativo=ativos[linha.ticker],
                        lado=linha.lado,
                        quantidade=linha.quantidade,
                        preco=linha.preco,
                        chave_importacao=chave,
                    )
                    for linha, chave in itens
                ],
            )
        )

    validar_e_confirmar(db, usuario_id)
    return RelatorioImportacao(
        notas_criadas=len(grupos),
        operacoes_importadas=len(novas),
        duplicadas_ignoradas=len(candidatas) - len(novas),
        ignoradas=[LinhaIgnorada(linha=n, motivo=m) for n, m in leitura.ignoradas],
        pendencias=sorted(pendencias),
    )
