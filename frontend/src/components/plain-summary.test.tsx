import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { ContractPlainSummary } from "./plain-summary";

describe("ContractPlainSummary", () => {
  it("responde as perguntas do cidadão em linguagem simples", () => {
    render(
      <ContractPlainSummary
        data={{
          objectDescription: "Compra de computadores",
          contractorName: "IFSP - Campus Salto",
          supplierName: "Empresa Exemplo LTDA",
          date: "2024-01-10",
          contractedValue: 19045.32,
          committedValue: 20000,
          liquidatedValue: 5000,
          paidValue: 2500,
        }}
      />,
    );

    expect(screen.getByText("Quem contratou?")).toBeInTheDocument();
    expect(screen.getByText("Quem recebeu o dinheiro?")).toBeInTheDocument();
    expect(screen.getByText("Quanto foi realmente pago?")).toBeInTheDocument();
    expect(screen.getByText("IFSP - Campus Salto")).toBeInTheDocument();
    expect(screen.getByText("Empresa Exemplo LTDA")).toBeInTheDocument();
    // O valor pago aparece separado do contratado.
    expect(screen.getByText(/R\$\s?2\.500,00/)).toBeInTheDocument();
  });
});
