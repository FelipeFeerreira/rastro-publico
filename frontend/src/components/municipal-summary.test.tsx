import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import {
  DESCRIPTION_FALLBACK,
  ExpenseDescription,
  InstitutionBreakdown,
  MunicipalFinancialCards,
  describeCoverage,
} from "./municipal-summary";
import type { MunicipalExpenseTotals } from "@/lib/types";

const TOTALS: MunicipalExpenseTotals = {
  records: 72223,
  empenhado: 1600759650.83,
  liquidado: 1259830012.93,
  pago: 1251683160.36,
  reforco: 0,
  anulacao: 133137693.29,
  committed_net: 1467621957.54,
  coverage: {
    first_date: "2025-01-02",
    last_date: "2026-08-31",
    last_collected_at: "2026-10-11T22:58:24Z",
    months_by_year: { "2025": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12], "2026": [1, 2, 3, 4, 5, 6, 7, 8] },
    partial_years: [2026],
  },
};

describe("MunicipalFinancialCards", () => {
  it("mostra os estágios separados, com o pago em destaque", () => {
    render(<MunicipalFinancialCards totals={TOTALS} />);
    expect(screen.getByText("Pago")).toBeInTheDocument();
    expect(screen.getByText("Empenhado")).toBeInTheDocument();
    expect(screen.getByText("Liquidado")).toBeInTheDocument();
    expect(screen.getByText("Anulado")).toBeInTheDocument();

    expect(screen.getByTestId("municipal-pago")).toHaveTextContent(/1\.251\.683\.160,36/);
    expect(screen.getByTestId("municipal-empenhado")).toHaveTextContent(/1\.600\.759\.650,83/);
    // Nunca iguais: estágios não são somados nem confundidos.
    expect(screen.getByTestId("municipal-pago")).not.toHaveTextContent("1.600.759.650,83");
  });
});

describe("describeCoverage", () => {
  it("marca o ano parcial", () => {
    const cov = describeCoverage(TOTALS.coverage);
    expect(cov).not.toBeNull();
    expect(cov?.hasPartial).toBe(true);
    const y2026 = cov?.perYear.find((y) => y.year === "2026");
    expect(y2026?.partial).toBe(true);
    expect(y2026?.label).toBe("jan–ago");
    const y2025 = cov?.perYear.find((y) => y.year === "2025");
    expect(y2025?.partial).toBe(false);
  });

  it("retorna null sem cobertura", () => {
    expect(describeCoverage(null)).toBeNull();
  });
});

describe("ExpenseDescription", () => {
  it("avisa quando a fonte não informa descrição", () => {
    render(<ExpenseDescription description={null} />);
    expect(screen.getByText(DESCRIPTION_FALLBACK)).toBeInTheDocument();
  });

  it("mostra a descrição quando existe", () => {
    render(<ExpenseDescription description="Compra de material" />);
    expect(screen.getByText("Compra de material")).toBeInTheDocument();
  });
});

describe("InstitutionBreakdown", () => {
  it("separa as instituições e destaca o pago", () => {
    render(
      <InstitutionBreakdown
        items={[
          {
            entity_id: 1,
            entity_name: "PREFEITURA MUNICIPAL DE SALTO",
            records: 56426,
            empenhado: 1377858688.02,
            liquidado: 1000,
            pago: 1109042483.17,
            reforco: 0,
            anulacao: 100,
            committed_net: 1377858588.02,
          },
          {
            entity_id: 2,
            entity_name: "CÂMARA MUNICIPAL DE SALTO",
            records: 2817,
            empenhado: 15822444.08,
            liquidado: 0,
            pago: 14439348.39,
            reforco: 0,
            anulacao: 0,
            committed_net: 15822444.08,
          },
        ]}
      />,
    );
    expect(screen.getByText("PREFEITURA MUNICIPAL DE SALTO")).toBeInTheDocument();
    expect(screen.getByText("CÂMARA MUNICIPAL DE SALTO")).toBeInTheDocument();
  });
});
