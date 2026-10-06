"""
Módulo de validação de schemas usando Pandera.
Define schemas para diferentes tipos de dados e funções de validação.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

try:
    # Pandera >= 0.20 (inclui 0.34.1 pinada): API nova em pandera.pandas
    import pandera.pandas as pa
    from pandera.pandas import Check, Column, DataFrameModel, DataFrameSchema
    from pandera.errors import SchemaErrors
    import pandera.typing as pat

    _PANDERA_MODERNA = True
except ImportError:  # fallback legado (pandera < 0.20)
    import pandera as pa  # type: ignore[no-redef]
    from pandera import Check, Column, DataFrameSchema  # type: ignore

    try:
        from pandera import SchemaModel as DataFrameModel  # type: ignore
    except ImportError:
        from pandera import SchemaModel as DataFrameModel  # type: ignore
    from pandera.errors import SchemaErrors  # type: ignore
    pat = None  # type: ignore
    _PANDERA_MODERNA = False


if _PANDERA_MODERNA:

    class PedidoSchema(DataFrameModel):
        """Schema para tabela de pedidos."""

        id_pedido: pat.Series[int] = pa.Field(nullable=False, unique=True)  # type: ignore[name-defined]
        id_cliente: pat.Series[int] = pa.Field(nullable=False)  # type: ignore[name-defined]
        data_pedido: pat.Series[datetime] = pa.Field(nullable=False)  # type: ignore[name-defined]
        valor_total: pat.Series[float] = pa.Field(ge=0, nullable=False)  # type: ignore[name-defined]
        status: pat.Series[str] = pa.Field(  # type: ignore[name-defined]
            nullable=False,
            isin=["pendente", "processando", "enviado", "entregue", "cancelado"],
        )

    class ClienteSchema(DataFrameModel):
        """Schema para tabela de clientes."""

        id_cliente: pat.Series[int] = pa.Field(nullable=False, unique=True)  # type: ignore[name-defined]
        nome: pat.Series[str] = pa.Field(nullable=False, str_length={"min_value": 2})  # type: ignore[name-defined]
        email: pat.Series[str] = pa.Field(  # type: ignore[name-defined]
            nullable=False, str_matches=r"^[\w\.-]+@[\w\.-]+\.\w+$"
        )
        telefone: pat.Series[str] = pa.Field(nullable=True)  # type: ignore[name-defined]
        data_cadastro: pat.Series[datetime] = pa.Field(nullable=False)  # type: ignore[name-defined]
        ativo: pat.Series[bool] = pa.Field(nullable=False)  # type: ignore[name-defined]

    class ProdutoSchema(DataFrameModel):
        """Schema para tabela de produtos."""

        id_produto: pat.Series[int] = pa.Field(nullable=False, unique=True)  # type: ignore[name-defined]
        nome: pat.Series[str] = pa.Field(nullable=False, str_length={"min_value": 1})  # type: ignore[name-defined]
        categoria: pat.Series[str] = pa.Field(nullable=False)  # type: ignore[name-defined]
        preco: pat.Series[float] = pa.Field(ge=0, nullable=False)  # type: ignore[name-defined]
        estoque: pat.Series[int] = pa.Field(ge=0, nullable=False)  # type: ignore[name-defined]

else:  # pragma: no cover - caminho legado

    class PedidoSchema(DataFrameModel):  # type: ignore[no-redef]
        """Schema para tabela de pedidos."""

        id_pedido: Column = pa.Field(nullable=False, unique=True)  # type: ignore
        id_cliente: Column = Column(nullable=False)  # type: ignore
        data_pedido: Column = Column(nullable=False)  # type: ignore
        valor_total: Column = Column(ge=0, nullable=False)  # type: ignore
        status: Column = Column(  # type: ignore
            nullable=False,
            isin=["pendente", "processando", "enviado", "entregue", "cancelado"],
        )

    class ClienteSchema(DataFrameModel):  # type: ignore[no-redef]
        """Schema para tabela de clientes."""

        id_cliente: Column = pa.Field(nullable=False, unique=True)  # type: ignore
        nome: Column = Column(nullable=False)  # type: ignore
        email: Column = Column(nullable=False)  # type: ignore
        telefone: Column = Column(nullable=True)  # type: ignore
        data_cadastro: Column = Column(nullable=False)  # type: ignore
        ativo: Column = Column(nullable=False)  # type: ignore

    class ProdutoSchema(DataFrameModel):  # type: ignore[no-redef]
        """Schema para tabela de produtos."""

        id_produto: Column = pa.Field(nullable=False, unique=True)  # type: ignore
        nome: Column = Column(nullable=False)  # type: ignore
        categoria: Column = Column(nullable=False)  # type: ignore
        preco: Column = Column(ge=0, nullable=False)  # type: ignore
        estoque: Column = Column(ge=0, nullable=False)  # type: ignore


class ResultadoValidacao:
    """Armazena o resultado de uma validação."""

    def __init__(
        self,
        valido: bool,
        erros: Optional[List[str]] = None,
        df_original: Optional[pd.DataFrame] = None,
        indices_invalidos: Optional[List[Any]] = None,
    ):
        self.valido = valido
        self.erros = erros or []
        self.df_original = df_original
        self.total_registros = len(df_original) if df_original is not None else 0
        # indices das linhas reprovadas (usado pelo pipeline para split validated/rejected)
        self.indices_invalidos: List[Any] = list(indices_invalidos or [])
        if valido:
            self.registros_invalidos = 0
        elif self.indices_invalidos:
            self.registros_invalidos = len(self.indices_invalidos)
        elif df_original is not None:
            # sem granularidade por linha: não inferir; pipeline preenche via failure_cases
            self.registros_invalidos = 0
        else:
            self.registros_invalidos = 0

    def __repr__(self) -> str:
        status = "VÁLIDO" if self.valido else "INVÁLIDO"
        return (
            f"ResultadoValidacao(status={status}, erros={len(self.erros)}, "
            f"registros={self.total_registros}, invalidos={self.registros_invalidos})"
        )


class SchemaValidator:
    """Classe principal para validação de schemas."""

    def __init__(self) -> None:
        self._schemas: Dict[str, Any] = {
            "pedido": PedidoSchema,
            "cliente": ClienteSchema,
            "produto": ProdutoSchema,
        }

    def registrar_schema(self, nome: str, schema: Any) -> None:
        """Registra um novo schema personalizado."""
        self._schemas[nome] = schema

    def validar_dataframe(self, df: pd.DataFrame, nome_schema: str) -> ResultadoValidacao:
        """
        Valida um DataFrame contra um schema registrado.

        Args:
            df: DataFrame a ser validado.
            nome_schema: Nome do schema registrado.

        Returns:
            ResultadoValidacao com o resultado da validação.
        """
        if nome_schema not in self._schemas:
            return ResultadoValidacao(
                valido=False,
                erros=[f"Schema '{nome_schema}' não encontrado. Disponíveis: {list(self._schemas.keys())}"],
            )

        schema = self._schemas[nome_schema]
        try:
            schema.validate(df, lazy=True)
            return ResultadoValidacao(valido=True, df_original=df)
        except SchemaErrors as e:
            failure_cases = getattr(e, "failure_cases", None)
            erros: List[str] = []
            indices_invalidos: List[Any] = []
            try:
                if failure_cases is not None and not failure_cases.empty:
                    # mensagens legíveis por (coluna, check)
                    if "failure_case" in failure_cases.columns and "check" in failure_cases.columns:
                        col = failure_cases["column"] if "column" in failure_cases.columns else ""
                        for _, row in failure_cases.iterrows():
                            coluna = row.get("column", "?") if hasattr(row, "get") else "?"
                            erros.append(
                                f"coluna '{coluna}': check '{row['check']}' falhou "
                                f"(ex.: {row['failure_case']})"
                            )
                    else:
                        erros = [str(v) for v in failure_cases.to_dict(orient="records")]
                    if "index" in failure_cases.columns:
                        indices_invalidos = sorted(
                            failure_cases["index"].dropna().unique().tolist()
                        )
                else:
                    erros = [str(e)]
            except Exception:
                erros = [str(e)]
            # deduplicar preservando ordem
            erros = list(dict.fromkeys(erros))
            return ResultadoValidacao(
                valido=False,
                erros=erros,
                df_original=df,
                indices_invalidos=indices_invalidos,
            )
        except Exception as e:  # SchemaError não-lazy ou erro inesperado
            return ResultadoValidacao(valido=False, erros=[str(e)], df_original=df)

    def criar_schema_customizado(
        self,
        colunas: Dict[str, Dict[str, Any]],
        index: Optional[Dict[str, Any]] = None,
        coerce: bool = False,
    ) -> DataFrameSchema:
        """
        Cria um schema Pandera personalizado a partir de um dicionário.

        Args:
            colunas: Dicionário com definições das colunas.
            index: Configuração do índice (opcional).
            coerce: Se deve coercir tipos automaticamente.

        Returns:
            DataFrameSchema configurado.
        """
        colunas_schema = {}
        for nome, config in colunas.items():
            kwargs = {}
            if "dtype" in config:
                kwargs["dtype"] = config["dtype"]
            if "nullable" in config:
                kwargs["nullable"] = config["nullable"]
            if "unique" in config:
                kwargs["unique"] = config["unique"]
            if "ge" in config:
                kwargs["ge"] = config["ge"]
            if "le" in config:
                kwargs["le"] = config["le"]
            if "isin" in config:
                kwargs["isin"] = config["isin"]
            if "str_matches" in config:
                kwargs["str_matches"] = config["str_matches"]
            colunas_schema[nome] = Column(**kwargs)

        return DataFrameSchema(columns=colunas_schema, index=index, coerce=coerce)

    def validar_colunas_obrigatorias(self, df: pd.DataFrame, colunas: List[str]) -> ResultadoValidacao:
        """
        Verifica se todas as colunas obrigatórias estão presentes no DataFrame.

        Args:
            df: DataFrame a ser verificado.
            colunas: Lista de colunas obrigatórias.

        Returns:
            ResultadoValidacao com o resultado.
        """
        colunas_faltantes = set(colunas) - set(df.columns)
        if colunas_faltantes:
            return ResultadoValidacao(
                valido=False,
                erros=[f"Colunas faltantes: {', '.join(colunas_faltantes)}"],
                df_original=df,
            )
        return ResultadoValidacao(valido=True, df_original=df)

    @staticmethod
    def _tipos_equivalentes(esperado: str, atual: str) -> bool:
        """Compara dtypes tolerando object<->str do pandas 3 e aliases comuns."""
        if esperado == atual:
            return True
        texto = {"object", "str", "string", "StringDtype", "string[python]", "string[pyarrow]"}
        if esperado in texto and (atual in texto or atual.startswith("string")):
            return True
        # int/float combit: int64==int, float64==float, bool==boolean
        norm = lambda t: {"int": "int64", "float": "float64", "bool": "bool",
                          "boolean": "bool"}.get(t, t)
        return norm(esperado) == norm(atual)

    def validar_tipos(self, df: pd.DataFrame, tipos: Dict[str, str]) -> ResultadoValidacao:
        """
        Verifica se as colunas têm os tipos corretos.

        Args:
            df: DataFrame a ser verificado.
            tipos: Dicionário mapeando colunas para tipos esperados.

        Returns:
            ResultadoValidacao com o resultado.
        """
        erros = []
        for coluna, tipo in tipos.items():
            if coluna not in df.columns:
                erros.append(f"Coluna '{coluna}' não encontrada")
                continue
            tipo_atual = str(df[coluna].dtype)
            if not self._tipos_equivalentes(tipo, tipo_atual):
                erros.append(f"Coluna '{coluna}': tipo esperado '{tipo}', encontrado '{tipo_atual}'")

        return ResultadoValidacao(
            valido=len(erros) == 0,
            erros=erros,
            df_original=df,
        )

    def validar_regras_negocio(
        self,
        df: pd.DataFrame,
        regras: List[Tuple[Any, ...]],
    ) -> ResultadoValidacao:
        """
        Aplica regras de negócio customizadas.

        Formatos aceitos (compatível com versões antigas):
        - (nome_regra, coluna, check): aplica ``check`` em ``df[coluna]``.
        - (nome_regra, check): tenta aplicar ``check`` coluna a coluna;
          use quando o Check já sabe a coluna ou para checks de DataFrame.
        - (coluna, check): atalho onde o nome da regra é ``coluna``.

        Args:
            df: DataFrame a ser validado.
            regras: Lista de tuplas nos formatos acima.

        Returns:
            ResultadoValidacao com o resultado (inclui indices_invalidos).
        """
        erros: List[str] = []
        indices_invalidos_set = set()

        for regra in regras:
            if len(regra) == 3:
                nome_regra, coluna, check = regra
            elif len(regra) == 2:
                nome_regra, check = regra
                coluna = None
            else:
                erros.append(f"Regra malformada: {regra!r} (esperado 2 ou 3 elementos)")
                continue

            try:
                # Caso 1: (nome, coluna, check) — caminho recomendado
                if coluna is not None:
                    if coluna not in df.columns:
                        erros.append(f"Regra '{nome_regra}': coluna '{coluna}' não encontrada")
                        continue
                    serie = df[coluna]
                    mask = check(serie) if callable(getattr(check, "__call__", None)) and not isinstance(check, Check) else None
                    if mask is None:
                        # pa.Check: validar a Series
                        try:
                            # Check.validate retorna Series[bool] ou levanta
                            res = check.validate(serie)
                            # em algumas versões retorna a própria série validada;
                            # considerar falha apenas se levantar exceção
                            mask = pd.Series(True, index=serie.index)
                        except Exception as exc:
                            # extrair índices de falha se for SchemaError com failure_cases
                            fc = getattr(exc, "failure_cases", None)
                            if fc is not None and "index" in fc.columns:
                                for idx in fc["index"].dropna().unique().tolist():
                                    indices_invalidos_set.add(idx)
                                erros.append(
                                    f"Regra '{nome_regra}' (coluna '{coluna}'): "
                                    f"{len(fc)} falha(s)"
                                )
                            else:
                                erros.append(f"Regra '{nome_regra}': {exc}")
                            continue
                    falhas = serie[~mask] if mask is not None and hasattr(mask, "__invert__") else pd.Series([], dtype=object)
                    if len(falhas) > 0:
                        erros.append(f"Regra '{nome_regra}': {len(falhas)} registros falharam")
                        indices_invalidos_set.update(falhas.index.tolist())
                else:
                    # Caso 2: (nome, check) legado — tenta aplicar em cada coluna objeto/numérica
                    aplicado = False
                    for col in df.columns:
                        try:
                            res = check.validate(df[col])
                            aplicado = True
                        except Exception as exc:
                            fc = getattr(exc, "failure_cases", None)
                            if fc is not None:
                                aplicado = True
                                if "index" in fc.columns:
                                    for idx in fc["index"].dropna().unique().tolist():
                                        indices_invalidos_set.add(idx)
                                erros.append(f"Regra '{nome_regra}' (coluna '{col}'): falha de check")
                    if not aplicado:
                        erros.append(
                            f"Regra '{nome_regra}': não foi possível aplicar o Check. "
                            "Use o formato (nome, coluna, check)."
                        )
            except Exception as e:
                erros.append(f"Regra '{nome_regra}': erro ao executar - {str(e)}")

        return ResultadoValidacao(
            valido=len(erros) == 0,
            erros=erros,
            df_original=df,
            indices_invalidos=sorted(indices_invalidos_set),
        )

    def comparar_schemas(
        self, df1: pd.DataFrame, df2: pd.DataFrame, nome: str = "comparacao"
    ) -> ResultadoValidacao:
        """
        Compara a estrutura de dois DataFrames.

        Args:
            df1: Primeiro DataFrame.
            df2: Segundo DataFrame.
            nome: Nome para identificação.

        Returns:
            ResultadoValidacao com diferenças encontradas.
        """
        erros = []

        # Comparar colunas
        colunas_1 = set(df1.columns)
        colunas_2 = set(df2.columns)

        apenas_1 = colunas_1 - colunas_2
        apenas_2 = colunas_2 - colunas_1

        if apenas_1:
            erros.append(f"Colunas apenas no primeiro DataFrame: {apenas_1}")
        if apenas_2:
            erros.append(f"Colunas apenas no segundo DataFrame: {apenas_2}")

        # Comparar tipos nas colunas comuns
        colunas_comuns = colunas_1 & colunas_2
        for coluna in sorted(colunas_comuns):
            tipo_1 = str(df1[coluna].dtype)
            tipo_2 = str(df2[coluna].dtype)
            if tipo_1 != tipo_2:
                erros.append(f"Coluna '{coluna}': tipos diferentes ({tipo_1} vs {tipo_2})")

        return ResultadoValidacao(
            valido=len(erros) == 0,
            erros=erros,
            df_original=df1,
        )
