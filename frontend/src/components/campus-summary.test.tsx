import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { CampusFinancialCards } from "./campus-summary";

describe("CampusFinancialCards", () => {
  it("mostra os quatro estágios separadamente", () => {
    render(
      <CampusFinancialCards
        values={{
          contracted: 17015527.51,
          committed: 14700551.7,
          liquidated: 139967.62,
          paid: 8212820.59,
        }}
      />,
    );

    expect(screen.getByText("Contratado")).toBeInTheDocument();
    expect(screen.getByText("Empenhado")).toBeInTheDocument();
    expect(screen.getByText("Liquidado")).toBeInTheDocument();
    expect(screen.getByText("Pago")).toBeInTheDocument();

    // Contratado nunca aparece igual ao pago.
    expect(screen.getByTestId("financial-contracted")).toHaveTextContent(/17\.015\.527,51/);
    expect(screen.getByTestId("financial-paid")).toHaveTextContent(/8\.212\.820,59/);
    expect(screen.getByTestId("financial-contracted")).not.toHaveTextContent("8.212.820,59");
  });
});
