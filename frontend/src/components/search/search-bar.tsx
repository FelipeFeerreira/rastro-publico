"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { Loader2, Search } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { suggest } from "@/lib/api";
import type { Suggestion } from "@/lib/types";
import { cn } from "@/lib/utils";

interface SearchBarProps {
  defaultValue?: string;
  size?: "default" | "lg";
  autoFocus?: boolean;
  className?: string;
}

const TYPE_LABEL: Record<string, string> = {
  municipality: "Município",
  entity: "Órgão",
  supplier: "Fornecedor",
  procurement: "Contratação",
};

export function SearchBar({
  defaultValue = "",
  size = "default",
  autoFocus = false,
  className,
}: SearchBarProps) {
  const router = useRouter();
  const [value, setValue] = React.useState(defaultValue);
  const [items, setItems] = React.useState<Suggestion[]>([]);
  const [open, setOpen] = React.useState(false);
  const [loading, setLoading] = React.useState(false);
  const containerRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    const handler = (event: MouseEvent) => {
      if (!containerRef.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  React.useEffect(() => {
    const term = value.trim();
    if (term.length < 2) {
      setItems([]);
      return;
    }
    let active = true;
    setLoading(true);
    const timer = setTimeout(async () => {
      try {
        const results = await suggest(term);
        if (active) {
          setItems(results);
          setOpen(true);
        }
      } catch {
        if (active) setItems([]);
      } finally {
        if (active) setLoading(false);
      }
    }, 220);
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [value]);

  const submit = (event?: React.FormEvent) => {
    event?.preventDefault();
    const term = value.trim();
    if (!term) return;
    setOpen(false);
    router.push(`/busca?q=${encodeURIComponent(term)}`);
  };

  return (
    <div ref={containerRef} className={cn("relative w-full", className)}>
      <form onSubmit={submit} role="search">
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={value}
            autoFocus={autoFocus}
            onChange={(event) => setValue(event.target.value)}
            onFocus={() => items.length > 0 && setOpen(true)}
            placeholder="Busque por órgão, município, fornecedor, contrato ou item"
            aria-label="Buscar"
            className={cn(
              "pl-9 pr-24",
              size === "lg" && "h-14 rounded-xl pl-11 text-base shadow-sm",
            )}
          />
          <div className="absolute right-2 top-1/2 flex -translate-y-1/2 items-center gap-1">
            {loading && <Loader2 className="size-4 animate-spin text-muted-foreground" />}
            <Button type="submit" size={size === "lg" ? "default" : "sm"}>
              Buscar
            </Button>
          </div>
        </div>
      </form>

      {open && items.length > 0 && (
        <div className="absolute z-40 mt-2 w-full overflow-hidden rounded-lg border bg-popover shadow-lg animate-fade-in">
          <ul className="max-h-80 overflow-auto py-1">
            {items.map((item) => (
              <li key={`${item.type}-${item.id}`}>
                <button
                  type="button"
                  className="flex w-full items-center justify-between px-4 py-2 text-left text-sm transition-colors hover:bg-accent"
                  onClick={() => {
                    setOpen(false);
                    if (item.url) router.push(item.url);
                  }}
                >
                  <span className="flex items-center gap-2">
                    <span className="text-muted-foreground">
                      {TYPE_LABEL[item.type] ?? item.type}
                    </span>
                    <span className="font-medium">{item.label}</span>
                  </span>
                  {item.subtitle && (
                    <span className="text-xs text-muted-foreground">{item.subtitle}</span>
                  )}
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
