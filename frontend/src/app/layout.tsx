import type { Metadata } from "next";

import { PriceStreamProvider } from "@/components/PriceStreamProvider";

import "./globals.css";

export const metadata: Metadata = {
  title: "FinAlly — AI Trading Workstation",
  description: "AI-powered trading workstation with live market data",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-bg-base text-text-primary antialiased">
        <PriceStreamProvider>{children}</PriceStreamProvider>
      </body>
    </html>
  );
}