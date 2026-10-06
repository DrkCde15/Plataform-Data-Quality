# Revisão de Engenharia de Dados — data-quality-platform

**Data:** 2026-10-06
**Escopo:** repositório local (código, README, requirements, notebook, testes); sem execução contra produção
**Maturidade assumida:** Estágio 1 — biblioteca de qualidade de dados sem consumidores reais, 1 commit, sem CI; o objetivo é entregar o primeiro valor com poucas peças

## Veredito

É uma biblioteca de validação/profiling bem estruturada para o estágio 1: Pandera pinada e testada (25 testes passando), pipeline `raw → validated/rejected` funcional com contrato único de dicionário, e dependências documentadas com honestidade sobre o conflito do GX. O bruto é preservado, não há segredo vazado e reprocessar não duplica. Os 3 pontos que mais importam agora: um arquivo-fonte (`dtypes.py`) está fora do versionamento e quebra fresh clone; o score 99,4 com metade das linhas rejeitadas mostra que a métrica principal engana; e o README não é reproduzível do zero porque `data/raw` está vazio e ignorado pelo git.

## Mapa do ciclo de vida

| Etapa do ciclo | Onde está no repo | Tecnologia | Observação |
|---|---|---|---|
| Geração (fontes) | `notebooks/01_qualidade_dados.ipynb`, fixtures em `tests/test_validators.py:21-73` | Dados sintéticos em pandas | **Sem fontes reais** — esperado no estágio 1, mas sem dono/consumidor definido |
| Armazenamento | `data/raw\|validated\|rejected`, `reports/` | CSV local | Camadas bruto→validado existem; pipeline nunca sobrescreve `raw` (verificado) |
| Ingestão | `src/pipeline.py:70-140` (`carregar_arquivo`, `carregar_raw`) | Batch manual via CLI (CSV/Parquet/JSON) | Sem agendador; backfill = reexecutar o arquivo |
| Transformação | `src/validators/schema_validator.py`, `data_profiler.py`, `expectations.py` | Pandera 0.34.1 + GX legado opcional | Sem modelagem dimensional — não se aplica (é biblioteca de qualidade, não marts) |
| Disponibilização | `src/reporters/quality_report.py`, `alerts.py` | HTML/JSON + console/arquivo/email/webhook | Funciona; **sem consumidor real** (sem BI, sem KPI versionado) |

## Scorecard

| Dimensão | Nota (0–3) | Esperado no estágio | Resumo em uma linha |
|---|---|---|---|
| Geração | 1 | 1 | Sintético, sem contrato de fonte — ok para estágio 1 |
| Armazenamento | 2 | 1 | Bruto imutável, camadas claras; acima do esperado |
| Ingestão | 1 | 1 | CLI manual, idempotente; sem agendamento (aceitável) |
| Transformação | 1 | 2 | Pandera sólida, mas GX legado puxa para baixo |
| Disponibilização | 1 | 1 | Relatórios+alertas ok, sem consumidor para validar confiança |
| Segurança/privacidade | 1 | 1 | Sem vazamento; sem tratamento de PII nem env vars |
| Gerenciamento | 1 | 1 | README executável em partes; sem dicionário nem linhagem |
| DataOps | 1 | 1 | Testes existem, mas sem CI para rodá-los |
| Arquitetura | 2 | 1 | Simples, reversível, sem over-engineering |
| Orquestração | 1 | 1 | CLI parametrizado; sem DAG (aceitável no estágio 1) |
| Eng. de software | 2 | 1 | Tipagem, testes, deps pinadas; acima do esperado |

## Pontos fortes verificados

- Nenhum segredo no repo nem no histórico (`grep` por chaves/senhas literais: zero matches; `alerts.py:120` recebe `senha` só como parâmetro).
- Bruto preservado: pipeline só escreve em `validated/`, `rejected/` e `reports/` (`pipeline.py:381-393`).
- Reprocessamento idempotente: `to_csv` sobrescreve, sem `append`/`insert` em lugar nenhum (varredura `if_exists`/`insert into`: zero matches).
- Degradação graciosa do GX documentada no código e no `requirements.txt:11-20`.
- `__pycache__`/`.pytest_cache` fora do git (verificado via `git ls-files`).

## Achados

### DQ-01 `dtypes.py` fora do versionamento — Alta · Esforço P
- **Local:** `src/validators/dtypes.py` (ausente em `git ls-files`)
- **Status:** verificado
- **Evidência:** `schema_validator.py` e `data_profiler.py` importam `tipos_equivalentes`/`categoria_tipo` desse arquivo; fresh clone quebra com `ImportError`.
- **Por que importa:** inegociável nº 5 (outra pessoa rodar do zero) — o commit inicial está incompleto.
- **Como corrigir:** `git add src/validators/dtypes.py` e commitar; conferir `git status` antes de cada commit.

### DQ-02 Score enganoso: 99,4 com metade das linhas rejeitadas — Média · Esforço P
- **Local:** `src/validators/data_profiler.py:200-230`
- **Status:** verificado
- **Evidência:** pesos 40/30/30 e penalidades (`-5`, `-2`) sem justificativa; o score mede colunas, não linhas — execução real anterior deu score 99,4 com 3/6 linhas em `rejected`.
- **Por que importa:** erro silencioso clássico — métrica verde com dado ruim, sem alarme (qualidade como confiança, cap. 9).
- **Como corrigir:** incluir taxa de aprovação de linhas no score ou exibir os dois números lado a lado no relatório; documentar a fórmula no README.

### DQ-03 Reprovação do GX não quarentena linhas — Média · Esforço M
- **Local:** `src/pipeline.py:256-268`
- **Status:** verificado
- **Evidência:** `dividir_validados_rejeitados` usa só índices da Pandera; falha GX gera alerta (via `validacoes`), mas as linhas vão para `validated/` mesmo assim.
- **Por que importa:** quarentena parcial — o consumidor do CSV validado não vê o alarme.
- **Como corrigir:** documentar que `validated/` = "aprovado Pandera" ou mapear expectativas GX críticas para índices de linha.

### DQ-04 README não roda do zero: `data/raw` vazio e ignorado — Média · Esforço P
- **Local:** `.gitignore` (linha `data/`), `src/pipeline.py` (`executar_raw_dir` retorna `[]` → `main` retorna 1)
- **Status:** verificado
- **Evidência:** `data/raw` vazio; comandos `python -m src.pipeline ...` do README falham sem arquivo de entrada.
- **Por que importa:** inegociável nº 5.
- **Como corrigir:** afrouxar o ignore (`data/*` + `!data/raw/.gitkeep`, ou versionar 1 CSV pequeno ~20 linhas) e apontar o README para ele.

### DQ-05 GX preso à API 0.15–0.18 — Alta · Esforço M
- **Local:** `src/validators/expectations.py:10-17,144-146`
- **Status:** verificado
- **Evidência:** imports `PandasExecutionEngine`, `Validator(batches=...)` removidos no GX 1.x; instalar `great-expectations==0.18.22` no Python 3.14 faz downgrade para `numpy<2`/pandas 2.x, quebrando o resto.
- **Por que importa:** dependência que corrompe o ambiente ao instalar (escolha de tecnologia vs. custo, cap. 4).
- **Como corrigir:** decidir — (a) remover GX e ficar Pandera-only, ou (b) congelar Python 3.11–3.13 e migrar para a API GX 1.x. Não deixar o meio-termo.

### DQ-06 Sem CI: 25 testes que ninguém roda sozinho — Média · Esforço P
- **Local:** ausência de `.github/` (verificado no inventário)
- **Status:** verificado (ausência)
- **Evidência:** `tests/test_validators.py` cobre schemas, profiler, reports e alertas, mas só roda manualmente.
- **Por que importa:** DataOps no estágio 1 = ao menos lint+testes automáticos (cap. 2).
- **Como corrigir:** `.github/workflows/ci.yml` com `pip install -r requirements.txt` (sem GX no 3.14) + `pytest`.

### DQ-07 PII sem tratamento (nome, email, telefone) — Baixa · Esforço P
- **Local:** `src/validators/schema_validator.py:ClienteSchema`, `data_profiler.py:165-168` (top-10 valores expostos no perfil)
- **Status:** verificado
- **Evidência:** nenhum `mask/anonym/pseudonim` no código; relatórios e `failure_cases` carregam valores crus. Dados atuais são sintéticos (sem dano real).
- **Por que importa:** LGPD (acréscimo da skill) — quando chegar dado real, o vazamento já estará arquitetado.
- **Como corrigir:** flag `incluir_amostras=False` no profiler/relatórios + seção de privacidade no README quando houver dado real.

### DQ-08 Detalhes de endurecimento — Baixa · Esforço P
- **Local:** `src/reporters/alerts.py:120-161`; `quality_report.py:36`, `alerts.py:58`, `pipeline.py:252` (`datetime.now()` naive)
- **Status:** verificado
- **Evidência:** senha SMTP só via parâmetro (sem `os.getenv`); timestamps sem fuso.
- **Por que importa:** segurança por configuração (cap. 10); fuso implícito hoje é inofensivo (sem agendador nem backfill por data lógica).
- **Como corrigir:** `SMTP_PASSWORD=os.getenv(...)`; trocar `now()` por `now(timezone.utc)` nos metadados.

### DQ-09 Notebook demonstração que nunca falha — Info · Esforço P
- **Local:** `notebooks/01_qualidade_dados.ipynb` (`sys.path.insert`, `display`, geradores de dados limpos)
- **Status:** verificado
- **Evidência:** gera 100 clientes/200 pedidos sempre válidos; `display()` exige Jupyter; `sys.path` em vez de pacote instalável.
- **Por que importa:** demo de qualidade que não mostra falha ensina pouco; não é falha de pipeline.
- **Como corrigir:** injetar ~5% de sujeira proposital e mostrar o split validated/rejected.

## Roadmap

1. **Agora** — DQ-01 (commitar `dtypes.py`), DQ-04 (CSV exemplo + `.gitignore`), DQ-06 (CI mínimo). Todos P, desbloqueiam colaboração.
2. **Em seguida** — DQ-02 (score honesto), DQ-05 (decisão GX), DQ-03 (semântica do `validated/`), DQ-07/08 (endurecimento).
3. **Deliberadamente adiado** — Airflow/Dagster, Parquet particionado, catálogo/linhagem, Spark, data mesh: over-engineering para o estágio 1 sem volume nem consumidor (princípios 3 e 7 de arquitetura, caps. 3–4).

## O que esta análise não cobriu

Produção e volumes reais, custos, permissões na nuvem, qualidade real dos dados (só sintéticos aqui), e o que vive fora do repositório (eventual BI, console de nuvem, outro repo). Comandos executados foram só leitura; nada foi instalado nem alterado durante a revisão.

## Perguntas em aberto

1. Há previsão de dado real (com PII) ou segue sintético/portfólio? (muda DQ-07 de Baixa para Crítica)
2. O GX deve viver ou morrer neste projeto? (define DQ-05)
3. Quem consome `validated/` e qual decisão depende dele? (define se DQ-03 é Média ou Alta)
