"""
Módulo de geração de relatórios de qualidade de dados.
Suporta geração de relatórios HTML e JSON.
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd


class QualityReport:
    """Classe para gerar relatórios de qualidade de dados."""

    def __init__(self) -> None:
        self._historico: List[Dict[str, Any]] = []

    def gerar_html(
        self,
        resultados: Dict[str, Any],
        caminho_saida: str,
        titulo: str = "Relatório de Qualidade de Dados",
    ) -> str:
        """
        Gera um relatório HTML com os resultados da qualidade.

        Args:
            resultados: Dicionário com resultados das validações.
            caminho_saida: Caminho do arquivo HTML de saída.
            titulo: Título do relatório.

        Returns:
            Caminho do arquivo gerado.
        """
        data_geracao = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        score = resultados.get("score_qualidade", 0)
        score_perfil = resultados.get("score_perfil", score)
        taxa_aprovacao = resultados.get("taxa_aprovacao_linhas")
        linhas_validadas = resultados.get("linhas_validadas")
        linhas_rejeitadas = resultados.get("linhas_rejeitadas")
        total_registros = resultados.get("total_registros", 0)
        colunas_analisadas = resultados.get("colunas_analisadas", 0)
        problemas = resultados.get("problemas", [])
        validacoes = resultados.get("validacoes", [])

        # Determinar cor do score
        if score >= 80:
            cor_score = "#27ae60"
            status_score = "Bom"
        elif score >= 60:
            cor_score = "#f39c12"
            status_score = "Regular"
        else:
            cor_score = "#e74c3c"
            status_score = "Crítico"

        # Detalhe DQ-02: score final = min(score do perfil, aprovação de linhas).
        # Mostra o detalhamento só quando o pipeline informou a taxa.
        len_problemas = len(problemas)
        if taxa_aprovacao is not None:
            datalhe_score = (
                f'<div class="status" style="font-size: 13px; opacity: 0.85;">'
                f"perfil {score_perfil:.1f}% · linhas {taxa_aprovacao * 100:.1f}%</div>"
            )
            card_aprovacao = f"""<div class="card">
                <h3>Linhas Aprovadas</h3>
                <div class="valor">{taxa_aprovacao * 100:.1f}%</div>
                <div class="status" style="font-size: 13px;">{linhas_validadas} ok · {linhas_rejeitadas} rejeitadas</div>
            </div>"""
        else:
            datalhe_score = ""
            card_aprovacao = ""

        # Gerar HTML
        html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{titulo}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f5f6fa; color: #2c3e50; line-height: 1.6; }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
        header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px; margin-bottom: 30px; }}
        header h1 {{ font-size: 28px; margin-bottom: 10px; }}
        header p {{ opacity: 0.9; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 30px; }}
        .card {{ background: white; border-radius: 10px; padding: 25px; box-shadow: 0 2px 15px rgba(0,0,0,0.1); }}
        .card h3 {{ color: #667eea; margin-bottom: 15px; font-size: 14px; text-transform: uppercase; letter-spacing: 1px; }}
        .card .valor {{ font-size: 36px; font-weight: bold; }}
        .score-card {{ text-align: center; }}
        .score-card .valor {{ color: {cor_score}; }}
        .score-card .status {{ font-size: 16px; color: {cor_score}; margin-top: 5px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ecf0f1; }}
        th {{ background: #f8f9fa; font-weight: 600; color: #2c3e50; }}
        tr:hover {{ background: #f8f9fa; }}
        .badge {{ display: inline-block; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: 600; }}
        .badge-sucesso {{ background: #d4edda; color: #155724; }}
        .badge-erro {{ background: #f8d7da; color: #721c24; }}
        .badge-aviso {{ background: #fff3cd; color: #856404; }}
        .problema {{ background: #fff3cd; border-left: 4px solid #f39c12; padding: 15px; margin-bottom: 10px; border-radius: 5px; }}
        footer {{ text-align: center; padding: 20px; color: #7f8c8d; font-size: 14px; }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>{titulo}</h1>
            <p>Gerado em: {data_geracao}</p>
        </header>

        <div class="grid">
            <div class="card score-card">
                <h3>Score de Qualidade</h3>
                <div class="valor">{score:.1f}%</div>
                <div class="status">{status_score}</div>
                {datalhe_score}
            </div>
            <div class="card">
                <h3>Total de Registros</h3>
                <div class="valor">{total_registros:,}</div>
            </div>
            <div class="card">
                <h3>Colunas Analisadas</h3>
                <div class="valor">{colunas_analisadas}</div>
            </div>
            <div class="card">
                <h3>Problemas Encontrados</h3>
                <div class="valor">{len_problemas}</div>
            </div>
            {card_aprovacao}
        </div>
"""

        # Adicionar problemas
        if problemas:
            html += """
        <div class="card">
            <h3>Problemas Encontrados</h3>
"""
            for problema in problemas:
                html += f'            <div class="problema">{problema}</div>\n'
            html += "        </div>\n"

        # Adicionar validações
        if validacoes:
            html += """
        <div class="card">
            <h3>Resultados das Validações</h3>
            <table>
                <thead>
                    <tr>
                        <th>Validação</th>
                        <th>Status</th>
                        <th>Detalhes</th>
                    </tr>
                </thead>
                <tbody>
"""
            for val in validacoes:
                status_badge = "badge-sucesso" if val.get("sucesso", False) else "badge-erro"
                status_texto = "Sucesso" if val.get("sucesso", False) else "Falha"
                html += f"""                    <tr>
                        <td>{val.get('nome', 'N/A')}</td>
                        <td><span class="badge {status_badge}">{status_texto}</span></td>
                        <td>{val.get('detalhes', 'N/A')}</td>
                    </tr>
"""
            html += """                </tbody>
            </table>
        </div>
"""

        html += """
        <footer>
            <p>Plataforma de Qualidade de Dados - Relatório Automático</p>
        </footer>
    </div>
</body>
</html>"""

        with open(caminho_saida, "w", encoding="utf-8") as f:
            f.write(html)

        self._registrar_historico("html", caminho_saida, resultados)
        return caminho_saida

    def gerar_json(
        self,
        resultados: Dict[str, Any],
        caminho_saida: str,
    ) -> str:
        """
        Gera um relatório JSON com os resultados da qualidade.

        Args:
            resultados: Dicionário com resultados das validações.
            caminho_saida: Caminho do arquivo JSON de saída.

        Returns:
            Caminho do arquivo gerado.
        """
        relatorio = {
            "metadata": {
                "data_geracao": datetime.now().isoformat(),
                "versao_plataforma": "1.0.0",
            },
            "resultados": resultados,
        }

        with open(caminho_saida, "w", encoding="utf-8") as f:
            json.dump(relatorio, f, indent=2, ensure_ascii=False, default=str)

        self._registrar_historico("json", caminho_saida, resultados)
        return caminho_saida

    def gerar_resumo_executivo(
        self,
        perfis: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Gera um resumo executivo de múltiplos perfis.

        Args:
            perfis: Lista de perfis de dados.

        Returns:
            Dicionário com o resumo executivo.
        """
        total_registros = sum(p.get("total_registros", 0) for p in perfis)
        total_colunas = sum(p.get("total_colunas", 0) for p in perfis)
        scores = [p.get("score_qualidade", 0) for p in perfis]
        score_medio = sum(scores) / len(scores) if scores else 0

        problemas_total = []
        for p in perfis:
            problemas_total.extend(p.get("problemas_encontrados", []))

        return {
            "data_geracao": datetime.now().isoformat(),
            "total_datasets": len(perfis),
            "total_registros": total_registros,
            "total_colunas": total_colunas,
            "score_qualidade_medio": round(score_medio, 2),
            "scores_por_dataset": [
                {"nome": p.get("nome", "N/A"), "score": p.get("score_qualidade", 0)}
                for p in perfis
            ],
            "total_problemas": len(problemas_total),
            "problemas": problemas_total[:50],  # Limitar a 50 problemas
        }

    def gerar_html_resumo_executivo(
        self,
        resumo: Dict[str, Any],
        caminho_saida: str,
    ) -> str:
        """
        Gera um relatório HTML do resumo executivo.

        Args:
            resumo: Dicionário com o resumo executivo.
            caminho_saida: Caminho do arquivo HTML de saída.

        Returns:
            Caminho do arquivo gerado.
        """
        data_geracao = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        score_medio = resumo.get("score_qualidade_medio", 0)

        if score_medio >= 80:
            cor_score = "#27ae60"
            status_score = "Bom"
        elif score_medio >= 60:
            cor_score = "#f39c12"
            status_score = "Regular"
        else:
            cor_score = "#e74c3c"
            status_score = "Crítico"

        html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Resumo Executivo - Qualidade de Dados</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', sans-serif; background: #f5f6fa; color: #2c3e50; }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
        header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px; margin-bottom: 30px; }}
        header h1 {{ font-size: 28px; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }}
        .card {{ background: white; border-radius: 10px; padding: 25px; box-shadow: 0 2px 15px rgba(0,0,0,0.1); text-align: center; }}
        .card h3 {{ color: #667eea; font-size: 14px; text-transform: uppercase; margin-bottom: 10px; }}
        .card .valor {{ font-size: 32px; font-weight: bold; }}
        .datasets {{ background: white; border-radius: 10px; padding: 25px; box-shadow: 0 2px 15px rgba(0,0,0,0.1); margin-bottom: 30px; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ecf0f1; }}
        th {{ background: #f8f9fa; font-weight: 600; }}
        footer {{ text-align: center; padding: 20px; color: #7f8c8d; }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Resumo Executivo - Qualidade de Dados</h1>
            <p>Gerado em: {data_geracao}</p>
        </header>

        <div class="grid">
            <div class="card">
                <h3>Datasets Analisados</h3>
                <div class="valor">{resumo.get('total_datasets', 0)}</div>
            </div>
            <div class="card">
                <h3>Total de Registros</h3>
                <div class="valor">{resumo.get('total_registros', 0):,}</div>
            </div>
            <div class="card">
                <h3>Score Médio</h3>
                <div class="valor" style="color: {cor_score};">{score_medio:.1f}%</div>
                <p>{status_score}</p>
            </div>
            <div class="card">
                <h3>Problemas Encontrados</h3>
                <div class="valor">{resumo.get('total_problemas', 0)}</div>
            </div>
        </div>

        <div class="datasets">
            <h2 style="margin-bottom: 20px; color: #2c3e50;">Datasets</h2>
            <table>
                <thead>
                    <tr>
                        <th>Dataset</th>
                        <th>Score</th>
                    </tr>
                </thead>
                <tbody>
"""
        for item in resumo.get("scores_por_dataset", []):
            score = item.get("score", 0)
            cor = "#27ae60" if score >= 80 else "#f39c12" if score >= 60 else "#e74c3c"
            html += f"""                    <tr>
                        <td>{item.get('nome', 'N/A')}</td>
                        <td style="color: {cor}; font-weight: bold;">{score:.1f}%</td>
                    </tr>
"""
        html += """                </tbody>
            </table>
        </div>

        <footer>
            <p>Plataforma de Qualidade de Dados - Resumo Executivo</p>
        </footer>
    </div>
</body>
</html>"""

        with open(caminho_saida, "w", encoding="utf-8") as f:
            f.write(html)

        return caminho_saida

    def _registrar_historico(
        self,
        formato: str,
        caminho: str,
        resultados: Dict[str, Any],
    ) -> None:
        """Registra no histórico de relatórios gerados."""
        self._historico.append({
            "data": datetime.now().isoformat(),
            "formato": formato,
            "caminho": caminho,
            "score": resultados.get("score_qualidade", 0),
        })

    def obter_historico(self) -> List[Dict[str, Any]]:
        """Retorna o histórico de relatórios gerados."""
        return self._historico.copy()

    def exportar_historico_json(self, caminho: str) -> None:
        """Exporta o histórico para JSON."""
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(self._historico, f, indent=2, ensure_ascii=False, default=str)
