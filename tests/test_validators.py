"""
Testes unitários para os módulos de validação da Plataforma de Qualidade de Dados.
"""

import sys
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, "..")

from src.validators.schema_validator import (
    ResultadoValidacao,
    SchemaValidator,
)


@pytest.fixture
def df_clientes_valido() -> pd.DataFrame:
    """Cria DataFrame válido de clientes para testes."""
    return pd.DataFrame(
        {
            "id_cliente": [1, 2, 3, 4, 5],
            "nome": ["Ana", "Bruno", "Carlos", "Diana", "Eduardo"],
            "email": [
                "ana@email.com",
                "bruno@email.com",
                "carlos@email.com",
                "diana@email.com",
                "eduardo@email.com",
            ],
            "telefone": ["(11) 99999-0001", "(11) 99999-0002", "(11) 99999-0003", "(11) 99999-0004", "(11) 99999-0005"],
            "data_cadastro": [datetime.now() - timedelta(days=i * 10) for i in range(5)],
            "ativo": [True, False, True, True, False],
        }
    )


@pytest.fixture
def df_clientes_invalido() -> pd.DataFrame:
    """Cria DataFrame inválido de clientes para testes."""
    return pd.DataFrame(
        {
            "id_cliente": [1, 1, 3, 4, 5],  # Duplicado
            "nome": ["A", "Bruno", "Carlos", "Diana", "Eduardo"],  # Nome muito curto
            "email": [
                "ana@email.com",
                "invalido",  # Email inválido
                "carlos@email.com",
                "diana@email.com",
                "eduardo@email.com",
            ],
            "telefone": ["(11) 99999-0001", None, "(11) 99999-0003", "(11) 99999-0004", "(11) 99999-0005"],
            "data_cadastro": [datetime.now() - timedelta(days=i * 10) for i in range(5)],
            "ativo": [True, False, True, True, False],
        }
    )


@pytest.fixture
def df_pedidos_valido() -> pd.DataFrame:
    """Cria DataFrame válido de pedidos para testes."""
    return pd.DataFrame(
        {
            "id_pedido": [1, 2, 3, 4, 5],
            "id_cliente": [1, 2, 3, 4, 5],
            "data_pedido": [datetime.now() - timedelta(days=i * 5) for i in range(5)],
            "valor_total": [100.0, 250.50, 50.0, 750.0, 120.0],
            "status": ["pendente", "processando", "enviado", "entregue", "cancelado"],
        }
    )


@pytest.fixture
def validator() -> SchemaValidator:
    """Cria instância do validador."""
    return SchemaValidator()


class TestSchemaValidator:
    """Testes para a classe SchemaValidator."""

    def test_validar_dataframe_valido(self, validator: SchemaValidator, df_clientes_valido: pd.DataFrame) -> None:
        """Testa validação de DataFrame válido."""
        resultado = validator.validar_dataframe(df_clientes_valido, "cliente")
        assert resultado.valido is True
        assert len(resultado.erros) == 0
        assert resultado.total_registros == 5

    def test_validar_dataframe_invalido(self, validator: SchemaValidator, df_clientes_invalido: pd.DataFrame) -> None:
        """Testa validação de DataFrame inválido."""
        resultado = validator.validar_dataframe(df_clientes_invalido, "cliente")
        assert resultado.valido is False
        assert len(resultado.erros) > 0

    def test_schema_nao_encontrado(self, validator: SchemaValidator, df_clientes_valido: pd.DataFrame) -> None:
        """Testa quando schema não existe."""
        resultado = validator.validar_dataframe(df_clientes_valido, "inexistente")
        assert resultado.valido is False
        assert "não encontrado" in resultado.erros[0]

    def test_validar_pedidos(self, validator: SchemaValidator, df_pedidos_valido: pd.DataFrame) -> None:
        """Testa validação de pedidos."""
        resultado = validator.validar_dataframe(df_pedidos_valido, "pedido")
        assert resultado.valido is True

    def test_colunas_obrigatorias_presentes(self, validator: SchemaValidator, df_clientes_valido: pd.DataFrame) -> None:
        """Testa verificação de colunas obrigatórias."""
        colunas = ["id_cliente", "nome", "email"]
        resultado = validator.validar_colunas_obrigatorias(df_clientes_valido, colunas)
        assert resultado.valido is True

    def test_colunas_obrigatorias_faltantes(self, validator: SchemaValidator, df_clientes_valido: pd.DataFrame) -> None:
        """Testa quando colunas obrigatórias estão faltando."""
        colunas = ["id_cliente", "nome", "coluna_inexistente"]
        resultado = validator.validar_colunas_obrigatorias(df_clientes_valido, colunas)
        assert resultado.valido is False
        assert "coluna_inexistente" in str(resultado.erros)

    def test_validar_tipos_corretos(self, validator: SchemaValidator, df_clientes_valido: pd.DataFrame) -> None:
        """Testa validação de tipos corretos."""
        tipos = {"id_cliente": "int64", "nome": "object"}
        resultado = validator.validar_tipos(df_clientes_valido, tipos)
        assert resultado.valido is True

    def test_validar_tipos_incorretos(self, validator: SchemaValidator, df_clientes_valido: pd.DataFrame) -> None:
        """Testa validação de tipos incorretos."""
        tipos = {"id_cliente": "float64"}  # Tipo errado
        resultado = validator.validar_tipos(df_clientes_valido, tipos)
        assert resultado.valido is False

    def test_comparar_schemas_iguais(self, validator: SchemaValidator, df_clientes_valido: pd.DataFrame) -> None:
        """Testa comparação de DataFrames com mesma estrutura."""
        df_copia = df_clientes_valido.copy()
        resultado = validator.comparar_schemas(df_clientes_valido, df_copia)
        assert resultado.valido is True

    def test_comparar_schemas_diferentes(self, validator: SchemaValidator, df_clientes_valido: pd.DataFrame) -> None:
        """Testa comparação de DataFrames com estrutura diferente."""
        df_diferente = df_clientes_valido.drop(columns=["telefone"])
        df_diferente["nova_coluna"] = [1, 2, 3, 4, 5]
        resultado = validator.comparar_schemas(df_clientes_valido, df_diferente)
        assert resultado.valido is False


class TestResultadoValidacao:
    """Testes para a classe ResultadoValidacao."""

    def test_resultado_valido(self, df_clientes_valido: pd.DataFrame) -> None:
        """Testa criação de resultado válido."""
        resultado = ResultadoValidacao(valido=True, df_original=df_clientes_valido)
        assert resultado.valido is True
        assert resultado.total_registros == 5
        assert len(resultado.erros) == 0

    def test_resultado_invalido(self, df_clientes_invalido: pd.DataFrame) -> None:
        """Testa criação de resultado inválido."""
        erros = ["Erro 1", "Erro 2"]
        resultado = ResultadoValidacao(valido=False, erros=erros, df_original=df_clientes_invalido)
        assert resultado.valido is False
        assert len(resultado.erros) == 2

    def test_repr(self) -> None:
        """Testa representação em string."""
        resultado = ResultadoValidacao(valido=True)
        assert "VÁLIDO" in repr(resultado)


class TestDataProfiler:
    """Testes para a classe DataProfiler."""

    @pytest.fixture
    def profiler(self):
        """Cria instância do profiler."""
        from src.validators.data_profiler import DataProfiler

        return DataProfiler()

    def test_perfilar_basico(self, profiler, df_clientes_valido: pd.DataFrame) -> None:
        """Testa profiling básico."""
        perfil = profiler.perfilar(df_clientes_valido, nome="clientes")
        assert perfil.total_registros == 5
        assert perfil.total_colunas == 6
        assert perfil.score_qualidade > 0

    def test_perfilar_colunas(self, profiler, df_clientes_valido: pd.DataFrame) -> None:
        """Testa se todas as colunas foram perfiladas."""
        perfil = profiler.perfilar(df_clientes_valido, nome="clientes")
        assert len(perfil.colunas) == 6
        assert "id_cliente" in perfil.colunas
        assert "nome" in perfil.colunas

    def test_score_qualidade(self, profiler, df_clientes_valido: pd.DataFrame) -> None:
        """Testa cálculo do score de qualidade."""
        perfil = profiler.perfilar(df_clientes_valido, nome="clientes")
        assert 0 <= perfil.score_qualidade <= 100

    def test_deteccao_anomalias_iqr(self, profiler) -> None:
        """Testa detecção de anomalias com IQR."""
        df = pd.DataFrame({"valor": [1, 2, 3, 4, 5, 100]})
        anomalias = profiler.detectar_anomalias(df, "valor", metodo="iqr")
        assert len(anomalias) >= 1  # 100 é um outlier

    def test_deteccao_anomalias_zscore(self, profiler) -> None:
        """Testa detecção de anomalias com Z-Score."""
        df = pd.DataFrame({"valor": [1, 2, 3, 4, 5, 100]})
        anomalias = profiler.detectar_anomalias(df, "valor", metodo="zscore", limiar=2)
        assert len(anomalias) >= 1

    def test_gerar_resumo(self, profiler, df_clientes_valido: pd.DataFrame) -> None:
        """Testa geração de resumo."""
        perfil = profiler.perfilar(df_clientes_valido, nome="clientes")
        resumo = profiler.gerar_resumo(perfil)
        assert "total_registros" in resumo
        assert "score_qualidade" in resumo
        assert "problemas_encontrados" in resumo


class TestQualityReport:
    """Testes para a classe QualityReport."""

    @pytest.fixture
    def report(self):
        """Cria instância do relatório."""
        from src.reporters.quality_report import QualityReport

        return QualityReport()

    def test_gerar_json(self, report, tmp_path) -> None:
        """Testa geração de relatório JSON."""
        resultados = {"score_qualidade": 85.0, "total_registros": 100}
        caminho = str(tmp_path / "teste.json")
        report.gerar_json(resultados, caminho)

        import json

        with open(caminho, "r") as f:
            dados = json.load(f)
        assert "metadata" in dados
        assert "resultados" in dados

    def test_gerar_html(self, report, tmp_path) -> None:
        """Testa geração de relatório HTML."""
        resultados = {"score_qualidade": 85.0, "total_registros": 100, "colunas_analisadas": 5, "problemas": [], "validacoes": []}
        caminho = str(tmp_path / "teste.html")
        report.gerar_html(resultados, caminho)

        with open(caminho, "r") as f:
            conteudo = f.read()
        assert "<!DOCTYPE html>" in conteudo
        assert "85.0%" in conteudo


class TestAlertSystem:
    """Testes para a classe AlertSystem."""

    @pytest.fixture
    def alert_system(self):
        """Cria instância do sistema de alertas."""
        from src.reporters.alerts import AlertSystem

        return AlertSystem()

    def test_verificar_falhas_score_baixo(self, alert_system) -> None:
        """Testa alerta quando score está baixo."""
        resultados = {"score_qualidade": 40.0, "dataset": "teste"}
        alertas = alert_system.verificar_falhas(resultados)
        assert len(alertas) > 0

    def test_verificar_falhas_completude(self, alert_system) -> None:
        """Testa alerta de completude."""
        resultados = {
            "score_qualidade": 90.0,
            "dataset": "teste",
            "colunas": {"nome_coluna": {"percentual_nulos": 80}},
        }
        alertas = alert_system.verificar_falhas(resultados)
        assert any(a.tipo.value == "completude" for a in alertas)

    def test_estatisticas(self, alert_system) -> None:
        """Testa estatísticas dos alertas."""
        resultados = {"score_qualidade": 40.0, "dataset": "teste"}
        alert_system.verificar_falhas(resultados)
        stats = alert_system.obter_estatisticas()
        assert stats["total"] > 0

    def test_resolver_alerta(self, alert_system) -> None:
        """Testa resolução de alerta."""
        resultados = {"score_qualidade": 40.0, "dataset": "teste"}
        alert_system.verificar_falhas(resultados)
        if alert_system._alertas:
            alert_system.resolver_alerta(0)
            assert alert_system._alertas[0].resolvido is True
