"use client";

import * as React from "react";
import Link from "next/link";
import { BookmarkPlus, Check, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  addEvidence,
  createInvestigation,
  listInvestigations,
} from "@/lib/api";
import type { Investigation } from "@/lib/types";

interface Props {
  recordType: "procurement" | "contract" | "finding";
  recordId: number | string;
  title: string;
  sourceUrl?: string | null;
}

export function AddToInvestigation({ recordType, recordId, title, sourceUrl }: Props) {
  const [open, setOpen] = React.useState(false);
  const [token, setToken] = React.useState<string | null>(null);
  const [items, setItems] = React.useState<Investigation[]>([]);
  const [newTitle, setNewTitle] = React.useState("");
  const [status, setStatus] = React.useState<"idle" | "loading" | "saved" | "error">("idle");

  React.useEffect(() => {
    setToken(localStorage.getItem("rp_token"));
  }, []);

  React.useEffect(() => {
    if (!open || !token) return;
    setStatus("loading");
    listInvestigations(token)
      .then((data) => {
        setItems(data);
        setStatus("idle");
      })
      .catch(() => setStatus("error"));
  }, [open, token]);

  const save = async (investigationId?: number) => {
    if (!token) return;
    setStatus("loading");
    try {
      let publicId: string | undefined;
      if (investigationId) {
        const found = items.find((item) => item.id === investigationId);
        publicId = found?.public_id;
      } else if (newTitle.trim()) {
        const created = await createInvestigation(token, { title: newTitle.trim() });
        publicId = created.public_id;
      }
      if (!publicId) return;
      await addEvidence(token, publicId, {
        kind: "record",
        title: title.slice(0, 280),
        reference_type: recordType,
        reference_id: String(recordId),
        source_url: sourceUrl ?? null,
      });
      setStatus("saved");
      setTimeout(() => setOpen(false), 1200);
    } catch {
      setStatus("error");
    }
  };

  if (!token) {
    return (
      <Button asChild variant="outline" size="sm">
        <Link href="/entrar">
          <BookmarkPlus className="size-4" /> Entrar para salvar
        </Link>
      </Button>
    );
  }

  return (
    <div className="relative">
      <Button variant="outline" size="sm" onClick={() => setOpen((value) => !value)}>
        <BookmarkPlus className="size-4" /> Salvar em investigação
      </Button>
      {open && (
        <div className="absolute right-0 z-40 mt-2 w-80 rounded-lg border bg-popover p-4 shadow-lg animate-fade-in">
          {status === "saved" ? (
            <p className="flex items-center gap-2 text-sm text-success">
              <Check className="size-4" /> Registro salvo como evidência.
            </p>
          ) : (
            <div className="space-y-3">
              <p className="text-sm font-medium">Salvar registro</p>
              {items.length > 0 && (
                <div className="max-h-40 space-y-1 overflow-auto">
                  {items.map((item) => (
                    <button
                      key={item.id}
                      className="w-full rounded-md px-2 py-1.5 text-left text-sm hover:bg-accent"
                      onClick={() => save(item.id)}
                    >
                      {item.title}
                    </button>
                  ))}
                </div>
              )}
              <div className="space-y-2 border-t pt-3">
                <Input
                  placeholder="Nova investigação…"
                  value={newTitle}
                  onChange={(event) => setNewTitle(event.target.value)}
                />
                <Button
                  size="sm"
                  className="w-full"
                  disabled={!newTitle.trim() || status === "loading"}
                  onClick={() => save()}
                >
                  {status === "loading" ? (
                    <Loader2 className="size-4 animate-spin" />
                  ) : (
                    "Criar e salvar"
                  )}
                </Button>
              </div>
              {status === "error" && (
                <p className="text-xs text-destructive">
                  Não foi possível salvar. Tente novamente.
                </p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
