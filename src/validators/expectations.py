"""
Módulo de Great Expectations para validação de dados.
Define suites de expectativas para diferentes tipos de dados.
"""

from typing import Any, Dict, List, Optional

import pandas as pd

try:
    import great_expectations as gx
    from great_expectations.core import ExpectationSuite, ExpectationValidationResult
    from great_expectations.execution_engine import PandasExecutionEngine
    from great_expectations.expectations.expectation import ColumnExpectation
    from great_expectations.validator.validator import Validator

    GE_DISPONIVEL = True
except ImportError:
    GE_DISPONIVEL = False


class ExpectationsSuite:
    """Classe para gerenciar suites de Great Expectations."""

    def __init__(self) -> None:
        if not GE_DISPONIVEL:
            raise ImportError("Great Expectations não está instalado. Execute: pip install great_expectations")
        self._suites: Dict[str, ExpectationSuite] = {}
        self._criar_suites_padrao()

    def _criar_suites_padrao(self) -> None:
        """Cria suites de expectativas padrão."""
        self._suites["clientes"] = self._suite_clientes()
        self._suites["pedidos"] = self._suite_pedidos()
        self._suites["produtos"] = self._suite_produtos()
        self._suites["geral"] = self._suite_geral()

    def _suite_clientes(self) -> ExpectationSuite:
        """Cria suite de expectativas para clientes."""
        suite = ExpectationSuite(expectation_suite_name="suite_clientes")

        suite.add_expectation(
            gx.expectations.ExpectColumnValuesToNotBeNull(column="id_cliente")
        )
        suite.add_expectation(
            gx.expectations.ExpectColumnValuesToBeUnique(column="id_cliente")
        )
        suite.add_expectation(
            gx.expectations.ExpectColumnValuesToNotBeNull(column="nome")
        )
        suite.add_expectation(
            gx.expectations.ExpectColumnValueLengthsToBeBetween(
                column="nome", min_value=2, max_value=255
            )
        )
        suite.add_expectation(
            gx.expectations.ExpectColumnValuesToMatchRegex(
                column="email", regex=r"^[\w\.-]+@[\w\.-]+\.\w+$"
            )
        )
        suite.add_expectation(
            gx.expectations.ExpectColumnValuesToNotBeNull(column="data_cadastro")
        )
        return suite

    def _suite_pedidos(self) -> ExpectationSuite:
        """Cria suite de expectativas para pedidos."""
        suite = ExpectationSuite(expectation_suite_name="suite_pedidos")

        suite.add_expectation(
            gx.expectations.ExpectColumnValuesToNotBeNull(column="id_pedido")
        )
        suite.add_expectation(
            gx.expectations.ExpectColumnValuesToBeUnique(column="id_pedido")
        )
        suite.add_expectation(
            gx.expectations.ExpectColumnValuesToNotBeNull(column="id_cliente")
        )
        suite.add_expectation(
            gx.expectations.ExpectColumnValuesToBeBetween(
                column="valor_total", min_value=0, max_value=1000000
            )
        )
        suite.add_expectation(
            gx.expectations.ExpectColumnValuesToBeInSet(
                column="status",
                value_set=["pendente", "processando", "enviado", "entregue", "cancelado"],
            )
        )
        return suite

    def _suite_produtos(self) -> ExpectationSuite:
        """Cria suite de expectativas para produtos."""
        suite = ExpectationSuite(expectation_suite_name="suite_produtos")

        suite.add_expectation(
            gx.expectations.ExpectColumnValuesToNotBeNull(column="id_produto")
        )
        suite.add_expectation(
            gx.expectations.ExpectColumnValuesToBeUnique(column="id_produto")
        )
        suite.add_expectation(
            gx.expectations.ExpectColumnValuesToNotBeNull(column="nome")
        )
        suite.add_expectation(
            gx.expectations.ExpectColumnValuesToBeBetween(
                column="preco", min_value=0, max_value=100000
            )
        )
        suite.add_expectation(
            gx.expectations.ExpectColumnValuesToBeBetween(
                column="estoque", min_value=0, max_value=1000000
            )
        )
        return suite

    def _suite_geral(self) -> ExpectationSuite:
        """Cria suite de expectativas gerais para qualquer DataFrame."""
        suite = ExpectationSuite(expectation_suite_name="suite_geral")

        suite.add_expectation(
            gx.expectations.ExpectTableRowCountToBeBetween(min_value=0, max_value=10000000)
        )
        return suite

    def registrar_suite(self, nome: str, suite: ExpectationSuite) -> None:
        """Registra uma nova suite de expectativas."""
        self._suites[nome] = suite

    def executar_validacoes(self, df: pd.DataFrame, nome_suite: str = "geral") -> Dict[str, Any]:
        """
        Executa as validações de uma suite contra um DataFrame.

        Args:
            df: DataFrame a ser validado.
            nome_suite: Nome da suite a ser executada.

        Returns:
            Dicionário com resultados das validações.
        """
        if nome_suite not in self._suites:
            return {"sucesso": False, "erro": f"Suite '{nome_suite}' não encontrada"}

        suite = self._suites[nome_suite]
        execution_engine = PandasExecutionEngine()
        validator = Validator(execution_engine=execution_engine, batches=[(df, None)])

        resultados = []
        for expectativa in suite.expectations:
            try:
                resultado = validator.validate(expectativa)
                resultados.append({
                    "expectativa": str(type(expectativa).__name__),
                    "coluna": getattr(expectativa, "column", None),
                    "sucesso": resultado.success,
                    "detalhes": str(resultado.result) if hasattr(resultado, "result") else None,
                })
            except Exception as e:
                resultados.append({
                    "expectativa": str(type(expectativa).__name__),
                    "coluna": getattr(expectativa, "column", None),
                    "sucesso": False,
                    "erro": str(e),
                })

        total = len(resultados)
        sucesso = sum(1 for r in resultados if r.get("sucesso", False))

        return {
            "sucesso": sucesso == total,
            "total_expectativas": total,
            "sucesso_count": sucesso,
            "falha_count": total - sucesso,
            "resultados": resultados,
        }

    def criar_suite_customizada(
        self,
        nome: str,
        expectativas: List[Dict[str, Any]],
    ) -> ExpectationSuite:
        """
        Cria uma suite customizada a partir de uma lista de expectativas.

        Args:
            nome: Nome da suite.
            expectativas: Lista de dicts com configurações das expectativas.

        Returns:
            ExpectationSuite configurada.
        """
        suite = ExpectationSuite(expectation_suite_name=nome)

        for exp_config in expectativas:
            tipo = exp_config.get("tipo")
            coluna = exp_config.get("coluna")
            params = exp_config.get("params", {})

            if tipo == "not_null" and coluna:
                suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(column=coluna))
            elif tipo == "unique" and coluna:
                suite.add_expectation(gx.expectations.ExpectColumnValuesToBeUnique(column=coluna))
            elif tipo == "between" and coluna:
                suite.add_expectation(
                    gx.expectations.ExpectColumnValuesToBeBetween(
                        column=coluna,
                        min_value=params.get("min_value"),
                        max_value=params.get("max_value"),
                    )
                )
            elif tipo == "in_set" and coluna:
                suite.add_expectation(
                    gx.expectations.ExpectColumnValuesToBeInSet(
                        column=coluna,
                        value_set=params.get("value_set", []),
                    )
                )
            elif tipo == "regex" and coluna:
                suite.add_expectation(
                    gx.expectations.ExpectColumnValuesToMatchRegex(
                        column=coluna,
                        regex=params.get("regex", ".*"),
                    )
                )

        return suite

    def adicionar_expectativa(
        self,
        nome_suite: str,
        tipo: str,
        coluna: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """
        Adiciona uma expectativa a uma suite existente.

        Args:
            nome_suite: Nome da suite.
            tipo: Tipo da expectativa.
            coluna: Nome da coluna (se aplicável).
            **kwargs: Parâmetros adicionais.
        """
        if nome_suite not in self._suites:
            self._suites[nome_suite] = ExpectationSuite(expectation_suite_name=nome_suite)

        suite = self._suites[nome_suite]

        if tipo == "not_null" and coluna:
            suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(column=coluna))
        elif tipo == "unique" and coluna:
            suite.add_expectation(gx.expectations.ExpectColumnValuesToBeUnique(column=coluna))
        elif tipo == "between" and coluna:
            suite.add_expectation(
                gx.expectations.ExpectColumnValuesToBeBetween(
                    column=coluna,
                    min_value=kwargs.get("min_value"),
                    max_value=kwargs.get("max_value"),
                )
            )
        elif tipo == "in_set" and coluna:
            suite.add_expectation(
                gx.expectations.ExpectColumnValuesToBeInSet(
                    column=coluna,
                    value_set=kwargs.get("value_set", []),
                )
            )
        elif tipo == "row_count":
            suite.add_expectation(
                gx.expectations.ExpectTableRowCountToBeBetween(
                    min_value=kwargs.get("min_value", 0),
                    max_value=kwargs.get("max_value", 1000000),
                )
            )

    def listar_suites(self) -> List[str]:
        """Retorna nomes de todas as suites disponíveis."""
        return list(self._suites.keys())

    def obter_suite(self, nome: str) -> Optional[ExpectationSuite]:
        """Retorna uma suite pelo nome."""
        return self._suites.get(nome)
