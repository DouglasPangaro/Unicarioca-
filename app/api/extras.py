from fastapi import APIRouter, UploadFile
from sqlalchemy import select

from app.api.deps import Ano, DbDep, UsuarioDep
from app.core.config import get_settings
from app.core.erros import ArquivoGrande, Invalido
from app.models import RegraFiscal
from app.schemas.apuracao import RegraSaida, SimulacaoEntrada, SimulacaoSaida
from app.schemas.relatorios import RelatorioImportacao, RelatorioIRPFSaida
from app.services.analises import relatorio_irpf, simular
from app.services.importacao_service import importar_b3

router = APIRouter()


@router.get("/regras-fiscais", response_model=list[RegraSaida], tags=["Regras fiscais"])
def regras_fiscais(db: DbDep) -> list[RegraFiscal]:
    """Alíquotas e limites usados no cálculo; mudanças na lei entram por migration."""
    return list(db.scalars(select(RegraFiscal).order_by(RegraFiscal.modalidade, RegraFiscal.vigencia_inicio)))


@router.post("/importacoes/b3", response_model=RelatorioImportacao, tags=["Importação"])
def importar(arquivo: UploadFile, usuario: UsuarioDep, db: DbDep) -> RelatorioImportacao:
    """Importa a planilha .xlsx de negociação da Área do Investidor B3 (reimportar não duplica)."""
    limite = get_settings().upload_max_bytes
    conteudo = arquivo.file.read(limite + 1)
    if len(conteudo) > limite:
        raise ArquivoGrande(f"O arquivo excede {limite // (1024 * 1024)} MB.")
    if not (arquivo.filename or "").lower().endswith(".xlsx") or not conteudo.startswith(b"PK"):
        raise Invalido("Envie a planilha .xlsx exportada da Área do Investidor da B3.")
    return importar_b3(db, usuario.id, conteudo)


@router.post("/simulacoes/venda", response_model=SimulacaoSaida, tags=["Simulador"])
def simular_venda(dados: SimulacaoEntrada, usuario: UsuarioDep, db: DbDep) -> SimulacaoSaida:
    """Quanto muda o imposto do mês se eu vender agora? Nada é gravado."""
    return SimulacaoSaida.model_validate(simular(db, usuario.id, dados))


@router.get("/relatorios/irpf/{ano}", response_model=RelatorioIRPFSaida, tags=["Relatórios"])
def irpf(ano: Ano, usuario: UsuarioDep, db: DbDep) -> RelatorioIRPFSaida:
    """Renda Variável mês a mês, rendimentos isentos e Bens e Direitos para conferir a declaração."""
    return RelatorioIRPFSaida.model_validate(relatorio_irpf(db, usuario.id, ano))
