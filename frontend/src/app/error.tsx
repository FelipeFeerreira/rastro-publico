"use client";

import { useEffect } from "react";
import { AlertTriangle } from "lucide-react";

import { Button } from "@/components/ui/button";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Registra no console do cliente; em produção, integraria com observabilidade.
    console.error(error);
  }, [error]);

  return (
    <div className="container flex flex-col items-center justify-center py-24 text-center">
      <AlertTriangle className="size-10 text-destructive" />
      <h1 className="mt-4 text-2xl font-semibold">Algo deu errado</h1>
      <p className="mt-2 max-w-md text-sm text-muted-foreground">
        Ocorreu um erro ao carregar esta página. Você pode tentar novamente; se persistir,
        a fonte de dados pode estar temporariamente indisponível.
      </p>
      <Button className="mt-6" onClick={reset}>
        Tentar novamente
      </Button>
    </div>
  );
}
