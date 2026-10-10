"""Enumeradores de domínio compartilhados."""

from __future__ import annotations

import enum


class StrEnum(str, enum.Enum):
    """Enum compatível com serialização direta em JSON/Postgres."""

    def __str__(self) -> str:  # pragma: no cover - conveniência
        return self.value


class UserRole(StrEnum):
    VISITOR = "visitor"
    CITIZEN = "citizen"
    RESEARCHER = "researcher"
    ADMIN = "admin"


class SourceStatus(StrEnum):
    ACTIVE = "active"
    DEGRADED = "degraded"       # respondendo com erros parciais
    UNAVAILABLE = "unavailable"  # fora do ar
    MAINTENANCE = "maintenance"


class CollectionStatus(StrEnum):
    RUNNING = "running"
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


class GovernmentSphere(StrEnum):
    FEDERAL = "federal"
    STATE = "state"
    MUNICIPAL = "municipal"
    OTHER = "other"


class GovernmentPower(StrEnum):
    EXECUTIVE = "executive"
    LEGISLATIVE = "legislative"
    JUDICIARY = "judiciary"
    OTHER = "other"


class ProcurementModality(StrEnum):
    """Modalidades do PNCP (codigoModalidadeContratacao)."""

    LEILAO = "1"
    DIALOGO_COMPETITIVO = "2"
    CONCORRENCIA = "3"
    CONCURSO = "4"
    PREGAO = "5"
    DISPENSA = "6"
    INEXIGIBILIDADE = "7"
    MANIFESTACAO_INTERESSE = "8"
    PRE_QUALIFICACAO = "9"
    CREDENCIAMENTO = "10"
    LEILAO_ELETRONICO = "11"
    DIALOGO_COMPETITIVO_ELETRONICO = "12"
    CONCORRENCIA_ELETRONICA = "13"
    DESCONHECIDA = "0"


class ProcurementStatus(StrEnum):
    DIVULGADA = "divulgada"
    REVOGADA = "revogada"
    ANULADA = "anurada"
    SUSPENSA = "suspensa"
    DESCONHECIDA = "desconhecida"


class ItemKind(StrEnum):
    MATERIAL = "material"
    SERVICO = "servico"
    OBRA = "obra"
    DESCONHECIDO = "desconhecido"


class ContractStatus(StrEnum):
    VIGENTE = "vigente"
    ENCERRADO = "encerrado"
    RESCINDIDO = "rescindido"
    SUSPENSO = "suspenso"
    DESCONHECIDO = "desconhecido"


class FinancialStage(StrEnum):
    """Estágios financeiros da despesa pública.

    Nunca trate um estágio como se fosse outro. Um contrato publicado não é
    pagamento; um valor homologado não é despesa liquidada.
    """

    ESTIMADO = "estimado"          # valor previsto/estimado da contratação
    HOMOLOGADO = "homologado"      # valor contratado/adjudicado
    EMPENHADO = "empenhado"        # empenho emitido
    LIQUIDADO = "liquidado"        # despesa liquidada
    PAGO = "pago"                  # efetivamente pago


class FindingRule(StrEnum):
    """Regras de detecção de anomalias (indicadores para investigação)."""

    UNIT_PRICE_OUTLIER = "unit_price_outlier"
    TOTAl_ABOVE_ESTIMATE = "total_above_estimate"
    QUANTITY_INCONSISTENT = "quantity_inconsistent"
    REPEATED_SIMILAR_PURCHASE = "repeated_similar_purchase"
    SUPPLIER_CONCENTRATION = "supplier_concentration"
    LARGE_CONTRACT_AMENDMENT = "large_contract_amendment"


class FindingStatus(StrEnum):
    IDENTIFICADO = "identificado"            # identificado automaticamente
    AGUARDANDO_VERIFICACAO = "aguardando_verificacao"
    EM_ANALISE = "em_analise"
    DOCUMENTADO = "documentado"
    ENCERRADO_APOS_ANALISE = "encerrado_apos_analise"
    SEM_IRREGULARIDADE = "sem_irregularidade"


class FindingSeverity(StrEnum):
    INFO = "info"
    ATENCAO = "atencao"
    RELEVANTE = "relevante"


class InvestigationStatus(StrEnum):
    ABERTA = "aberta"
    EM_ANDAMENTO = "em_andamento"
    CONCLUIDA = "concluida"
    ARQUIVADA = "arquivada"


class EvidenceKind(StrEnum):
    RECORD = "record"           # registro público salvo
    NOTE = "note"               # anotação do usuário
    DOCUMENT = "document"       # documento anexado/referenciado
    FINDING = "finding"         # achado de auditoria associado
    COMPARISON = "comparison"   # comparação de preços/contratos


class SubscriptionKind(StrEnum):
    SUPPLIER = "supplier"
    MUNICIPALITY = "municipality"
    GOVERNMENT_ENTITY = "government_entity"
    KEYWORD = "keyword"


class NotificationChannel(StrEnum):
    IN_APP = "in_app"
    EMAIL = "email"
