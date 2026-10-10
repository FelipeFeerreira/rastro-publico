import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { EmptyState, ErrorState, SeverityBadge, StatCard } from "./common";

describe("EmptyState", () => {
  it("mostra título e descrição", () => {
    render(<EmptyState title="Nada por aqui" description="Sem registros" />);
    expect(screen.getByText("Nada por aqui")).toBeInTheDocument();
    expect(screen.getByText("Sem registros")).toBeInTheDocument();
  });
});

describe("ErrorState", () => {
  it("mostra mensagem de erro acessível", () => {
    render(<ErrorState title="Falha" description="Tente novamente" />);
    expect(screen.getByRole("heading", { name: "Falha" })).toBeInTheDocument();
  });
});

describe("StatCard", () => {
  it("renderiza rótulo e valor", () => {
    render(<StatCard label="Contratações" value="50" />);
    expect(screen.getByText("Contratações")).toBeInTheDocument();
    expect(screen.getByText("50")).toBeInTheDocument();
  });
});

describe("SeverityBadge", () => {
  it("traduz severidade", () => {
    render(<SeverityBadge severity="relevante" />);
    expect(screen.getByText("Relevante")).toBeInTheDocument();
  });
});
