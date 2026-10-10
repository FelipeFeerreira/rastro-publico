"""Geração de relatórios de evidências (dados + PDF)."""

from __future__ import annotations

import io
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit import AuditFinding
from app.models.investigation import Investigation
from app.models.procurement import Contract, Procurement

OVERSIGHT_GUIDANCE = [
    {
        "orgao": "Fala.BR (Ouvidoria Nacional)",
        "descricao": (
            "Canal oficial para denúncias, reclamações e solicitações de acesso à "
            "informação."
        ),
        "url": "https://falabr.cgu.gov.br/",
    },
    {
        "orgao": "Tribunal de Contas da União (TCU)",
        "descricao": "Ouvidoria e canal de denúncias sobre recursos federais.",
        "url": "https://portal.tcu.gov.br/ouvidoria/",
    },
    {
        "orgao": "Tribunais de Contas Estaduais/Municipais",
        "descricao": (
            "Responsáveis pela fiscalização de recursos estaduais e municipais. "
            "Consulte o tribunal competente para o ente envolvido."
        ),
        "url": "https://www.portaltransparencia.gov.br/",
    },
    {
        "orgao": "Ministério Público",
        "descricao": "Atua na defesa do patrimônio público; recebe representações.",
        "url": "https://www.cnmp.mp.br/portal/",
    },
]


def build_report(db: Session, investigation: Investigation) -> dict:
    evidence = investigation.evidence_items
    records = []
    findings = []
    notes = []
    documents = []

    for item in evidence:
        reference = {
            "id": item.id,
            "kind": item.kind.value,
            "title": item.title,
            "note": item.note,
            "reference_type": item.reference_type,
            "reference_id": item.reference_id,
            "source_url": item.source_url,
            "created_at": item.created_at.isoformat(),
        }

        if item.reference_type == "procurement" and item.reference_id:
            procurement = db.get(Procurement, int(item.reference_id))
            if procurement is not None:
                reference["record"] = {
                    "pncp": procurement.pncp_control_number,
                    "object": procurement.object_description,
                    "entity": procurement.entity.name if procurement.entity else None,
                    "estimated_total": float(procurement.estimated_total or 0),
                    "approved_total": float(procurement.approved_total or 0),
                    "source_url": procurement.source_url,
                }
                records.append(reference)
                continue
        if item.reference_type == "contract" and item.reference_id:
            contract = db.get(Contract, int(item.reference_id))
            if contract is not None:
                reference["record"] = {
                    "number": contract.number,
                    "object": contract.object_description,
                    "supplier": contract.supplier.name if contract.supplier else None,
                    "global_value": float(contract.global_value or 0),
                    "source_url": contract.source_url,
                }
                records.append(reference)
                continue
        if item.reference_type == "finding" and item.reference_id:
            finding = db.scalar(
                select(AuditFinding).where(AuditFinding.public_id == item.reference_id)
            )
            if finding:
                findings.append(reference)
                continue

        if item.kind.value == "note":
            notes.append(reference)
        elif item.kind.value == "document":
            documents.append(reference)
        else:
            records.append(reference)

    return {
        "title": investigation.title,
        "description": investigation.description,
        "public_id": investigation.public_id,
        "status": investigation.status.value,
        "scope": investigation.scope,
        "tags": investigation.tags or [],
        "created_at": investigation.created_at.isoformat(),
        "generated_at": datetime.now(UTC).isoformat(),
        "records": records,
        "findings": findings,
        "notes": notes,
        "documents": documents,
        "methodology": (
            "Os dados provêm de fontes públicas oficiais (PNCP e demais portais). "
            "Cálculos financeiros são determinísticos e reproduzíveis. Achados são "
            "indicadores automáticos, não conclusões de irregularidade."
        ),
        "limitations": (
            "Este relatório reúne informações públicas para fins de pesquisa e "
            "controle social. Não constitui acusação, laudo pericial ou conclusão "
            "de órgão competente. Diferenças de contexto contratual podem explicar "
            "variações observadas."
        ),
        "oversight_guidance": OVERSIGHT_GUIDANCE,
    }


def render_pdf(report: dict) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=2 * cm
    )
    styles = getSampleStyleSheet()
    body = styles["BodyText"]
    title_style = ParagraphStyle("Title2", parent=styles["Title"], fontSize=18)
    h2 = ParagraphStyle("H2", parent=styles["Heading2"], spaceBefore=12)

    story = [Paragraph("Rastro Público — Relatório de Evidências", styles["Title"])]
    story.append(Paragraph(report["title"], title_style))
    story.append(Spacer(1, 6))
    story.append(Paragraph(f"Identificador: {report['public_id']}", body))
    story.append(Paragraph(f"Gerado em: {report['generated_at']}", body))
    if report.get("description"):
        story.append(Paragraph(report["description"], body))

    story.append(Paragraph("Escopo", h2))
    story.append(Paragraph(str(report.get("scope") or "Não especificado"), body))

    story.append(Paragraph("Registros públicos citados", h2))
    if report["records"]:
        for record in report["records"]:
            text = f"<b>{record['title']}</b><br/>{record.get('note') or ''}"
            if record.get("record"):
                text += f"<br/>Dados: {record['record']}"
            if record.get("source_url"):
                text += f"<br/>Fonte: {record['source_url']}"
            story.append(Paragraph(text, body))
            story.append(Spacer(1, 6))
    else:
        story.append(Paragraph("Nenhum registro citado.", body))

    story.append(Paragraph("Achados de auditoria associados", h2))
    story.append(
        Paragraph(
            "Achados são indicadores automáticos para verificação, não conclusões de irregularidade.",
            body,
        )
    )
    for finding in report["findings"]:
        story.append(Paragraph(f"<b>{finding['title']}</b> — {finding.get('note') or ''}", body))

    story.append(Paragraph("Metodologia", h2))
    story.append(Paragraph(report["methodology"], body))

    story.append(Paragraph("Limitações e explicações alternativas", h2))
    story.append(Paragraph(report["limitations"], body))

    story.append(Paragraph("Como encaminhar uma denúncia", h2))
    for guidance in report["oversight_guidance"]:
        story.append(
            Paragraph(f"<b>{guidance['orgao']}</b>: {guidance['descricao']} ({guidance['url']})", body)
        )

    doc.build(story)
    return buffer.getvalue()
