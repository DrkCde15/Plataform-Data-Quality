"""
Testes do score honesto (DQ-02) e do contrato unificado do pipeline.
"""

import sys

import pandas as pd
import pytest

sys.path.insert(0, "..")

from src.pipeline import normalizar_resultado


@pytest.fixture
def df_pequeno() -> pd.DataFrame:
    return pd.DataFrame({"a": [1, 2, 3, 4], "b": ["x", "y", "z", "w"]})


def test_score_limitado_pela_taxa_de_aprovacao(df_pequeno: pd.DataFrame) -> None:
    """Score final nunca passa da aprovação de linhas x 100."""
    resumo = {"total_registros": 4, "total_colunas": 2, "score_qualidade": 100.0,
              "problemas_encontrados": []}
    u = normalizar_resultado("t", df_pequeno, resumo, None, None,
                             taxa_aprovacao=0.5, linhas_validadas=2, linhas_rejeitadas=2)
    assert u["score_perfil"] == 100.0
    assert u["score_qualidade"] == 50.0
    assert u["taxa_aprovacao_linhas"] == 0.5


def test_score_mantem_perfil_quando_aprovacao_total(df_pequeno: pd.DataFrame) -> None:
    resumo = {"total_registros": 4, "total_colunas": 2, "score_qualidade": 80.0,
              "problemas_encontrados": []}
    u = normalizar_resultado("t", df_pequeno, resumo, None, None,
                             taxa_aprovacao=1.0, linhas_validadas=4, linhas_rejeitadas=0)
    assert u["score_qualidade"] == 80.0


def test_sem_taxa_mantem_comportamento_legado(df_pequeno: pd.DataFrame) -> None:
    """Sem taxa informada, score = score do perfil (compat com callers antigos)."""
    resumo = {"total_registros": 4, "total_colunas": 2, "score_qualidade": 77.5,
              "problemas_encontrados": []}
    u = normalizar_resultado("t", df_pequeno, resumo)
    assert u["score_qualidade"] == 77.5
    assert u["taxa_aprovacao_linhas"] is None
