"""
DAG mínima da plataforma de qualidade (orquestração, estágio 1).

Executa o pipeline `raw -> validated/rejected` sobre `data/raw/` e
funciona como **gate de qualidade**: a task falha se algum dataset
for reprovado pela Pandera, o que dispara o alarme do próprio Airflow
(retry + alerta). Os detalhes por linha continuam no sidecar
`<dataset>_erros.json` e no relatório HTML.

Requer Airflow 2.x no ambiente de execução, com as dependências do
`requirements.txt` instaladas nos workers. Este diretório `dags/`
fica fora do pacote `src/` e não é coletado pelo pytest.

Configuração por variável de ambiente:
    DQ_BASE_DIR: diretório base do projeto (padrão: /opt/data-quality-platform)
    DQ_SCHEMA: schema pandera padrão (cliente|pedido|produto, padrão: cliente)
    DQ_FAIL_ON_REJECTED: "true" para falhar com linhas rejeitadas
        (padrão: "true"; use "false" para só reportar via alertas)
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta

from airflow.decorators import dag, task

BASE_DIR = os.getenv("DQ_BASE_DIR", "/opt/data-quality-platform")
SCHEMA_DEFAULT = os.getenv("DQ_SCHEMA", "cliente")
FAIL_ON_REJECTED = os.getenv("DQ_FAIL_ON_REJECTED", "true").lower() == "true"


@dag(
    dag_id="data_quality",
    schedule="@daily",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    default_args={
        "owner": "data-quality",
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
    },
    tags=["data-quality"],
)
def data_quality():
    @task
    def validar_raw_dir(schema: str = SCHEMA_DEFAULT) -> dict:
        from src.pipeline import DataQualityPipeline

        pipe = DataQualityPipeline(base_dir=BASE_DIR)
        resultados = pipe.executar_raw_dir(nome_schema=schema)
        if not resultados:
            raise ValueError(f"Nenhum arquivo de dados em {pipe.dir_raw}")

        resumo = {
            r["dataset"]: {
                "pandera_valido": r["pandera_valido"],
                "score": r["unificado"]["score_qualidade"],
                "validados": r["unificado"]["linhas_validadas"],
                "rejeitados": r["unificado"]["linhas_rejeitadas"],
            }
            for r in resultados
        }
        reprovados = [d for d, s in resumo.items() if s["pandera_valido"] is False]
        if reprovados and FAIL_ON_REJECTED:
            raise ValueError(
                f"Datasets reprovados: {reprovados}. "
                "Ver sidecar *_erros.json em data/rejected/."
            )
        return resumo

    validar_raw_dir()


data_quality()
