import Link from "next/link";

import { SeverityBadge } from "@/components/common";
import { Card, CardContent } from "@/components/ui/card";
import type { Finding } from "@/lib/types";
import { formatDate } from "@/lib/format";

export function FindingCard({ finding }: { finding: Finding }) {
  return (
    <Link href={`/achados/${finding.public_id}`}>
      <Card className="transition-colors hover:border-primary/40">
        <CardContent className="p-5">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <SeverityBadge severity={finding.severity} />
                <span className="text-xs text-muted-foreground">{finding.public_id}</span>
              </div>
              <p className="mt-2 text-sm font-medium">{finding.title}</p>
              <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">{finding.summary}</p>
            </div>
            <span className="text-xs text-muted-foreground">{formatDate(finding.created_at)}</span>
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}
