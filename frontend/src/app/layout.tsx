import type { Metadata, Viewport } from "next";

import { Footer } from "@/components/layout/footer";
import { Header } from "@/components/layout/header";
import { ThemeProvider } from "@/components/layout/theme-provider";

import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "Rastro Público — Para onde vai o dinheiro público?",
    template: "%s · Rastro Público",
  },
  description:
    "Pesquise, entenda e investigue como os recursos públicos são utilizados no Brasil. Plataforma independente de transparência de gastos públicos.",
  applicationName: "Rastro Público",
  keywords: [
    "transparência",
    "gastos públicos",
    "contratações públicas",
    "PNCP",
    "licitações",
    "controle social",
  ],
  robots: { index: true, follow: true },
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#ffffff" },
    { media: "(prefers-color-scheme: dark)", color: "#0b1220" },
  ],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR" suppressHydrationWarning>
      <body className="min-h-dvh font-sans">
        <ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
          <div className="flex min-h-dvh flex-col">
            <Header />
            <main className="flex-1">{children}</main>
            <Footer />
          </div>
        </ThemeProvider>
      </body>
    </html>
  );
}
