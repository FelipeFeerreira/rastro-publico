import Link from "next/link";
import { Database, ShieldCheck } from "lucide-react";

const columns = [
  {
    title: "Plataforma",
    links: [
      { href: "/busca", label: "Busca" },
      { href: "/contratacoes", label: "Contratações" },
      { href: "/fornecedores", label: "Empresas e fornecedores" },
      { href: "/orgaos", label: "Órgãos e entidades" },
      { href: "/salarios", label: "Salários de servidores" },
    ],
  },
  {
    title: "Investigar",
    links: [
      { href: "/achados", label: "Achados de auditoria" },
      { href: "/assistente", label: "Assistente de pesquisa" },
      { href: "/investigacoes", label: "Minhas investigações" },
      { href: "/monitoramento", label: "Monitoramento" },
    ],
  },
  {
    title: "Transparência",
    links: [
      { href: "/metodologia", label: "Metodologia" },
      { href: "/fontes", label: "Fontes de dados" },
      { href: "/limitacoes", label: "Limitações" },
      { href: "/privacidade", label: "Privacidade e LGPD" },
    ],
  },
];

export function Footer() {
  return (
    <footer className="mt-20 border-t bg-muted/30">
      <div className="container grid gap-10 py-12 md:grid-cols-2 lg:grid-cols-4">
        <div className="space-y-3">
          <div className="flex items-center gap-2 font-semibold">
            <ShieldCheck className="size-5 text-primary" />
            Rastro Público
          </div>
          <p className="text-sm text-muted-foreground">
            Plataforma independente e apartidária de transparência dos gastos
            públicos brasileiros. Não é um serviço oficial do governo.
          </p>
        </div>
        {columns.map((column) => (
          <div key={column.title}>
            <h3 className="text-sm font-semibold">{column.title}</h3>
            <ul className="mt-3 space-y-2 text-sm text-muted-foreground">
              {column.links.map((link) => (
                <li key={link.href}>
                  <Link className="transition-colors hover:text-foreground" href={link.href}>
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
      <div className="border-t">
        <div className="container flex flex-col gap-2 py-6 text-xs text-muted-foreground md:flex-row md:items-center md:justify-between">
          <p className="flex items-center gap-2">
            <Database className="size-3.5" />
            Dados de fontes públicas oficiais. Valores podem estar desatualizados.
          </p>
          <p>
            Anomalias estatísticas não constituem prova de irregularidade. Verifique
            sempre o registro original.
          </p>
        </div>
      </div>
    </footer>
  );
}
