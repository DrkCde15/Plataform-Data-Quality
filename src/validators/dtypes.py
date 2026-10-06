"""
Helpers canônicos de dtypes (pandas 2/3).

Centraliza a equivalência object<->str do pandas 3 e a classificação
numérico/texto/data/bool usada por SchemaValidator e DataProfiler.
"""

from __future__ import annotations

_TEXTO = {
    "object", "str", "string",
    "StringDtype", "string[python]", "string[pyarrow]",
    "str32", "str64",
}

_NUMERICOS = {
    "int64", "int32", "int16", "int8", "int",
    "uint64", "uint32", "uint16", "uint8",
    "float64", "float32", "float16", "float",
    "Int64", "Int32", "Float64", "Float32",  # nullable
}

_BOOL = {"bool", "boolean", "bool_", "BooleanDtype"}


def normalizar_tipo(dtype: object) -> str:
    """Normaliza um dtype para comparação (minúsculas, sem parâmetros)."""
    t = str(dtype).strip()
    # "string[python]" -> "string", "datetime64[ns]" -> "datetime64"
    if "[" in t:
        base = t.split("[")[0]
        # manter string[...] como texto
        if base.lower() == "string":
            return "string"
        # datetime64[ns, tz] -> datetime64
        if base.lower().startswith("datetime"):
            return "datetime64"
        return t
    return t


def is_texto(dtype: object) -> bool:
    t = normalizar_tipo(dtype)
    return t in _TEXTO or t.lower().startswith("string")


def is_numerico(dtype: object) -> bool:
    return normalizar_tipo(dtype) in _NUMERICOS


def is_bool(dtype: object) -> bool:
    return normalizar_tipo(dtype) in _BOOL


def is_data(dtype: object) -> bool:
    t = normalizar_tipo(dtype).lower()
    return (
        t.startswith("datetime")
        or t.startswith("date")
        or "datetimetz" in t
        or t in {"<m8[ns]", "datetime64"}
    )


def categoria_tipo(dtype: object) -> str:
    """Retorna 'numerico' | 'texto' | 'data' | 'bool' | 'outro'."""
    if is_bool(dtype):
        return "bool"
    if is_numerico(dtype):
        return "numerico"
    if is_texto(dtype):
        return "texto"
    if is_data(dtype):
        return "data"
    return "outro"


def tipos_equivalentes(esperado: object, atual: object) -> bool:
    """
    Compara dtypes tolerando:
    - object <-> str/string (pandas 3)
    - int<->int64, float<->float64, bool<->boolean
    """
    exp, atu = normalizar_tipo(esperado), normalizar_tipo(atual)
    if exp == atu:
        return True
    if exp.lower() in _TEXTO and atu.lower() in _TEXTO:
        return True
    if is_texto(exp) and is_texto(atu):
        return True
    alias = {
        "int": "int64", "float": "float64", "bool": "bool",
        "boolean": "bool", "datetime": "datetime64",
    }
    return alias.get(exp.lower(), exp.lower()) == alias.get(atu.lower(), atu.lower())
