from io import BytesIO

from openpyxl import Workbook

from app.core.config import get_settings
from tests.api.util import criar_corretora, criar_nota, op

CABECALHO = [
    "Data do Negócio", "Tipo de Movimentação", "Mercado", "Prazo/Vencimento", "Instituição",
    "Código de Negociação", "Quantidade", "Preço", "Valor",
]
XP = "XP INVESTIMENTOS CCTVM S/A"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def planilha(*linhas, cabecalho=CABECALHO) -> bytes:
    pasta = Workbook()
    aba = pasta.active
    aba.append(cabecalho)
    for linha in linhas:
        aba.append(linha)
    buffer = BytesIO()
    pasta.save(buffer)
    return buffer.getvalue()


def enviar(client, auth, conteudo: bytes, nome: str = "negociacao.xlsx"):
    return client.post("/importacoes/b3", files={"arquivo": (nome, conteudo, XLSX)}, headers=auth)


def _saldo_cenario_d(client, auth) -> int:
    corpo = {
        "data_referencia": "2026-05-31",
        "posicoes": [
            {"ticker": "ITSA4", "quantidade": 1000, "custo_total": "10000.00"},
            {"ticker": "BBAS3", "quantidade": 500, "custo_total": "10000.00"},
        ],
    }
    assert client.put("/saldo-inicial", json=corpo, headers=auth).status_code == 200
    return criar_corretora(client, auth)


def test_importacao_b3_classifica_e_e_idempotente(client, auth):
    conteudo = planilha(
        ["12/01/2026", "Compra", "Mercado à Vista", "-", XP, "PETR4", 100, 30.0, 3000.0],
        ["12/01/2026", "Venda", "Mercado à Vista", "-", XP, "PETR4", 100, 29.0, 2900.0],
        ["10/02/2026", "Compra", "Mercado Fracionário", "-", XP, "VALE3F", 100, 60.0, 6000.0],
        ["10/02/2026", "Venda", "Mercado à Vista", "-", XP, "VALE3", 100, 64.0, 6400.0],
        ["11/02/2026", "Compra", "Opção de Compra", "-", XP, "PETRB40", 100, 1.0, 100.0],
        ["12/02/2026", "Compra", "Mercado à Vista", "-", XP, "BOVA11", 10, 100.0, 1000.0],
    )
    relatorio = enviar(client, auth, conteudo).json()
    assert (relatorio["notas_criadas"], relatorio["operacoes_importadas"], relatorio["duplicadas_ignoradas"]) == (2, 4, 0)
    assert relatorio["ignoradas"] == [{"linha": 6, "motivo": "Mercado não suportado: Opção de Compra"}]
    assert relatorio["pendencias"] == ["BOVA11"]

    assert client.get("/apuracoes/2026/2", headers=auth).json()["darf"]["valor"] == "56.00"
    notas = client.get("/notas", headers=auth).json()
    assert all(n["custos_pendentes"] and n["origem"] == "IMPORTACAO_B3" for n in notas)
    assert {n["corretora_nome"] for n in notas} == {XP}

    repetida = enviar(client, auth, conteudo).json()
    assert (repetida["operacoes_importadas"], repetida["duplicadas_ignoradas"]) == (0, 4)


def test_importacao_rejeita_planilha_sem_colunas(client, auth):
    resposta = enviar(client, auth, planilha(["12/01/2026", "Compra"], cabecalho=["Data do Negócio", "Tipo de Movimentação"]))
    assert resposta.status_code == 422
    assert "Código de Negociação" in resposta.json()["colunas_ausentes"]


def test_importacao_rejeita_arquivo_invalido(client, auth):
    assert enviar(client, auth, b"nao e planilha", "negociacao.xlsx").status_code == 422
    assert enviar(client, auth, planilha(), "negociacao.csv").status_code == 422
    assert enviar(client, auth, b"PK\x03\x04lixo", "negociacao.xlsx").status_code == 422


def test_importacao_rejeita_arquivo_grande(client, auth, monkeypatch):
    monkeypatch.setattr(get_settings(), "upload_max_bytes", 100)
    assert enviar(client, auth, planilha()).status_code == 413


def test_saldo_inicial_e_simulador_avisa_perda_de_isencao(client, auth):
    corretora_id = _saldo_cenario_d(client, auth)
    criar_nota(client, auth, corretora_id, "2026-06-10", op("ITSA4", "V", 1000, "11.00"))
    corpo = {"ticker": "BBAS3", "quantidade": 500, "preco": "22.00", "corretora_id": corretora_id, "data": "2026-06-15"}
    simulacao = client.post("/simulacoes/venda", json=corpo, headers=auth).json()
    assert (simulacao["modalidade"], simulacao["perde_isencao"]) == ("COMUM", True)
    assert (simulacao["darf_antes"], simulacao["darf_depois"], simulacao["diferenca_darf"]) == ("0.00", "298.90", "298.90")
    assert len(client.get("/notas", headers=auth).json()) == 1


def test_simulador_valida_ativo_e_corretora(client, auth):
    corretora_id = criar_corretora(client, auth)
    corpo = {"ticker": "PETR4", "quantidade": 1, "preco": "30.00", "corretora_id": corretora_id}
    assert client.post("/simulacoes/venda", json=corpo, headers=auth).status_code == 422
    assert client.post("/simulacoes/venda", json={**corpo, "corretora_id": 999}, headers=auth).status_code == 422


def test_saldo_inicial_crud_e_validacoes(client, auth):
    corretora_id = _saldo_cenario_d(client, auth)
    saldo = client.get("/saldo-inicial", headers=auth).json()
    assert [(p["ticker"], p["custo_total"]) for p in saldo["posicoes"]] == [("ITSA4", "10000.00"), ("BBAS3", "10000.00")]

    corpo = {"data_referencia": "2026-05-31", "posicoes": [{"ticker": "ITSA4", "quantidade": 900, "custo_total": "9000.00"}]}
    assert client.put("/saldo-inicial", json=corpo, headers=auth).json()["posicoes"][0]["quantidade"] == 900
    assert client.put("/saldo-inicial", json={"data_referencia": "2026-05-30"}, headers=auth).status_code == 422

    criar_nota(client, auth, corretora_id, "2026-06-10", op("ITSA4", "V", 900, "11.00"))
    assert client.delete("/saldo-inicial", headers=auth).status_code == 422
    assert client.put("/saldo-inicial", json={"data_referencia": "2026-06-30"}, headers=auth).status_code == 422


def test_relatorio_irpf(client, auth):
    corretora_id = criar_corretora(client, auth)
    criar_nota(client, auth, corretora_id, "2026-05-11", op("PETR4", "C", 300, "38.00"), op("PETR4", "V", 200, "38.50"))
    relatorio = client.get("/relatorios/irpf/2026", headers=auth).json()
    maio = relatorio["renda_variavel"][4]
    assert (maio["mes"], maio["day_trade"]["imposto"], maio["imposto_a_pagar"]) == (5, "20.00", "19.00")
    (bem,) = relatorio["bens_e_direitos"]
    assert (bem["grupo"], bem["codigo"], bem["situacao_anterior"], bem["situacao_atual"]) == ("03", "01", "0.00", "3800.00")
    assert bem["discriminacao"] == "100 ações PETR4, custo médio de R$ 38,00."


def test_regras_fiscais_e_health(client):
    regras = client.get("/regras-fiscais").json()
    assert [(r["modalidade"], r["aliquota"], r["aliquota_irrf"]) for r in regras] == [
        ("COMUM", "0.15", "0.00005"), ("DAY_TRADE", "0.2", "0.01"),
    ]
    assert client.get("/health").json() == {"status": "ok"}
