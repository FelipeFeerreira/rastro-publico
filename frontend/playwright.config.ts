import { defineConfig, devices } from "@playwright/test";

/**
 * Testes end-to-end essenciais.
 * Exigem a stack em execução (docker compose up) ou os servidores locais:
 *   - frontend em http://localhost:3000
 *   - API em http://localhost:8000
 */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: "list",
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:3000",
    trace: "on-first-retry",
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
    { name: "mobile", use: { ...devices["Pixel 7"] } },
  ],
});
