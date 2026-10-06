"""
Módulo de profiling de dados.
Gera estatísticas detalhadas sobre a qualidade e características dos dados.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

try:
    from src.validators.dtypes import categoria_tipo
except ImportError:
    try:
        from validators.dtypes import categoria_tipo  # type: ignore
    except ImportError:
        from .dtypes import categoria_tipo  # type: ignore


@dataclass
class PerfilColuna:
    """Armazena o perfil de uma coluna."""

    nome: str
    tipo: str
    total_registros: int = 0
    nulos: int = 0
    percentual_nulos: float = 0.0
    unicos: int = 0
    duplicados: int = 0
    valores_negativos: int = 0
    valores_zero: int = 0
    minimo: Optional[float] = None
    maximo: Optional[float] = None
    media: Optional[float] = None
    mediana: Optional[float] = None
    desvio_padrao: Optional[float] = None
    percentis: Dict[int, float] = field(default_factory=dict)
    moda: Optional[Any] = None
    valores_mais_frequentes: List[Dict[str, Any]] = field(default_factory=list)
    comprimento_medio: Optional[float] = None
    comprimento_minimo: Optional[int] = None
    comprimento_maximo: Optional[int] = None
    padrao_data: Optional[str] = None
    categorias_unicas: Optional[List[str]] = None


@dataclass
class PerfilDataFrame:
    """Armazena o perfil completo de um DataFrame."""

    nome: str
    total_registros: int = 0
    total_colunas: int = 0
    colunas: Dict[str, PerfilColuna] = field(default_factory=dict)
    espaco_memoria_mb: float = 0.0
    duplicatas_totais: int = 0
    colunas_completas: int = 0
    colunas_com_nulos: int = 0
    score_qualidade: float = 0.0


class DataProfiler:
    """Classe principal para profiling de dados."""

    def __init__(self, percentis: Optional[List[int]] = None) -> None:
        self._percentis = percentis or [25, 50, 75, 90, 95, 99]

    def perfilar(
        self,
        df: pd.DataFrame,
        nome: str = "sem_nome",
        colunas_numericas: Optional[List[str]] = None,
        colunas_texto: Optional[List[str]] = None,
        colunas_data: Optional[List[str]] = None,
    ) -> PerfilDataFrame:
        """
        Gera o perfil completo de um DataFrame.

        Args:
            df: DataFrame a ser perfilado.
            nome: Nome para identificação.
            colunas_numericas: Lista de colunas numéricas (auto-detect se None).
            colunas_texto: Lista de colunas de texto (auto-detect se None).
            colunas_data: Lista de colunas de data (auto-detect se None).

        Returns:
            PerfilDataFrame com todas as estatísticas.
        """
        perfil = PerfilDataFrame(
            nome=nome,
            total_registros=len(df),
            total_colunas=len(df.columns),
            espaco_memoria_mb=df.memory_usage(deep=True).sum() / 1024 / 1024,
            duplicatas_totais=df.duplicated().sum(),
        )

        # Auto-detectar tipos de colunas
        if colunas_numericas is None:
            colunas_numericas = df.select_dtypes(include=[np.number]).columns.tolist()
        if colunas_texto is None:
            colunas_texto = df.select_dtypes(include=["object", "string"]).columns.tolist()
        if colunas_data is None:
            colunas_data = df.select_dtypes(include=["datetime", "datetimetz"]).columns.tolist()

        for coluna in df.columns:
            perfil_coluna = self._perfilar_coluna(
                df, coluna, colunas_numericas, colunas_texto, colunas_data
            )
            perfil.colunas[coluna] = perfil_coluna

            if perfil_coluna.nulos == 0:
                perfil.colunas_completas += 1
            else:
                perfil.colunas_com_nulos += 1

        perfil.score_qualidade = self._calcular_score_qualidade(perfil)

        return perfil

    def _perfilar_coluna(
        self,
        df: pd.DataFrame,
        coluna: str,
        colunas_numericas: List[str],
        colunas_texto: List[str],
        colunas_data: List[str],
    ) -> PerfilColuna:
        """Perfila uma coluna individual."""
        serie = df[coluna]
        perfil = PerfilColuna(
            nome=coluna,
            tipo=str(serie.dtype),
            total_registros=len(serie),
            nulos=int(serie.isnull().sum()),
            percentual_nulos=round(serie.isnull().sum() / len(serie) * 100, 2) if len(serie) > 0 else 0,
            unicos=int(serie.nunique()),
            duplicados=int(serie.duplicated().sum()),
        )

        # Estatísticas numéricas
        if coluna in colunas_numericas and not serie.isnull().all():
            perfil.minimo = float(serie.min()) if pd.notna(serie.min()) else None
            perfil.maximo = float(serie.max()) if pd.notna(serie.max()) else None
            perfil.media = float(serie.mean()) if pd.notna(serie.mean()) else None
            perfil.mediana = float(serie.median()) if pd.notna(serie.median()) else None
            perfil.desvio_padrao = float(serie.std()) if pd.notna(serie.std()) else None
            perfil.valores_negativos = int((serie < 0).sum())
            perfil.valores_zero = int((serie == 0).sum())

            # Percentis
            for p in self._percentis:
                valor = serie.quantile(p / 100)
                if pd.notna(valor):
                    perfil.percentis[p] = float(valor)

            # Moda
            if not serie.mode().empty:
                perfil.moda = float(serie.mode().iloc[0])

        # Estatísticas de texto
        elif coluna in colunas_texto and not serie.isnull().all():
            serie_texto = serie.dropna()
            if not serie_texto.empty:
                comprimentos = serie_texto.str.len()
                perfil.comprimento_medio = float(comprimentos.mean())
                perfil.comprimento_minimo = int(comprimentos.min())
                perfil.comprimento_maximo = int(comprimentos.max())

                # Valores mais frequentes
                valores_freq = serie_texto.value_counts().head(10)
                perfil.valores_mais_frequentes = [
                    {"valor": str(valor), "frequencia": int(freq)}
                    for valor, freq in valores_freq.items()
                ]

                # Moda
                if not serie_texto.mode().empty:
                    perfil.moda = str(serie_texto.mode().iloc[0])

        # Estatísticas de data
        elif coluna in colunas_data and not serie.isnull().all():
            serie_data = pd.to_datetime(serie.dropna(), errors="coerce").dropna()
            if not serie_data.empty:
                perfil.minimo = serie_data.min().isoformat()
                perfil.maximo = serie_data.max().isoformat()

                # Verificar padrão mais comum
                padroes = serie_data.dt.strftime("%Y-%m-%d").value_counts()
                if not padroes.empty:
                    perfil.padrao_data = str(padroes.index[0])

        # Categorias únicas para colunas com poucos valores únicos
        if perfil.unicos <= 20 and perfil.unicos > 0:
            perfil.categorias_unicas = [str(v) for v in serie.dropna().unique()[:20]]

        return perfil

    def _calcular_score_qualidade(self, perfil: PerfilDataFrame) -> float:
        """
        Calcula um score geral de qualidade das COLUNAS (0-100).

        Fórmula (heurística, não norma):
        - Completude (40%): percentual de colunas sem nulos
        - Unicidade (30%): percentual de registros únicos
        - Consistência (30%): 100 - 5 por coluna com >50% nulos
          - 2 por coluna constante; piso em 0

        Limitação conhecida (DQ-02): este score ignora a taxa de
        aprovação de LINHAS. O `pipeline.normalizar_resultado()`
        corrige isso com `min(score_perfil, taxa_aprovacao * 100)`.
        """
        if perfil.total_registros == 0:
            return 0.0

        # Completude: percentual de colunas sem nulos
        completude = (perfil.colunas_completas / perfil.total_colunas * 100) if perfil.total_colunas > 0 else 0

        # Unicidade: percentual de registros únicos
        unicidade = ((perfil.total_registros - perfil.duplicatas_totais) / perfil.total_registros * 100)

        # Consistência: baseada na qualidade dos tipos
        consistencia = 100.0
        for coluna in perfil.colunas.values():
            if coluna.percentual_nulos > 50:
                consistencia -= 5
            if coluna.unicos == 1 and coluna.total_registros > 1:
                consistencia -= 2

        consistencia = max(0, consistencia)

        # Média ponderada
        score = (completude * 0.4) + (unicidade * 0.3) + (consistencia * 0.3)
        return round(min(100, max(0, score)), 2)

    def detectar_anomalias(
        self,
        df: pd.DataFrame,
        coluna: str,
        metodo: str = "iqr",
        limiar: float = 1.5,
    ) -> pd.DataFrame:
        """
        Detecta anomalias/outliers em uma coluna numérica.

        Args:
            df: DataFrame a ser analisado.
            coluna: Nome da coluna.
            metodo: Método de detecção ('iqr' ou 'zscore').
            limiar: Limiar para considerar outlier.

        Returns:
            DataFrame com os registros anomalous.
        """
        if coluna not in df.columns:
            raise ValueError(f"Coluna '{coluna}' não encontrada")

        serie = df[coluna].dropna()

        if metodo == "iqr":
            q1 = serie.quantile(0.25)
            q3 = serie.quantile(0.75)
            iqr = q3 - q1
            limite_inferior = q1 - (limiar * iqr)
            limite_superior = q3 + (limiar * iqr)
            mascara = (df[coluna] < limite_inferior) | (df[coluna] > limite_superior)
        elif metodo == "zscore":
            media = serie.mean()
            desvio = serie.std()
            if desvio == 0:
                return pd.DataFrame()
            z_scores = np.abs((df[coluna] - media) / desvio)
            mascara = z_scores > limiar
        else:
            raise ValueError(f"Método '{metodo}' não suportado. Use 'iqr' ou 'zscore'")

        return df[mascara].copy()

    def gerar_resumo(self, perfil: PerfilDataFrame) -> Dict[str, Any]:
        """
        Gera um resumo executivo do perfil.

        Args:
            perfil: PerfilDataFrame a ser resumido.

        Returns:
            Dicionário com o resumo.
        """
        resumo = {
            "nome": perfil.nome,
            "total_registros": perfil.total_registros,
            "total_colunas": perfil.total_colunas,
            "score_qualidade": perfil.score_qualidade,
            "espaco_memoria_mb": round(perfil.espaco_memoria_mb, 2),
            "duplicatas_totais": perfil.duplicatas_totais,
            "colunas_completas": perfil.colunas_completas,
            "colunas_com_nulos": perfil.colunas_com_nulos,
            "colunas_numericas": 0,
            "colunas_texto": 0,
            "colunas_data": 0,
            "problemas_encontrados": [],
        }

        for coluna in perfil.colunas.values():
            cat = categoria_tipo(coluna.tipo)
            if cat == "numerico":
                resumo["colunas_numericas"] += 1
            elif cat == "texto":
                resumo["colunas_texto"] += 1
            elif cat == "data":
                resumo["colunas_data"] += 1

            # Identificar problemas
            if coluna.percentual_nulos > 10:
                resumo["problemas_encontrados"].append(
                    f"Coluna '{coluna.nome}': {coluna.percentual_nulos}% de nulos"
                )
            if coluna.duplicados > 0 and coluna.nome in ["id_cliente", "id_pedido", "id_produto"]:
                resumo["problemas_encontrados"].append(
                    f"Coluna '{coluna.nome}': {coluna.duplicados} valores duplicados em coluna-chave"
                )

        return resumo

    def comparar_perfis(
        self, perfil1: PerfilDataFrame, perfil2: PerfilDataFrame
    ) -> Dict[str, Any]:
        """
        Compara dois perfis de DataFrame.

        Args:
            perfil1: Primeiro perfil.
            perfil2: Segundo perfil.

        Returns:
            Dicionário com as diferenças encontradas.
        """
        comparacao = {
            "registros_diferenca": perfil2.total_registros - perfil1.total_registros,
            "colunas_diferenca": perfil2.total_colunas - perfil1.total_colunas,
            "score_diferenca": perfil2.score_qualidade - perfil1.score_qualidade,
            "colunas_adicionadas": [],
            "colunas_removidas": [],
            "colunas_com_mudanca_tipo": [],
            "colunas_com_mudanca_nulos": [],
        }

        colunas_1 = set(perfil1.colunas.keys())
        colunas_2 = set(perfil2.colunas.keys())

        comparacao["colunas_adicionadas"] = list(colunas_2 - colunas_1)
        comparacao["colunas_removidas"] = list(colunas_1 - colunas_2)

        for coluna in colunas_1 & colunas_2:
            c1 = perfil1.colunas[coluna]
            c2 = perfil2.colunas[coluna]

            if c1.tipo != c2.tipo:
                comparacao["colunas_com_mudanca_tipo"].append({
                    "coluna": coluna,
                    "tipo_anterior": c1.tipo,
                    "tipo_atual": c2.tipo,
                })

            if c1.percentual_nulos != c2.percentual_nulos:
                comparacao["colunas_com_mudanca_nulos"].append({
                    "coluna": coluna,
                    "nulos_anterior": c1.percentual_nulos,
                    "nulos_atual": c2.percentual_nulos,
                })

        return comparacao
