"""
Módulo de sistema de alertas para falhas de qualidade de dados.
Suporta diferentes canais de notificação.
"""

import json
import logging
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class NivelAlerta(Enum):
    """Níveis de severidade dos alertas."""

    INFO = "info"
    AVISO = "aviso"
    ERRO = "erro"
    CRITICO = "critico"


class TipoAlerta(Enum):
    """Tipos de alertas de qualidade."""

    COMPLETUDE = "completude"
    UNICIDADE = "unicidade"
    CONSISTENCIA = "consistencia"
    VALIDACAO = "validacao"
    PERFIL = "perfil"
    SISTEMA = "sistema"


class Alerta:
    """Representa um alerta de qualidade."""

    def __init__(
        self,
        titulo: str,
        mensagem: str,
        nivel: NivelAlerta,
        tipo: TipoAlerta,
        dataset: str = "",
        coluna: str = "",
        detalhes: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.titulo = titulo
        self.mensagem = mensagem
        self.nivel = nivel
        self.tipo = tipo
        self.dataset = dataset
        self.coluna = coluna
        self.detalhes = detalhes or {}
        self.data_criacao = datetime.now()
        self.resolvido = False

    def resolver(self) -> None:
        """Marca o alerta como resolvido."""
        self.resolvido = True

    def to_dict(self) -> Dict[str, Any]:
        """Converte o alerta para dicionário."""
        return {
            "titulo": self.titulo,
            "mensagem": self.mensagem,
            "nivel": self.nivel.value,
            "tipo": self.tipo.value,
            "dataset": self.dataset,
            "coluna": self.coluna,
            "detalhes": self.detalhes,
            "data_criacao": self.data_criacao.isoformat(),
            "resolvido": self.resolvido,
        }


class CanalNotificacao:
    """Classe base para canais de notificação."""

    def enviar(self, alerta: Alerta) -> bool:
        """
        Envia uma notificação.

        Args:
            alerta: Alerta a ser enviado.

        Returns:
            True se enviado com sucesso, False caso contrário.
        """
        raise NotImplementedError


class CanalConsole(CanalNotificacao):
    """Canal de notificação via console."""

    def enviar(self, alerta: Alerta) -> bool:
        """Envia notificação para o console."""
        emoji_map = {
            NivelAlerta.INFO: "ℹ️",
            NivelAlerta.AVISO: "⚠️",
            NivelAlerta.ERRO: "❌",
            NivelAlerta.CRITICO: "🚨",
        }
        emoji = emoji_map.get(alerta.nivel, "📢")
        logger.warning(f"{emoji} [{alerta.nivel.value.upper()}] {alerta.titulo}: {alerta.mensagem}")
        return True


class CanalEmail(CanalNotificacao):
    """Canal de notificação via email."""

    def __init__(
        self,
        servidor_smtp: str,
        porta: int,
        email_origem: str,
        senha: str,
        emails_destino: Optional[List[str]] = None,
    ) -> None:
        self.servidor_smtp = servidor_smtp
        self.porta = porta
        self.email_origem = email_origem
        self.senha = senha
        self.emails_destino = emails_destino or []

    def enviar(self, alerta: Alerta) -> bool:
        """Envia notificação por email."""
        if not self.emails_destino:
            logger.warning("Nenhum email de destino configurado")
            return False

        try:
            msg = MIMEMultipart()
            msg["From"] = self.email_origem
            msg["To"] = ", ".join(self.emails_destino)
            msg["Subject"] = f"[{alerta.nivel.value.upper()}] {alerta.titulo}"

            corpo = f"""
            <html>
            <body>
                <h2>Alerta de Qualidade de Dados</h2>
                <p><strong>Nível:</strong> {alerta.nivel.value.upper()}</p>
                <p><strong>Tipo:</strong> {alerta.tipo.value}</p>
                <p><strong>Dataset:</strong> {alerta.dataset or 'N/A'}</p>
                <p><strong>Coluna:</strong> {alerta.coluna or 'N/A'}</p>
                <p><strong>Mensagem:</strong></p>
                <p>{alerta.mensagem}</p>
                <hr>
                <p><small>Gerado em: {alerta.data_criacao.strftime('%d/%m/%Y %H:%M:%S')}</small></p>
            </body>
            </html>
            """

            msg.attach(MIMEText(corpo, "html"))

            with smtplib.SMTP(self.servidor_smtp, self.porta) as servidor:
                servidor.starttls()
                servidor.login(self.email_origem, self.senha)
                servidor.send_message(msg)

            logger.info(f"Email enviado para {len(self.emails_destino)} destinatários")
            return True
        except Exception as e:
            logger.error(f"Erro ao enviar email: {e}")
            return False


class CanalWebhook(CanalNotificacao):
    """Canal de notificação via webhook (HTTP POST)."""

    def __init__(self, url: str, headers: Optional[Dict[str, str]] = None) -> None:
        self.url = url
        self.headers = headers or {"Content-Type": "application/json"}

    def enviar(self, alerta: Alerta) -> bool:
        """Envia notificação via webhook."""
        try:
            import requests

            payload = alerta.to_dict()
            response = requests.post(
                self.url,
                json=payload,
                headers=self.headers,
                timeout=10,
            )
            response.raise_for_status()
            logger.info(f"Webhook enviado com sucesso para {self.url}")
            return True
        except ImportError:
            logger.warning("Biblioteca 'requests' não instalada. pip install requests")
            return False
        except Exception as e:
            logger.error(f"Erro ao enviar webhook: {e}")
            return False


class CanalArquivo(CanalNotificacao):
    """Canal de notificação via arquivo JSON."""

    def __init__(self, caminho_arquivo: str) -> None:
        self.caminho_arquivo = caminho_arquivo

    def enviar(self, alerta: Alerta) -> bool:
        """Salva o alerta em arquivo JSON."""
        try:
            alertas_existentes = []
            try:
                with open(self.caminho_arquivo, "r", encoding="utf-8") as f:
                    alertas_existentes = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                alertas_existentes = []

            alertas_existentes.append(alerta.to_dict())

            with open(self.caminho_arquivo, "w", encoding="utf-8") as f:
                json.dump(alertas_existentes, f, indent=2, ensure_ascii=False, default=str)

            logger.info(f"Alerta salvo em {self.caminho_arquivo}")
            return True
        except Exception as e:
            logger.error(f"Erro ao salvar alerta em arquivo: {e}")
            return False


class AlertSystem:
    """Sistema principal de gerenciamento de alertas."""

    def __init__(self) -> None:
        self._canais: List[CanalNotificacao] = []
        self._alertas: List[Alerta] = []
        self._regras: List[Callable[[Dict[str, Any]], Optional[Alerta]]] = []
        self._configurar_regras_padrao()

    def _configurar_regras_padrao(self) -> None:
        """Configura regras de alerta padrão."""
        self._regras.append(self._regra_completude)
        self._regras.append(self._regra_unicidade)
        self._regras.append(self._regra_score_baixo)
        self._regras.append(self._regra_aumento_nulos)

    def adicionar_canal(self, canal: CanalNotificacao) -> None:
        """Adiciona um canal de notificação."""
        self._canais.append(canal)

    def adicionar_regra(self, regra: Callable[[Dict[str, Any]], Optional[Alerta]]) -> None:
        """Adiciona uma regra de alerta customizada."""
        self._regras.append(regra)

    def verificar_falhas(self, resultados: Dict[str, Any]) -> List[Alerta]:
        """
        Verifica os resultados e gera alertas quando necessário.

        Args:
            resultados: Dicionário com resultados das validações.

        Returns:
            Lista de alertas gerados.
        """
        alertas_novos = []

        for regra in self._regras:
            try:
                alerta = regra(resultados)
                if alerta is not None:
                    alertas_novos.append(alerta)
            except Exception as e:
                logger.error(f"Erro ao executar regra de alerta: {e}")

        # Processar validações específicas
        for validacao in resultados.get("validacoes", []):
            if not validacao.get("sucesso", True):
                alerta = Alerta(
                    titulo=f"Falha na validação: {validacao.get('nome', 'Desconhecida')}",
                    mensagem=validacao.get("detalhes", "Sem detalhes"),
                    nivel=NivelAlerta.ERRO,
                    tipo=TipoAlerta.VALIDACAO,
                    dataset=resultados.get("dataset", ""),
                    coluna=validacao.get("coluna", ""),
                )
                alertas_novos.append(alerta)

        # Adicionar à lista e enviar
        self._alertas.extend(alertas_novos)
        self._enviar_alertas(alertas_novos)

        return alertas_novos

    def _enviar_alertas(self, alertas: List[Alerta]) -> None:
        """Envia alertas por todos os canais configurados."""
        for canal in self._canais:
            for alerta in alertas:
                try:
                    canal.enviar(alerta)
                except Exception as e:
                    logger.error(f"Erro ao enviar alerta via {type(canal).__name__}: {e}")

    def _regra_completude(self, resultados: Dict[str, Any]) -> Optional[Alerta]:
        """Regra: alertar quando completude estiver abaixo do limiar."""
        limiar = resultados.get("limiar_completude", 90)
        colunas = resultados.get("colunas", {})

        for nome_coluna, info in colunas.items():
            percentual_nulos = info.get("percentual_nulos", 0)
            if percentual_nulos > (100 - limiar):
                return Alerta(
                    titulo=f"Baixa completude na coluna '{nome_coluna}'",
                    mensagem=f"Coluna '{nome_coluna}' possui {percentual_nulos:.1f}% de valores nulos (limiar: {100 - limiar}%)",
                    nivel=NivelAlerta.AVISO if percentual_nulos < 50 else NivelAlerta.ERRO,
                    tipo=TipoAlerta.COMPLETUDE,
                    dataset=resultados.get("dataset", ""),
                    coluna=nome_coluna,
                    detalhes={"percentual_nulos": percentual_nulos, "limiar": limiar},
                )
        return None

    def _regra_unicidade(self, resultados: Dict[str, Any]) -> Optional[Alerta]:
        """Regra: alertar quando houver duplicatas em colunas-chave."""
        colunas_chave = resultados.get("colunas_chave", [])
        colunas = resultados.get("colunas", {})

        for nome_coluna in colunas_chave:
            if nome_coluna in colunas:
                duplicatas = colunas[nome_coluna].get("duplicados", 0)
                if duplicatas > 0:
                    return Alerta(
                        titulo=f"Duplicatas na coluna-chave '{nome_coluna}'",
                        mensagem=f"Coluna-chave '{nome_coluna}' possui {duplicatas} valores duplicados",
                        nivel=NivelAlerta.CRITICO,
                        tipo=TipoAlerta.UNICIDADE,
                        dataset=resultados.get("dataset", ""),
                        coluna=nome_coluna,
                        detalhes={"duplicatas": duplicatas},
                    )
        return None

    def _regra_score_baixo(self, resultados: Dict[str, Any]) -> Optional[Alerta]:
        """Regra: alertar quando score de qualidade estiver baixo."""
        score = resultados.get("score_qualidade", 100)
        limiar_critico = 50
        limiar_aviso = 70

        if score < limiar_critico:
            return Alerta(
                titulo="Score de qualidade crítico",
                mensagem=f"Score de qualidade: {score:.1f}% (crítico abaixo de {limiar_critico}%)",
                nivel=NivelAlerta.CRITICO,
                tipo=TipoAlerta.PERFIL,
                dataset=resultados.get("dataset", ""),
                detalhes={"score": score, "limiar": limiar_critico},
            )
        elif score < limiar_aviso:
            return Alerta(
                titulo="Score de qualidade abaixo do esperado",
                mensagem=f"Score de qualidade: {score:.1f}% (aviso abaixo de {limiar_aviso}%)",
                nivel=NivelAlerta.AVISO,
                tipo=TipoAlerta.PERFIL,
                dataset=resultados.get("dataset", ""),
                detalhes={"score": score, "limiar": limiar_aviso},
            )
        return None

    def _regra_aumento_nulos(self, resultados: Dict[str, Any]) -> Optional[Alerta]:
        """Regra: alertar quando houver aumento significativo de nulos."""
        comparacao = resultados.get("comparacao", {})
        if not comparacao:
            return None

        for mudanca in comparacao.get("colunas_com_mudanca_nulos", []):
            nulos_anterior = mudanca.get("nulos_anterior", 0)
            nulos_atual = mudanca.get("nulos_atual", 0)
            aumento = nulos_atual - nulos_anterior

            if aumento > 10:
                return Alerta(
                    titulo=f"Aumento de nulos na coluna '{mudanca.get('coluna', '')}'",
                    mensagem=f"Aumento de {aumento:.1f}% nos valores nulos (de {nulos_anterior:.1f}% para {nulos_atual:.1f}%)",
                    nivel=NivelAlerta.ERRO,
                    tipo=TipoAlerta.COMPLETUDE,
                    dataset=resultados.get("dataset", ""),
                    coluna=mudanca.get("coluna", ""),
                    detalhes={"aumento": aumento, "anterior": nulos_anterior, "atual": nulos_atual},
                )
        return None

    def obter_alertas(
        self,
        nivel: Optional[NivelAlerta] = None,
        tipo: Optional[TipoAlerta] = None,
        resolvidos: Optional[bool] = None,
    ) -> List[Alerta]:
        """
        Retorna alertas filtrados.

        Args:
            nivel: Filtrar por nível de severidade.
            tipo: Filtrar por tipo de alerta.
            resolvidos: Filtrar por status de resolução.

        Returns:
            Lista de alertas filtrados.
        """
        resultado = self._alertas

        if nivel is not None:
            resultado = [a for a in resultado if a.nivel == nivel]
        if tipo is not None:
            resultado = [a for a in resultado if a.tipo == tipo]
        if resolvidos is not None:
            resultado = [a for a in resultado if a.resolvido == resolvidos]

        return resultado

    def resolver_alerta(self, index: int) -> bool:
        """
        Marca um alerta como resolvido.

        Args:
            index: Índice do alerta na lista.

        Returns:
            True se resolvido, False se não encontrado.
        """
        if 0 <= index < len(self._alertas):
            self._alertas[index].resolver()
            return True
        return False

    def exportar_alertas_json(self, caminho: str) -> None:
        """Exporta todos os alertas para JSON."""
        alertas_dicts = [a.to_dict() for a in self._alertas]
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(alertas_dicts, f, indent=2, ensure_ascii=False, default=str)

    def obter_estatisticas(self) -> Dict[str, Any]:
        """Retorna estatísticas dos alertas."""
        total = len(self._alertas)
        por_nivel = {}
        por_tipo = {}
        resolvidos = sum(1 for a in self._alertas if a.resolvido)

        for alerta in self._alertas:
            nivel = alerta.nivel.value
            tipo = alerta.tipo.value
            por_nivel[nivel] = por_nivel.get(nivel, 0) + 1
            por_tipo[tipo] = por_tipo.get(tipo, 0) + 1

        return {
            "total": total,
            "resolvidos": resolvidos,
            "pendentes": total - resolvidos,
            "por_nivel": por_nivel,
            "por_tipo": por_tipo,
        }

    def limpar_alertas_resolvidos(self) -> int:
        """
        Remove alertas resolvidos da lista.

        Returns:
            Número de alertas removidos.
        """
        antes = len(self._alertas)
        self._alertas = [a for a in self._alertas if not a.resolvido]
        return antes - len(self._alertas)
