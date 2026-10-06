"""
Pipeline de qualidade de dados: raw -> validated/rejected.

Orquestra os módulos existentes e normaliza o dicionário intermediário
para um formato único entendido por QualityReport e AlertSystem.

Formato unificado (contrato):
{
    "dataset": str,
    "total_registros": int,
    "total_colunas": int,
    "colunas_analisadas": int,          # alias de total_colunas (QualityReport)
    "score_qualidade": float,
    "colunas": {                         # para AlertSystem._regra_completude/unicidade
        "<nome>": {
            "percentual_nulos": float,
            "duplicados": int,
            "unicos": int,
            "tipo": str,
        },
    },
    "colunas_chave": list[str],
    "problemas": list[str],              # para QualityReport
    "problemas_encontrados": list[str],  # alias (compat profiler)
    "validacoes": [                      # para QualityReport + AlertSystem
        {"nome": str, "sucesso": bool, "detalhes": str, "coluna": str|None}
    ],
    "comparacao": dict,                  # para AlertSystem._regra_aumento_nulos
    "limiar_completude": float,
    "pandera_erros": list[str],
}

Semântica de quarentena (DQ-03): `validated/` = "aprovado Pandera".
Linhas reprovadas vão para `rejected/` + sidecar `<dataset>_erros.json`.

Uso:
    python -m src.pipeline --arquivo data/raw/clientes_exemplo.csv --schema cliente --chave id_cliente
    python -m src.pipeline --base . --schema cliente
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

logger = logging.getLogger(__name__)

try:
    from src.validators.data_profiler import DataProfiler
    from src.validators.schema_validator import ResultadoValidacao, SchemaValidator
    from src.reporters.alerts import AlertSystem, CanalConsole
    from src.reporters.quality_report import QualityReport
except ImportError:  # execução como script dentro de src/
    from validators.data_profiler import DataProfiler  # type: ignore
    from validators.schema_validator import ResultadoValidacao, SchemaValidator  # type: ignore
    from reporters.alerts import AlertSystem, CanalConsole  # type: ignore
    from reporters.quality_report import QualityReport  # type: ignore


# ---------------------------------------------------------------------------
# IO: raw -> DataFrame
# ---------------------------------------------------------------------------

def _tentar_converter_datas(df: pd.DataFrame) -> pd.DataFrame:
    """Converte colunas object/str que parecem data (ex.: data_cadastro de CSV)."""
    df = df.copy()
    for col in df.columns:
        dtype_nome = str(df[col].dtype)
        # pandas 3 usa 'str' em vez de 'object' para texto
        if dtype_nome not in ("object", "str", "string", "StringDtype"):
            if not dtype_nome.startswith("string"):
                continue
        nome = str(col).lower()
        parece_data = any(k in nome for k in ("data", "date", "dt_", "_at", "cadastro", "pedido"))
        if not parece_data:
            # heurística genérica: amostra não-nula parece timestamp?
            amostra = df[col].dropna().head(20)
            if amostra.empty or not isinstance(amostra.iloc[0], str):
                continue
            parece_data = bool(amostra.str.match(r"^\d{4}-\d{2}-\d{2}").any())
            if not parece_data:
                continue
        try:
            convertida = pd.to_datetime(df[col], errors="coerce")
            taxa = float(convertida.notna().sum() / max(1, df[col].notna().sum()))
            if taxa >= 0.8:
                df[col] = convertida
        except Exception:
            continue
    # booleano vindo de CSV como "True"/"False" string
    for col in df.columns:
        if str(df[col].dtype) not in ("object", "str", "string", "StringDtype") and not str(
            df[col].dtype
        ).startswith("string"):
            continue
            vals = set(df[col].dropna().unique().tolist())
            if vals and vals <= {"True", "False", "true", "false", "TRUE", "FALSE", True, False}:
                df[col] = df[col].map(
                    lambda v: True if str(v).lower() == "true" else False if str(v).lower() == "false" else v
                ).astype("boolean").astype(bool)
    return df


def carregar_arquivo(caminho: Path) -> pd.DataFrame:
    """Carrega CSV/Parquet/JSON em DataFrame. Datas são parseadas quando possível."""
    caminho = Path(caminho)
    if not caminho.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho}")
    sufixo = caminho.suffix.lower()
    if sufixo == ".csv":
        df = pd.read_csv(caminho)
        return _tentar_converter_datas(df)
    if sufixo in (".parquet", ".pq"):
        return pd.read_parquet(caminho)
    if sufixo == ".json":
        try:
            df = pd.read_json(caminho)
        except ValueError:
            with open(caminho, encoding="utf-8") as f:
                df = pd.DataFrame(json.load(f))
        return _tentar_converter_datas(df)
    raise ValueError(f"Extensão não suportada: {sufixo} ({caminho})")


def carregar_raw(diretorio: Path, padrao: str = "*.csv") -> Tuple[str, pd.DataFrame]:
    """Carrega e concatena todos os arquivos do padrão em data/raw."""
    diretorio = Path(diretorio)
    arquivos = sorted(diretorio.glob(padrao))
    if not arquivos:
        # tenta qualquer formato suportado
        arquivos = sorted(
            [p for p in diretorio.iterdir()
             if p.is_file() and p.suffix.lower() in (".csv", ".parquet", ".pq", ".json")]
        )
    if not arquivos:
        raise FileNotFoundError(f"Nenhum arquivo de dados em {diretorio} (padrão {padrao})")
    frames = [carregar_arquivo(p) for p in arquivos]
    df = pd.concat(frames, ignore_index=True) if len(frames) > 1 else frames[0]
    nome = arquivos[0].stem if len(arquivos) == 1 else diretorio.name
    logger.info("Carregados %d registros de %d arquivo(s) (%s)", len(df), len(arquivos), nome)
    return nome, df


# ---------------------------------------------------------------------------
# Normalização: profiler + pandera + GX -> dict unificado
# ---------------------------------------------------------------------------

def _perfil_para_colunas(df: pd.DataFrame, perfil: Any = None) -> Dict[str, Dict[str, Any]]:
    """Constrói o bloco 'colunas' esperado pelo AlertSystem."""
    colunas: Dict[str, Dict[str, Any]] = {}
    perfil_cols = getattr(perfil, "colunas", None) or {}
    for nome in df.columns:
        serie = df[nome]
        pc = perfil_cols.get(nome)
        if pc is not None:
            colunas[nome] = {
                "percentual_nulos": float(getattr(pc, "percentual_nulos", 0.0)),
                "duplicados": int(getattr(pc, "duplicados", 0)),
                "unicos": int(getattr(pc, "unicos", 0)),
                "tipo": str(getattr(pc, "tipo", serie.dtype)),
            }
        else:
            n = len(serie)
            colunas[nome] = {
                "percentual_nulos": round(float(serie.isnull().sum() / n * 100), 2) if n else 0.0,
                "duplicados": int(serie.duplicated().sum()),
                "unicos": int(serie.nunique()),
                "tipo": str(serie.dtype),
            }
    return colunas


def normalizar_resultado(
    dataset: str,
    df: pd.DataFrame,
    perfil_resumo: Optional[Dict[str, Any]] = None,
    perfil: Any = None,
    resultado_pandera: Optional[ResultadoValidacao] = None,
    colunas_chave: Optional[List[str]] = None,
    limiar_completude: float = 90.0,
    taxa_aprovacao: Optional[float] = None,
    linhas_validadas: Optional[int] = None,
    linhas_rejeitadas: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Normaliza as saídas de profiler/pandera para o contrato único.

    - profiler.gerar_resumo() usa: total_colunas, problemas_encontrados
    - QualityReport usa: colunas_analisadas, problemas, validacoes
    - AlertSystem usa: colunas{percentual_nulos, duplicados}, colunas_chave, comparacao
    Esta função preenche todos os aliases para os três consumidores.

    Score honesto (DQ-02): o `score_qualidade` final é o MÍNIMO entre o
    score do perfil (colunas) e a taxa de aprovação de linhas x 100.
    A qualidade é limitada pela pior dimensão: não há métrica verde
    com metade das linhas rejeitadas. Sem `taxa_aprovacao`, o score é
    só o do perfil (comportamento legado).
    """
    perfil_resumo = perfil_resumo or {}
    colunas_chave = colunas_chave or []

    total_registros = int(perfil_resumo.get("total_registros", len(df)))
    total_colunas = int(perfil_resumo.get("total_colunas", len(df.columns)))
    score_perfil = float(perfil_resumo.get("score_qualidade", 100.0))

    if taxa_aprovacao is not None:
        score = round(min(score_perfil, float(taxa_aprovacao) * 100), 2)
    else:
        score = score_perfil

    problemas: List[str] = list(perfil_resumo.get("problemas_encontrados", []) or [])
    validacoes: List[Dict[str, Any]] = []
    pandera_erros: List[str] = []

    if resultado_pandera is not None:
        pandera_erros = list(resultado_pandera.erros or [])
        for erro in pandera_erros:
            if erro not in problemas:
                problemas.append(f"[pandera] {erro}")
        validacoes.append({
            "nome": "pandera_schema",
            "sucesso": bool(resultado_pandera.valido),
            "detalhes": "; ".join(pandera_erros[:5]) if pandera_erros else "schema válido",
            "coluna": None,
        })

    return {
        "dataset": dataset,
        "total_registros": total_registros,
        "total_colunas": total_colunas,
        "colunas_analisadas": total_colunas,
        "score_qualidade": score,
        "colunas": _perfil_para_colunas(df, perfil),
        "colunas_chave": colunas_chave,
        "problemas": problemas,
        "problemas_encontrados": problemas,
        "validacoes": validacoes,
        "comparacao": {},
        "limiar_completude": limiar_completude,
        "pandera_erros": pandera_erros,
        "score_perfil": score_perfil,
        "taxa_aprovacao_linhas": taxa_aprovacao,
        "linhas_validadas": linhas_validadas,
        "linhas_rejeitadas": linhas_rejeitadas,
        "data_processamento": datetime.now().isoformat(),
    }


def dividir_validados_rejeitados(
    df: pd.DataFrame, resultado: Optional[ResultadoValidacao]
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Separa linhas válidas/inválidas a partir dos índices de falha da Pandera."""
    if resultado is None or resultado.valido:
        return df.copy(), df.iloc[0:0].copy()
    idx = [i for i in (resultado.indices_invalidos or []) if i in df.index]
    if not idx:
        # sem granularidade: tudo para rejected + sidecar explica o motivo
        return df.iloc[0:0].copy(), df.copy()
    rejeitados = df.loc[idx].copy()
    validados = df.drop(index=idx).copy()
    return validados, rejeitados


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

class DataQualityPipeline:
    """Orquestra profiling + validação + relatórios + alertas + escrita validated/rejected."""

    def __init__(
        self,
        base_dir: Path | str = ".",
        colunas_chave: Optional[List[str]] = None,
        limiar_completude: float = 90.0,
        alert_system: Optional[AlertSystem] = None,
    ) -> None:
        self.base = Path(base_dir)
        self.dir_raw = self.base / "data" / "raw"
        self.dir_validated = self.base / "data" / "validated"
        self.dir_rejected = self.base / "data" / "rejected"
        self.dir_reports = self.base / "reports"
        for d in (self.dir_validated, self.dir_rejected, self.dir_reports):
            d.mkdir(parents=True, exist_ok=True)

        self.validator = SchemaValidator()
        self.profiler = DataProfiler()
        self.report = QualityReport()
        self.colunas_chave = colunas_chave or []
        self.limiar_completude = limiar_completude

        self.alerts = alert_system or AlertSystem()
        if not getattr(self.alerts, "_canais", []):
            self.alerts.adicionar_canal(CanalConsole())

    def executar_dataframe(
        self,
        df: pd.DataFrame,
        dataset: str,
        nome_schema: Optional[str] = None,
        colunas_chave: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Executa o pipeline completo para um DataFrame já carregado."""
        chaves = colunas_chave if colunas_chave is not None else self.colunas_chave

        # 1. profiling
        perfil = self.profiler.perfilar(df, nome=dataset)
        resumo = self.profiler.gerar_resumo(perfil)

        # 2. validação pandera (opcional)
        res_pandera: Optional[ResultadoValidacao] = None
        if nome_schema:
            try:
                res_pandera = self.validator.validar_dataframe(df, nome_schema)
            except Exception as e:
                logger.error("Falha na validação Pandera: %s", e)
                res_pandera = ResultadoValidacao(valido=False, erros=[str(e)], df_original=df)

        # 3. split validated / rejected (antes da normalização:
        #    a taxa de aprovação alimenta o score honesto - DQ-02)
        validados, rejeitados = dividir_validados_rejeitados(df, res_pandera)
        taxa_aprovacao = (len(validados) / len(df)) if len(df) > 0 else 1.0

        # 4. normalização
        unificado = normalizar_resultado(
            dataset=dataset,
            df=df,
            perfil_resumo=resumo,
            perfil=perfil,
            resultado_pandera=res_pandera,
            colunas_chave=chaves,
            limiar_completude=self.limiar_completude,
            taxa_aprovacao=taxa_aprovacao,
            linhas_validadas=len(validados),
            linhas_rejeitadas=len(rejeitados),
        )

        # 5. escrita validated / rejected + sidecar
        caminho_val = self.dir_validated / f"{dataset}_validated.csv"
        caminho_rej = self.dir_rejected / f"{dataset}_rejected.csv"
        validados.to_csv(caminho_val, index=False)
        rejeitados.to_csv(caminho_rej, index=False)
        lado = {
            "dataset": dataset,
            "total": len(df),
            "validados": len(validados),
            "rejeitados": len(rejeitados),
            "arquivo_validados": str(caminho_val),
            "arquivo_rejeitados": str(caminho_rej),
            "indices_rejeitados": (res_pandera.indices_invalidos if res_pandera else []),
            "erros": (res_pandera.erros if res_pandera else []),
        }
        with open(self.dir_rejected / f"{dataset}_erros.json", "w", encoding="utf-8") as f:
            json.dump(lado, f, indent=2, ensure_ascii=False, default=str)

        # 6. relatórios
        html_path = str(self.dir_reports / f"{dataset}_quality.html")
        json_path = str(self.dir_reports / f"{dataset}_quality.json")
        self.report.gerar_html(unificado, html_path, titulo=f"Relatório de Qualidade — {dataset}")
        self.report.gerar_json(unificado, json_path)

        # 7. alertas
        alertas = self.alerts.verificar_falhas(unificado)

        logger.info(
            "[%s] total=%d validados=%d rejeitados=%d score=%.1f alertas=%d",
            dataset, len(df), len(validados), len(rejeitados),
            unificado["score_qualidade"], len(alertas),
        )
        return {
            "dataset": dataset,
            "unificado": unificado,
            "validados": str(caminho_val),
            "rejeitados": str(caminho_rej),
            "relatorio_html": html_path,
            "relatorio_json": json_path,
            "alertas": [a.to_dict() for a in alertas],
            "pandera_valido": res_pandera.valido if res_pandera else None,
        }

    def executar_arquivo(
        self,
        caminho: Path | str,
        nome_schema: Optional[str] = None,
        colunas_chave: Optional[List[str]] = None,
        dataset: Optional[str] = None,
    ) -> Dict[str, Any]:
        caminho = Path(caminho)
        df = carregar_arquivo(caminho)
        return self.executar_dataframe(
            df, dataset or caminho.stem,
            nome_schema=nome_schema, colunas_chave=colunas_chave,
        )

    def executar_raw_dir(
        self,
        nome_schema: Optional[str] = None,
        padrao: str = "*.csv",
    ) -> List[Dict[str, Any]]:
        resultados = []
        for arquivo in sorted(self.dir_raw.glob(padrao)):
            if arquivo.is_file():
                resultados.append(self.executar_arquivo(arquivo, nome_schema))
        if not resultados:  # fallback: qualquer formato suportado
            for arquivo in sorted(self.dir_raw.iterdir()):
                if arquivo.is_file() and arquivo.suffix.lower() in (".csv", ".parquet", ".pq", ".json"):
                    resultados.append(self.executar_arquivo(arquivo, nome_schema))
        return resultados


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Pipeline de qualidade: raw -> validated/rejected")
    parser.add_argument("--base", default=".", help="diretório base do projeto (padrão: .)")
    parser.add_argument("--arquivo", default=None, help="processar um arquivo específico")
    parser.add_argument("--raw", default=None, help="diretório raw (padrão: <base>/data/raw)")
    parser.add_argument("--dataset", default=None, help="nome do dataset (padrão: nome do arquivo)")
    parser.add_argument("--schema", default=None, help="nome do schema pandera (cliente|pedido|produto)")
    parser.add_argument("--chave", action="append", default=None, help="coluna-chave (repetível)")
    parser.add_argument("--padrao", default="*.csv", help="padrão glob para varredura do raw")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    pipe = DataQualityPipeline(base_dir=args.base, colunas_chave=args.chave or [])

    if args.raw:
        pipe.dir_raw = Path(args.raw)

    if args.arquivo:
        res = pipe.executar_arquivo(args.arquivo, args.schema, dataset=args.dataset)
        print(json.dumps({"dataset": res["dataset"], "pandera_valido": res["pandera_valido"],
                          "alertas": len(res["alertas"]), "html": res["relatorio_html"]}, indent=2))
    else:
        resultados = pipe.executar_raw_dir(args.schema, padrao=args.padrao)
        if not resultados:
            print(f"Nenhum arquivo encontrado em {pipe.dir_raw}", file=sys.stderr)
            return 1
        for res in resultados:
            print(f"[{res['dataset']}] pandera={res['pandera_valido']} "
                  f"alertas={len(res['alertas'])} html={res['relatorio_html']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
