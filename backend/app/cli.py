"""Interface de linha de comando: seed, ingestão, auditoria e estatísticas.

Uso:
    python -m app.cli seed
    python -m app.cli ingest pncp --data-inicial 2026-01-01 --data-final 2026-01-07
    python -m app.cli audit --limit 200
    python -m app.cli stats
"""

from __future__ import annotations

import argparse
from datetime import date

from sqlalchemy import func, select

from app.core.logging import configure_logging
from app.db.session import session_scope
from app.models.audit import AuditFinding
from app.models.procurement import Contract, Payment, Procurement, ProcurementResult
from app.models.supplier import Supplier
from app.services.analysis.engine import AuditEngine, ensure_rules
from app.services.ingestion import IngestionService
from app.services.reference_data import seed_reference_data


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def cmd_seed(_: argparse.Namespace) -> None:
    with session_scope() as db:
        created = seed_reference_data(db)
        ensure_rules(db)
    print(f"Dados de referência criados: {created}")


def cmd_ingest(args: argparse.Namespace) -> None:
    if args.source != "pncp":
        raise SystemExit("Fonte não suportada. Use 'pncp'.")
    start = _parse_date(args.data_inicial)
    end = _parse_date(args.data_final)
    modalities = [int(m) for m in args.modalidades.split(",")] if args.modalidades else None
    with session_scope() as db:
        service = IngestionService(db)
        run = service.ingest_pncp_publications(
            start,
            end,
            modality_codes=modalities,
            uf=args.uf,
            municipality_ibge=args.municipio,
            cnpj=args.cnpj,
            with_items=args.com_itens,
            max_pages_per_modality=args.max_paginas,
        )
    print(
        f"Execução #{run.id} [{run.status.value}] "
        f"coletados={run.records_fetched} inseridos={run.records_inserted} "
        f"atualizados={run.records_updated} erros={run.error_count}"
    )


def cmd_contracts(args: argparse.Namespace) -> None:
    start = _parse_date(args.data_inicial)
    end = _parse_date(args.data_final)
    with session_scope() as db:
        run = IngestionService(db).ingest_pncp_contracts(
            start, end, cnpj=args.cnpj, max_pages=args.max_paginas
        )
    print(
        f"Execução #{run.id} [{run.status.value}] coletados={run.records_fetched} "
        f"inseridos={run.records_inserted} atualizados={run.records_updated}"
    )


def cmd_comprasnet(args: argparse.Namespace) -> None:
    with session_scope() as db:
        run = IngestionService(db).ingest_comprasnet_contracts(
            args.uasg,
            include_inactive=not args.sem_inativos,
            municipality_ibge=args.municipio,
            municipality_name=args.nome_municipio,
            uf=args.uf,
            max_contracts=args.max,
        )
    print(
        f"Execução #{run.id} [{run.status.value}] UASG {args.uasg} "
        f"coletados={run.records_fetched} inseridos={run.records_inserted} "
        f"atualizados={run.records_updated} erros={run.error_count}"
    )


def cmd_comprasnet_pagamentos(args: argparse.Namespace) -> None:
    with session_scope() as db:
        run = IngestionService(db).ingest_comprasnet_payments(
            args.uasg,
            max_contracts=args.max,
        )
    print(
        f"Execução #{run.id} [{run.status.value}] UASG {args.uasg} "
        f"contratos={run.records_fetched} lançamentos+={run.records_inserted} "
        f"atualizados={run.records_updated} erros={run.error_count}"
    )


def cmd_servidores(args: argparse.Namespace) -> None:
    with session_scope() as db:
        run = IngestionService(db).ingest_transparencia_servidores(
            args.orgao,
            args.mes,
            campus_uorg=args.campus,
            max_servidores=args.max,
        )
    print(
        f"Execução #{run.id} [{run.status.value}] órgão {args.orgao} mês {args.mes} "
        f"servidores={run.records_fetched} inseridos={run.records_inserted} "
        f"atualizados={run.records_updated} erros={run.error_count}"
    )
    if run.error_count:
        print("Observação:", run.message)


def cmd_audit(args: argparse.Namespace) -> None:
    with session_scope() as db:
        created = AuditEngine(db).run_scan(limit=args.limit)
    print(f"Achados gerados/atualizados: {created}")


def cmd_stats(_: argparse.Namespace) -> None:
    with session_scope() as db:
        def count(model) -> int:
            return int(db.scalar(select(func.count()).select_from(model)) or 0)

        comprasnet_contracts = int(
            db.scalar(
                select(func.count())
                .select_from(Contract)
                .where(Contract.source_system == "comprasnet")
            )
            or 0
        )
        print("Estatísticas da base local:")
        print(f"  Contratações:          {count(Procurement)}")
        print(f"  Resultados de item:    {count(ProcurementResult)}")
        print(f"  Contratos:             {count(Contract)}")
        print(f"  Contratos (Comprasnet):{comprasnet_contracts}")
        print(f"  Pagamentos (estágios): {count(Payment)}")
        print(f"  Fornecedores:          {count(Supplier)}")
        print(f"  Achados:               {count(AuditFinding)}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="rastro", description="Rastro Público CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("seed", help="Cria UFs, fontes e regras de auditoria").set_defaults(
        func=cmd_seed
    )

    ingest = sub.add_parser("ingest", help="Ingere contratações do PNCP")
    ingest.add_argument("source", choices=["pncp"], default="pncp", nargs="?")
    ingest.add_argument("--data-inicial", required=True)
    ingest.add_argument("--data-final", required=True)
    ingest.add_argument("--uf")
    ingest.add_argument("--municipio", help="Código IBGE do município")
    ingest.add_argument("--cnpj", help="CNPJ do órgão")
    ingest.add_argument("--modalidades", help="Códigos separados por vírgula")
    ingest.add_argument("--max-paginas", type=int, default=None)
    ingest.add_argument("--com-itens", action="store_true", help="Também buscar itens/resultados")
    ingest.set_defaults(func=cmd_ingest)

    contracts = sub.add_parser("contracts", help="Ingere contratos do PNCP")
    contracts.add_argument("--data-inicial", required=True)
    contracts.add_argument("--data-final", required=True)
    contracts.add_argument("--cnpj")
    contracts.add_argument("--max-paginas", type=int, default=None)
    contracts.set_defaults(func=cmd_contracts)

    comprasnet = sub.add_parser(
        "comprasnet", help="Importa contratos do Comprasnet por unidade gestora (UASG)"
    )
    comprasnet.add_argument("--uasg", required=True, help="Código da unidade gestora (ex.: 158364)")
    comprasnet.add_argument("--sem-inativos", action="store_true", help="Não importar inativos")
    comprasnet.add_argument("--municipio", help="Código IBGE do município (ex.: 3545209)")
    comprasnet.add_argument("--nome-municipio", help="Nome do município (ex.: Salto)")
    comprasnet.add_argument("--uf", help="UF da unidade (ex.: SP)")
    comprasnet.add_argument("--max", type=int, default=None, help="Limite de contratos processados")
    comprasnet.set_defaults(func=cmd_comprasnet)

    pagamentos = sub.add_parser(
        "comprasnet-pagamentos",
        help="Importa empenhos (empenhado/liquidado/pago) e faturas liquidadas de uma UASG",
    )
    pagamentos.add_argument("--uasg", required=True, help="Código da unidade gestora")
    pagamentos.add_argument("--max", type=int, default=None, help="Limite de contratos")
    pagamentos.set_defaults(func=cmd_comprasnet_pagamentos)

    servidores = sub.add_parser(
        "transparencia-servidores",
        help="Importa servidores e remunerações do Portal da Transparência (exige TRANSPARENCIA_API_KEY)",
    )
    servidores.add_argument("--orgao", required=True, help="Código SIAFI do órgão (ex.: 26439)")
    servidores.add_argument("--mes", required=True, help="Mês/ano de referência (AAAAMM, ex.: 202501)")
    servidores.add_argument("--campus", help="UORG do campus (ex.: 'IFSP - CAMPUS SALTO')")
    servidores.add_argument("--max", type=int, default=None, help="Limite de servidores")
    servidores.set_defaults(func=cmd_servidores)

    audit = sub.add_parser("audit", help="Executa o motor de auditoria")
    audit.add_argument("--limit", type=int, default=500)
    audit.set_defaults(func=cmd_audit)

    sub.add_parser("stats", help="Mostra estatísticas da base").set_defaults(func=cmd_stats)
    return parser


def main() -> None:
    configure_logging()
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
