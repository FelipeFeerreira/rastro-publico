import Link from "next/link";
import { notFound } from "next/navigation";
import { ExternalLink } from "lucide-react";

import { DataNotice } from "@/components/common";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ApiError, getServidor } from "@/lib/api";
import { formatCurrency } from "@/lib/format";

const MONTHS = [
  "janeiro", "fevereiro", "março", "abril", "maio", "junho",
  "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
];

export default async function ServidorPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  let person;
  try {
    person = await getServidor(id);
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) notFound();
    throw err;
  }

  return (
    <div className="container max-w-4xl py-10">
      <nav className="mb-4 text-sm text-muted-foreground">
        <Link href="/salarios" className="hover:text-foreground">
          Servidores
        </Link>
        <span className="mx-2">/</span>
        <span>{person.name}</span>
      </nav>

      <h1 className="text-2xl font-semibold tracking-tight">{person.name}</h1>
      <div className="mt-2 flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
        {person.role_title && <span>{person.role_title}</span>}
        {person.entity_name && <Badge variant="secondary">{person.entity_name}</Badge>}
      </div>

      <section className="mt-8">
        <h2 className="mb-3 text-lg font-semibold tracking-tight">Remuneração por mês</h2>
        <Card>
          <CardContent className="overflow-x-auto p-0">
            {person.remunerations.length === 0 ? (
              <p className="p-6 text-sm text-muted-foreground">
                Nenhuma remuneração registrada para esta pessoa.
              </p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Mês de referência</TableHead>
                    <TableHead className="text-right">Bruto</TableHead>
                    <TableHead className="text-right">Líquido</TableHead>
                    <TableHead>Fonte</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {person.remunerations.map((rem) => (
                    <TableRow key={rem.id}>
                      <TableCell>
                        {rem.reference_year && rem.reference_month
                          ? `${MONTHS[rem.reference_month - 1] ?? rem.reference_month}/${rem.reference_year}`
                          : "—"}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {formatCurrency(rem.gross_amount)}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {formatCurrency(rem.net_amount)}
                      </TableCell>
                      <TableCell>
                        {rem.source_url ? (
                          <a
                            href={rem.source_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 text-primary hover:underline"
                          >
                            <ExternalLink className="size-3.5" /> oficial
                          </a>
                        ) : (
                          "—"
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
        <div className="mt-3">
          <DataNotice>
            Valores brutos e líquidos conforme publicados pelo órgão. “Bruto” é antes dos
            descontos; “líquido” é após os descontos obrigatórios.
          </DataNotice>
        </div>
      </section>
    </div>
  );
}
