# API de Tributação de Day Trade (B3)

API REST em FastAPI para lançar notas de corretagem (CRUD) e calcular automaticamente o imposto de renda sobre ações e ETFs negociados na B3: separa **day trade** de **operação comum**, compensa prejuízos, aplica a isenção de R$ 20 mil, desconta o IRRF e gera o **DARF** (código 6015) com vencimento.

## Como rodar (Windows / PowerShell)

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
# gere a chave e cole em SECRET_KEY no .env
.venv\Scripts\python.exe -c "import secrets; print(secrets.token_hex(32))"
.venv\Scripts\alembic.exe upgrade head
.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Abra <http://127.0.0.1:8000/docs>, registre um usuário em `/auth/registrar` e clique em **Authorize** (e-mail no campo *username*).

Dados de demonstração (cenários abaixo): `.venv\Scripts\python.exe -m scripts.seed_demo` — login `demo@exemplo.com`, senha `demo-senha-123`.

**Docker com PostgreSQL:** com o `.env` preenchido, `docker compose up --build`. Para usar outra porta, defina `API_PORTA` no `.env`. Em rede corporativa que inspeciona HTTPS (ex.: Netskope), coloque o certificado `.crt` da empresa na pasta `certificados/` antes do build.

**Testes:** `.venv\Scripts\python.exe -m pytest --cov=app`

## Rotas

| Recurso | Rotas |
|---|---|
| Autenticação | `POST /auth/registrar`, `POST /auth/token`, `GET /usuarios/me` |
| Cadastros | CRUD `/corretoras`, CRUD `/ativos` |
| Notas e operações | CRUD `/notas`, `POST/PUT/DELETE /notas/{id}/operacoes[/{op_id}]` |
| Saldo inicial | `GET/PUT/DELETE /saldo-inicial` (posições e prejuízos de antes do sistema) |
| Apuração | `GET /apuracoes/{ano}/{mes}` (memória de cálculo), `GET /apuracoes/{ano}`, `GET /carteira` |
| DARF | `GET /darfs`, `GET /darfs/{competencia}/atualizado`, `POST/DELETE /darfs/{competencia}/pagamento` |
| Extras | `POST /importacoes/b3`, `POST /simulacoes/venda`, `GET /relatorios/irpf/{ano}`, `GET /regras-fiscais` |

## Regras de cálculo

- **Day trade:** compra e venda do mesmo ativo, no mesmo dia e na mesma corretora; a quantidade é o menor entre comprado e vendido. O excedente vira operação comum.
- **Custos** da nota (corretagem, emolumentos, taxas, ISS) são rateados pelo valor de cada operação.
- **Preço médio** da carteira inclui custos e consolida as corretoras. No mesmo dia, compras comuns entram antes das vendas.
- **Alíquotas:** 20% day trade e 15% operação comum, lidas da tabela `regras_fiscais` (mudança na lei = nova migration).
- **Prejuízos:** day trade só abate day trade; comum só abate comum; sem prazo.
- **Isenção:** vendas comuns de ações até R$ 20 mil no mês. O lucro isento não consome prejuízo; ETF e day trade nunca são isentos.
- **IRRF:** 1% do lucro de day trade do dia por corretora; 0,005% das vendas comuns por corretora no mês (dispensado até R$ 1,00). A sobra passa para os meses seguintes do mesmo ano.
- **DARF:** soma day trade + comum; abaixo de R$ 10,00 acumula para o mês seguinte; vence no último dia útil do mês seguinte.
- **Atraso:** multa de 0,33% ao dia (máx. 20%) e juros pela Selic acumulada (série SGS 4390 do Banco Central) + 1% no mês do pagamento.
- **Consistência:** a apuração é recalculada a cada escrita. Venda sem posição → 422. Alteração que muda DARF já pago → 409 com a diferença.

Base legal: IN RFB nº 1.585/2015; Lei nº 11.033/2004; Lei nº 9.430/1996, art. 61. Confira as alíquotas vigentes no site da Receita.

## Cenários de referência (testes automatizados)

| Cenário | Resultado esperado |
|---|---|
| Jan: day trade −100; fev: +400 (IRRF 4,00) | DARF de fev = 56,00, vence 31/03/2026 |
| Mar: +30; abr: +30 | 5,70 pendente em mar; DARF 11,40 em abr |
| Compra 300 / vende 200 PETR4 no dia; depois vende 100 | day trade +100, venda isenta +200, DARF 19,00 |
| Vendas comuns de 22 mil com lucro de 2 mil | 300,00 − IRRF 1,10 = DARF 298,90 |
| Compra na corretora X, venda na Y no mesmo dia | operação comum, não day trade |
| DARF de 56,00 pago 45 dias após o vencimento (Selic 1%) | multa 8,32 + juros 1,12 = 65,44 |

## Estrutura

```
app/
├── domain/        regras de cálculo puras (sem banco nem FastAPI)
├── models/        tabelas SQLAlchemy
├── schemas/       entrada e saída (Pydantic)
├── repositories/  consultas sempre filtradas pelo usuário
├── services/      orquestração: carrega dados, chama o domínio, valida e grava
├── importers/     leitura da planilha da B3
├── integrations/  Selic do Banco Central
└── api/           rotas
alembic/           migrations (esquema + regras fiscais)
tests/             domínio, API e infraestrutura
```

## Limitações

Fora do escopo: FIIs, opções, termo, futuros, aluguel de ações, venda a descoberto no swing, eventos corporativos (desdobramento, grupamento, bonificação) e subscrições. O IRRF é calculado pelas regras, não lido da nota. O relatório do IRPF é material de conferência e não substitui o programa da Receita.
