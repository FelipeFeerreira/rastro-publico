import Link from "next/link";
import { SearchX } from "lucide-react";

import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <div className="container flex flex-col items-center justify-center py-24 text-center">
      <SearchX className="size-10 text-muted-foreground" />
      <h1 className="mt-4 text-2xl font-semibold">Página não encontrada</h1>
      <p className="mt-2 max-w-md text-sm text-muted-foreground">
        O registro pode ter sido removido na fonte, ainda não estar sincronizado ou o
        endereço estar incorreto.
      </p>
      <div className="mt-6 flex gap-2">
        <Button asChild>
          <Link href="/busca">Ir para a busca</Link>
        </Button>
        <Button asChild variant="outline">
          <Link href="/">Página inicial</Link>
        </Button>
      </div>
    </div>
  );
}
