import { describe, expect, it } from "vitest";

import {
  formatCompact,
  formatCurrency,
  formatDate,
  formatDocument,
  formatNumber,
  modalityLabel,
} from "./format";

describe("formatCurrency", () => {
  it("formata valores em reais", () => {
    expect(formatCurrency(1234.5)).toContain("1.234,50");
    expect(formatCurrency("175000")).toContain("175.000,00");
  });

  it("trata valores ausentes", () => {
    expect(formatCurrency(null)).toBe("—");
    expect(formatCurrency(undefined)).toBe("—");
  });
});

describe("formatNumber", () => {
  it("formata inteiros", () => {
    expect(formatNumber(1000)).toBe("1.000");
    expect(formatNumber(0)).toBe("0");
  });
});

describe("formatCompact", () => {
  it("compacta grandes valores", () => {
    expect(formatCompact(1_500_000)).toBeTruthy();
    expect(formatCompact(null)).toBe("—");
  });
});

describe("formatDocument", () => {
  it("formata CNPJ e CPF", () => {
    expect(formatDocument("12345678000199")).toBe("12.345.678/0001-99");
    expect(formatDocument("12345678900")).toBe("123.456.789-00");
  });
});

describe("formatDate", () => {
  it("formata datas ISO", () => {
    expect(formatDate("2026-01-15")).toBe("15/01/2026");
    expect(formatDate(null)).toBe("—");
  });
});

describe("modalityLabel", () => {
  it("traduz códigos de modalidade", () => {
    expect(modalityLabel("6")).toBe("Dispensa");
    expect(modalityLabel("5")).toBe("Pregão");
  });
});
