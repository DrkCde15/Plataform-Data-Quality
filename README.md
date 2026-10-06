# 📊 Plataforma de Qualidade de Dados

Plataforma completa para validação, profiling e monitoramento da qualidade de dados utilizando Python, Pandera, Great Expectations, Pandas e PySpark.

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
│   │   ├── expectations.py        # Great Expectations suites (opcional/legado)
│   │   └── data_profiler.py       # Profiling de dados
│   └── reporters/
│       ├── quality_report.py      # Relatórios HTML/JSON
│       └── alerts.py              # Sistema de alertas
├── data/
│   ├── raw/                     # entrada (CSV/Parquet/JSON)
│   ├── validated/               # saída: linhas aprovadas
│   └── rejected/                # saída: linhas reprovadas + *_erros.json
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
python -m src.pipeline --base . --schema cliente --suite clientes
```

```python
from pathlib import Path
from src.pipeline import DataQualityPipeline

pipe = DataQualityPipeline(base_dir=".", colunas_chave=["id_cliente"])
res = pipe.executar_arquivo("data/raw/clientes_exemplo.csv", nome_schema="cliente", nome_suite="clientes")
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

### Great Expectations (opcional/legado)

```python
from src.validators.expectations import ExpectationsSuite

suite = ExpectationsSuite()  # levanta ImportError se GX não instalado
# nome_suite: "clientes" | "pedidos" | "produtos" | "geral"
resultados = suite.executar_validacoes(df, "clientes")
```

> Nota: GX 1.x exige Python <3.14 e GX 0.18.x conflita com `pandas==3`.
> O pipeline funciona sem GX (etapa ignorada com aviso). Ver `requirements.txt`.

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
    resultado_gx=resultados,
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

## 📋 Regras de Qualidade

| Dimensão | Descrição |
|----------|-----------|
| Completude | Verificação de valores nulos |
| Unicidade | Detecção de duplicatas |
| Consistência | Validação de formatos e tipos |
| Validez | Conformidade com regras de negócio |
| Tempestividade | Verificação de datas/atualizações |

## 🛠️ Tecnologias

- **Python 3.10+** (testado em 3.14; GX 1.x exige <3.14)
- **Pandas** - Manipulação de dados
- **Pandera** - Validação de schemas
- **Great Expectations** - Framework de qualidade (opcional/legado)
- **SQLAlchemy** - Conexão com bancos (reservado, sem uso atual)
- **Jupyter** - Análise interativa
- **Matplotlib** - Visualizações
- **Requests** - Webhooks de alerta

## 📝 Licença

MIT License
