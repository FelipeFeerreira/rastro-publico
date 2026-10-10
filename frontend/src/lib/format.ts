const currency = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
  maximumFractionDigits: 2,
});

const compact = new Intl.NumberFormat("pt-BR", {
  notation: "compact",
  maximumFractionDigits: 1,
});

const number = new Intl.NumberFormat("pt-BR");

export function formatCurrency(value?: number | string | null): string {
  if (value === null || value === undefined || value === "") return "—";
  const num = typeof value === "string" ? Number(value) : value;
  if (Number.isNaN(num)) return "—";
  return currency.format(num);
}

export function formatCompact(value?: number | string | null): string {
  if (value === null || value === undefined || value === "") return "—";
  const num = typeof value === "string" ? Number(value) : value;
  if (Number.isNaN(num)) return "—";
  return "R$ " + compact.format(num);
}

export function formatNumber(value?: number | string | null): string {
  if (value === null || value === undefined || value === "") return "—";
  const num = typeof value === "string" ? Number(value) : value;
  if (Number.isNaN(num)) return "—";
  return number.format(num);
}

export function formatDate(value?: string | null): string {
  if (!value) return "—";
  const date = new Date(value.length <= 10 ? `${value}T00:00:00` : value);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleDateString("pt-BR");
}

export function formatDateTime(value?: string | null): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
}

export function formatDocument(doc?: string | null): string {
  if (!doc) return "—";
  const digits = doc.replace(/\D/g, "");
  if (digits.length === 14) {
    return digits.replace(/^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})$/, "$1.$2.$3/$4-$5");
  }
  if (digits.length === 11) {
    return digits.replace(/^(\d{3})(\d{3})(\d{3})(\d{2})$/, "$1.$2.$3-$4");
  }
  return doc;
}

export function modalityLabel(value?: string | null): string {
  const labels: Record<string, string> = {
    "1": "Leilão",
    "2": "Diálogo competitivo",
    "3": "Concorrência",
    "4": "Concurso",
    "5": "Pregão",
    "6": "Dispensa",
    "7": "Inexigibilidade",
    "8": "Manifestação de interesse",
    "9": "Pré-qualificação",
    "10": "Credenciamento",
    "11": "Leilão eletrônico",
    "12": "Diálogo competitivo eletrônico",
    "13": "Concorrência eletrônica",
    "0": "Não informada",
  };
  return value ? labels[value] ?? value : "—";
}
