import { expect, test } from "@playwright/test";

test.describe("Fluxo essencial do Rastro Público", () => {
  test("a página inicial apresenta a pergunta principal e a busca", async ({ page }) => {
    await page.goto("/");
    await expect(
      page.getByRole("heading", { name: "Para onde vai o dinheiro público?" }),
    ).toBeVisible();
    await expect(page.getByRole("search").getByRole("textbox")).toBeVisible();
  });

  test("a página de busca aceita consulta e mostra contexto", async ({ page }) => {
    await page.goto("/busca?q=computadores");
    await expect(page.getByText(/resultados para/i)).toBeVisible();
  });

  test("as páginas de transparência estão acessíveis", async ({ page }) => {
    await page.goto("/metodologia");
    await expect(page.getByRole("heading", { name: "Metodologia" })).toBeVisible();

    await page.goto("/fontes");
    await expect(page.getByRole("heading", { name: "Fontes de dados" })).toBeVisible();

    await page.goto("/limitacoes");
    await expect(page.getByRole("heading", { name: "Limitações" })).toBeVisible();

    await page.goto("/privacidade");
    await expect(page.getByRole("heading", { name: "Privacidade e LGPD" })).toBeVisible();
  });

  test("o assistente explica terminologia", async ({ page }) => {
    await page.goto("/assistente");
    await expect(page.getByRole("heading", { name: "Assistente de pesquisa" })).toBeVisible();
  });
});
