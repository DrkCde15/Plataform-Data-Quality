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
04-data-quality-platform/
├── README.md
├── requirements.txt
├── src/
│   ├── __init__.py
│   ├── validators/
│   │   ├── schema_validator.py    # Validação com Pandera
│   │   ├── expectations.py        # Great Expectations suites
│   │   └── data_profiler.py       # Profiling de dados
│   └── reporters/
│       ├── quality_report.py      # Relatórios HTML/JSON
│       └── alerts.py              # Sistema de alertas
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

### Validação com Pandera

```python
from src.validators.schema_validator import SchemaValidator

validator = SchemaValidator()
resultado = validator.validar_dataframe(df)
print(resultado)
```

### Great Expectations

```python
from src.validators.expectations import ExpectationsSuite

suite = ExpectationsSuite()
resultados = suite.executar_validacoes(df)
```

### Profiling de Dados

```python
from src.validators.data_profiler import DataProfiler

profiler = DataProfiler()
relatorio = profiler.perfilar(df)
```

### Geração de Relatórios

```python
from src.reporters.quality_report import QualityReport

report = QualityReport()
report.gerar_html(resultados, "relatorio.html")
report.gerar_json(resultados, "relatorio.json")
```

### Sistema de Alertas

```python
from src.reporters.alerts import AlertSystem

alertas = AlertSystem()
alertas.verificar_falhas(resultados)
alertas.enviar_notificacao(falhas)
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

- **Python 3.8+**
- **Pandas** - Manipulação de dados
- **PySpark** - Processamento distribuído
- **Pandera** - Validação de schemas
- **Great Expectations** - Framework de qualidade
- **SQLAlchemy** - Conexão com bancos
- **Jupyter** - Análise interativa
- **Matplotlib** - Visualizações

## 📝 Licença

MIT License
