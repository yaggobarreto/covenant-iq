<div align="center">

# CovenantIQ

**Inteligência de compliance de covenants e de carteira de crédito, com IA.**
Lê contratos de crédito com um LLM, acompanha covenants financeiros em relação aos demonstrativos do tomador ao longo do tempo, e responde perguntas sobre a carteira em linguagem natural — sempre com base nos documentos originais.

[![Tests](https://img.shields.io/badge/testes-45%20passing-1f9d76)](#como-rodar)
[![Python](https://img.shields.io/badge/python-3.12-1e2a44)](#stack-t%C3%A9cnica)
[![LangChain](https://img.shields.io/badge/orquestra%C3%A7%C3%A3o%20de%20LLM-LangChain-1f9d76)](#o-pipeline-de-extra%C3%A7%C3%A3o)
[![License](https://img.shields.io/badge/licen%C3%A7a-MIT-4c5266)](#licen%C3%A7a)

[Whitepaper (PDF)](docs/whitepaper.pdf) · [Como rodar](#como-rodar) · [Arquitetura](#arquitetura) · [Roteiro](#roteiro)

</div>

> **Projeto de portfólio, com dados 100% sintéticos.** Todo número, nome de tomador e documento citado neste repositório foi gerado para fins de demonstração. O CovenantIQ não tem nenhuma relação com, e não processa dados de, nenhuma instituição financeira, credor ou cliente real.

> **Estado real da implementação:** a API (FastAPI), as duas chains de extração do LangChain, o motor de compliance, o endpoint de chat (RAG) e o banco de dados são **código real, com 45 testes automatizados passando** — não é só a proposta descrita no whitepaper. O que ainda **não** existe: o painel em React (as imagens abaixo são mockups estáticos, não telas de uma aplicação rodando), o processamento assíncrono via Celery/Redis (a API roda de forma síncrona nesta versão) e o deploy em produção com Postgres/pgvector (a stack padrão é SQLite, e o código já é compatível com Postgres — ver [Stack técnica](#stack-técnica)).

<img src="docs/dashboard.png" alt="Painel de carteira do CovenantIQ — lista de contratos com status de covenant e gráfico de tendência de folga" width="100%">

---

## O problema

Todo contrato de crédito que um credor assina — um empréstimo a prazo, uma debênture, uma linha rotativa — vem com **covenants financeiros**: limites contratuais que o tomador precisa manter, como uma alavancagem máxima (Dívida Líquida/EBITDA), um saldo mínimo de liquidez, ou um índice mínimo de cobertura do serviço da dívida.

Na maioria dos fundos e carteiras de crédito, checar esses covenants ainda é manual: um analista relê o contrato pra lembrar a definição e o limite exatos, depois cruza isso na mão com o demonstrativo financeiro que o tomador mandou naquele trimestre. Numa carteira de cinquenta ou cem contratos, isso não escala — e o resultado é que a quebra de covenant costuma ser percebida **depois** do fato, em vez de aparecer como uma tendência no momento em que a folga do tomador começa a encolher.

O CovenantIQ é uma prova de conceito pra inverter essa lógica: ler o documento jurídico uma vez com um LLM pra obter uma definição estruturada e consultável de cada covenant, e então alimentar essa estrutura continuamente com os dados financeiros, pra que quebras — e sinais de alerta antecipado — apareçam sozinhos.

## O que o sistema faz

| | |
|---|---|
| **Extrair** | Envie o PDF do contrato de crédito. Uma chain de extração do LangChain identifica as partes, o principal, a taxa, o vencimento e cada covenant financeiro como uma definição estruturada e tipada (métrica, operador, limite, frequência de teste, prazo de cura). |
| **Monitorar** | A cada demonstrativo financeiro que chega, uma segunda extração pega os itens contábeis que cada covenant precisa, calcula o índice real e grava um retrato de conformidade datado — não só aprovado/reprovado, mas quanta folga ainda resta. |
| **Visualizar** | Um painel consolida o status de covenant de cada contrato numa visão só de carteira: o que está em dia, o que está em alerta, o que quebrou, e de quem a folga vem encolhendo trimestre após trimestre. |
| **Perguntar** | Um chat com busca aumentada (RAG) responde perguntas como *"quais contratos têm um covenant de alavancagem com menos de 10% de folga?"* — sempre com base no texto real do contrato, com a citação da página de origem. |

## Arquitetura

Duas entradas de dados alimentam o mesmo repositório: o contrato (lido uma vez, muda raramente) e os demonstrativos financeiros (lidos a cada período). Tanto o motor de compliance quanto o chat da carteira leem desse mesmo repositório.

<img src="docs/architecture.png" alt="Diagrama de arquitetura do CovenantIQ: ingestão do contrato e dos demonstrativos financeiros por chains de extração do LangChain, gravação no PostgreSQL e num repositório vetorial (pgvector), alimentando o motor de compliance, o painel, os alertas e o chat com RAG" width="100%">

## O pipeline de extração

A parte mais difícil deste projeto não é chamar um LLM — é transformar a definição de um covenant, escrita em texto jurídico denso, em algo que um programa consiga testar depois.

**Saída estruturada, não texto livre.** Toda chamada de extração usa o `with_structured_output()` do LangChain, vinculado a um modelo Pydantic, então a resposta é validada contra um schema antes de chegar ao banco — um covenant malformado (sem limite, com operador ambíguo) falha de forma clara já na extração, não três meses depois, quando o motor tenta testá-lo.

```python
class Covenant(BaseModel):
    name: str
    metric: Literal["net_debt_ebitda", "dscr", "min_liquidity", "min_equity", "current_ratio"]
    operator: Literal["lte", "gte"]
    threshold: float
    test_frequency: Literal["quarterly", "annual"]
    cure_period_days: int | None
    source_clause: str          # cláusula literal, para auditoria e citações
    source_page: int

extraction_chain = prompt_template | llm.with_structured_output(CovenantExtractionResult)
result = extraction_chain.invoke({"document_text": agreement_text})
```

Cada covenant extraído carrega uma `source_page` e a cláusula literal de onde veio — a mesma âncora que as citações do chat usam depois (veja o [whitepaper](docs/whitepaper.pdf), §4 e §7, para o desenho completo de extração e busca).

## Como rodar

Requer Python 3.12. Os testes **não** precisam de chave de API — a chamada ao LLM é injetável, e a suíte usa um modelo falso em todos os pontos onde isso importa (veja `tests/fakes.py`).

```bash
python -m venv .venv
.venv/Scripts/activate          # no Windows; source .venv/bin/activate no Linux/Mac
pip install -e ".[dev]"

pytest                          # 45 testes, roda em menos de 1s, sem chave de API
```

Para rodar a API de verdade (precisa de `OPENAI_API_KEY`):

```bash
cp .env.example .env            # e preencha OPENAI_API_KEY
uvicorn app.main:app --reload
# docs interativas em http://localhost:8000/docs
```

Para ver o pipeline completo (extração de covenants + extração financeira + motor de compliance) rodando contra um contrato sintético de exemplo, de ponta a ponta, com a API real:

```bash
python scripts/demo.py
```

Para rodar com PostgreSQL + pgvector em vez de SQLite:

```bash
docker compose up
```

## Stack técnica

| Camada | Escolha | Status |
|---|---|---|
| API | FastAPI | ✅ implementado, testado |
| Orquestração de LLM | LangChain (chains de extração com saída estruturada, chain de busca para o RAG) | ✅ implementado, testado |
| Motor de compliance | Python puro — sem LLM, sem I/O | ✅ implementado, cobertura de teste exaustiva |
| Banco de dados | SQLAlchemy — SQLite por padrão (dev/testes), PostgreSQL + pgvector suportado via `DATABASE_URL` | ✅ SQLite funcionando · Postgres desenhado, não testado em produção |
| Busca vetorial | Repositório em memória com similaridade por cosseno, mesma interface que um adaptador pgvector usaria | ✅ implementado, testado |
| Processamento assíncrono | Celery + Redis | 📋 desenhado no whitepaper, não implementado — a API roda de forma síncrona |
| Frontend | React + TypeScript | 📋 só existe como mockup estático (`docs/dashboard.png`) |
| Implantação | Docker Compose (Postgres + API) | ✅ implementado |

## Estrutura do repositório

```
covenant-iq/
├── app/
│   ├── main.py              app FastAPI
│   ├── config.py            configurações (variáveis de ambiente)
│   ├── db.py, models.py     SQLAlchemy
│   ├── schemas.py           schemas da API (Pydantic)
│   ├── extraction/          chains do LangChain (contrato + demonstrativos)
│   ├── engine/               motor de compliance (Python puro, sem LLM)
│   ├── retrieval/            busca vetorial + chain de RAG do chat
│   └── routers/               rotas da API
├── data/synthetic/          contrato e demonstrativo sintéticos de exemplo
├── scripts/demo.py           pipeline completo, ponta a ponta, com a API real
├── tests/                     45 testes — motor de compliance, chains, API
├── docs/
│   ├── whitepaper.pdf         whitepaper técnico completo
│   ├── architecture.png
│   └── dashboard.png
├── docker-compose.yml         Postgres + pgvector + API
├── Dockerfile
├── .env.example
└── README.md
```

## Roteiro

- [x] **v0.1 — Pipeline principal:** upload do contrato → extração de covenants → revisão manual (endpoint de aprovação) → motor de compliance. Só com dados sintéticos.
- [x] **v0.2 — Chat:** chain de busca (RAG) sobre a carteira extraída, com citações — endpoint funcionando, com busca vetorial em memória.
- [ ] **Painel de verdade:** ligar o mockup React a essas rotas (hoje `docs/dashboard.png` é só uma imagem estática).
- [ ] **Processamento assíncrono:** mover a extração para filas (Celery + Redis), tirando-a do caminho síncrono da requisição.
- [ ] **v0.3 — Alertas:** limites de alerta antecipado configuráveis, envio por e-mail/webhook.
- [ ] **v0.4 — Contratos com múltiplos documentos:** aditivos e cartas-side que alteram um covenant original.
- [ ] **Ideia futura:** pontuação de confiança na extração, para a fila de revisão humana priorizar o que tem mais chance de estar errado.

O detalhamento completo do projeto — modelo de dados, considerações de segurança e governança, e o raciocínio por trás de cada decisão — está no [whitepaper técnico](docs/whitepaper.pdf).

## Licença

MIT — veja [`LICENSE`](LICENSE).

---

<div align="center">
<sub>Construído como projeto de portfólio para demonstrar engenharia aplicada de LLM/LangChain em inteligência documental para o mercado financeiro. Somente dados sintéticos.</sub>
</div>
