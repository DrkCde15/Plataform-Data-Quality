# 📊 Plataforma de Qualidade de Dados

Plataforma completa para validação, profiling e monitoramento da qualidade de dados utilizando Python, Pandera e Pandas.

## 🎯 Objetivo

Automatizar a verificação da qualidade de dados em pipelines de dados, garantindo:
- Conformidade com schemas definidos
- Validação de regras de negócio
- Detecção de anomalias e outliers
- Geração de relatórios de qualidade
- Alertas automáticos em falhas

## 📁 Estrutura do Projeto

```
data-quality-platform/
├── README.md
├── requirements.txt
├── src/
│   ├── __init__.py
│   ├── pipeline.py              # Pipeline raw -> validated/rejected (orquestrador)
│   ├── validators/
│   │   ├── schema_validator.py    # Validação com Pandera
│   │   ├── dtypes.py              # Helpers canônicos de tipos (pandas 2/3)
│   │   └── data_profiler.py       # Profiling de dados
│   └── reporters/
│       ├── quality_report.py      # Relatórios HTML/JSON
│       └── alerts.py              # Sistema de alertas
├── data/
│   ├── raw/                     # entrada (CSV/Parquet/JSON)
│   ├── validated/               # saída: linhas aprovadas
│   └── rejected/                # saída: linhas reprovadas + *_erros.json
├── dags/
│   └── data_quality.py          # DAG mínima (Airflow 2.x, gate diário)
├── reports/                     # HTML/JSON gerados pelo pipeline (gitignored)
├── notebooks/
│   └── 01_qualidade_dados.ipynb   # Análise interativa
└── tests/
    ├── __init__.py
    └── test_validators.py         # Testes unitários
```

## 🚀 Instalação

```bash
# Criar ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Instalar dependências
pip install -r requirements.txt
```

## 💻 Uso

> Caminho recomendado: use o **pipeline** (`src/pipeline.py`). Ele normaliza
> o dicionário intermediário para o formato único entendido por
> `QualityReport` e `AlertSystem`, e já separa `validated`/`rejected`.
> O uso individual dos módulos abaixo também funciona, mas exige montar
> o dicionário no formato do contrato (ver `normalizar_resultado()`).

### Pipeline (raw -> validated/rejected)

```bash
# exemplo versionado (20 linhas, com 3 falhas propositais)
python -m src.pipeline --arquivo data/raw/clientes_exemplo.csv --schema cliente --chave id_cliente
python -m src.pipeline --base . --schema cliente
```

> Semântica de quarentena: `validated/` = "aprovado Pandera".
> Linhas reprovadas vão para `rejected/` + sidecar `<dataset>_erros.json`.

```python
from pathlib import Path
from src.pipeline import DataQualityPipeline

pipe = DataQualityPipeline(base_dir=".", colunas_chave=["id_cliente"])
res = pipe.executar_arquivo("data/raw/clientes_exemplo.csv", nome_schema="cliente")
print(res["pandera_valido"], res["relatorio_html"], len(res["alertas"]))
```

### Validação com Pandera

```python
from src.validators.schema_validator import SchemaValidator

validator = SchemaValidator()
# nome_schema: "cliente" | "pedido" | "produto" (opcional — infere pelas colunas)
resultado = validator.validar_dataframe(df, "cliente")
print(resultado)  # ResultadoValidacao(valido=..., erros=[...], indices_invalidos=[...])
print(resultado.erros)
print(validator.listar_schemas())
```

### Profiling de Dados

```python
from src.validators.data_profiler import DataProfiler

profiler = DataProfiler()
perfil = profiler.perfilar(df, nome="clientes")
resumo = profiler.gerar_resumo(perfil)
print(resumo["score_qualidade"], resumo["problemas_encontrados"])
```

### Geração de Relatórios

```python
from src.pipeline import normalizar_resultado
from src.reporters.quality_report import QualityReport

# `resultados` precisa do formato unificado (não é o resumo bruto do profiler):
unificado = normalizar_resultado(
    dataset="clientes",
    df=df,
    perfil_resumo=resumo,
    perfil=perfil,
    resultado_pandera=resultado,
    colunas_chave=["id_cliente"],
)

report = QualityReport()
report.gerar_html(unificado, "reports/clientes_quality.html")
report.gerar_json(unificado, "reports/clientes_quality.json")
```

### Sistema de Alertas

```python
from src.reporters.alerts import AlertSystem, CanalConsole

alertas = AlertSystem()
alertas.adicionar_canal(CanalConsole())  # console, arquivo, email ou webhook
novos = alertas.verificar_falhas(unificado)  # já envia para todos os canais
# compat: para reenviar uma lista existente
# alertas.enviar_notificacao(novos)
print(alertas.obter_estatisticas())
```

## 🧪 Testes

```bash
pytest tests/ -v
```

## ⏰ Orquestração (Airflow, opcional)

`dags/data_quality.py` roda o pipeline diariamente como **gate de qualidade**: falha se algum dataset for reprovado. Requer Airflow 2.6 com este repo e o `requirements.txt` nos workers:

```bash
export DQ_BASE_DIR=/opt/data-quality-platform  # onde o repo está no worker
export DQ_SCHEMA=cliente
# DQ_FAIL_ON_REJECTED=false  # só reportar, sem falhar a task
```

### Subir local com docker compose

Sobe Postgres + scheduler + webserver (imagem oficial `apache/airflow:2.6.3-python3.11`, repo montado em `/opt/data-quality-platform`):

```bash
cp .env.example .env   # ajuste POSTGRES_PASSWORD e FERNET_KEY
docker compose up airflow-init && docker compose up -d
# UI em http://localhost:8080 (admin / admin)
```

> Sem docker na máquina, o compose não foi testado aqui — só o YAML foi validado. As deps do projeto entram via `_PIP_ADDITIONAL_REQUIREMENTS` no boot (lento na primeira vez).

### Com Podman (rootless)

Troque `docker compose` por `podman compose` e force `AIRFLOW_UID=0` no `.env` (o uid 0 do container mapeia para o seu usuário no host; sem isso, o Airflow não consegue escrever em `data/`):

```bash
cp .env.example .env   # ajuste POSTGRES_PASSWORD, FERNET_KEY e AIRFLOW_UID=0
podman compose up airflow-init   # migrate + cria admin (termina sozinho)
podman compose up -d             # scheduler + webserver
# UI em http://localhost:8080 (admin / admin)
podman compose logs -f airflow-scheduler
```

> A DAG é `@daily` com `catchup=False`: a primeira execução agenda para o dia seguinte — para testar na hora, dispare manualmente na UI (▶️). Para derrubar: `podman compose down` (`-v` apaga o banco).

## 📋 Regras de Qualidade

| Dimensão | Descrição |
|----------|-----------|
| Completude | Verificação de valores nulos |
| Unicidade | Detecção de duplicatas |
| Consistência | Validação de formatos e tipos |
| Validez | Conformidade com regras de negócio |
| Tempestividade | Verificação de datas/atualizações |

### Score de qualidade (DQ-02)

O profiler calcula um score de **colunas** (40% completude + 30% unicidade + 30% consistência — heurística documentada em `data_profiler.py`). O pipeline combina isso com a **taxa de aprovação de linhas**:

```
score_final = min(score_perfil, taxa_aprovacao × 100)
```

A qualidade é limitada pela pior dimensão: com 20% das linhas rejeitadas, o score nunca passa de 80. O relatório HTML exibe os dois números lado a lado.

## 🛠️ Tecnologias

- **Python 3.10+** (testado em 3.14)
- **Pandas** - Manipulação de dados
- **Pandera** - Validação de schemas
- **SQLAlchemy** - Conexão com bancos (reservado, sem uso atual)
- **Jupyter** - Análise interativa
- **Matplotlib** - Visualizações
- **Requests** - Webhooks de alerta

## 📝 Licença

MIT License
