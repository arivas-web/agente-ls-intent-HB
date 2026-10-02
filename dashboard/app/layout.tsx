import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Nav from "@/components/Nav";

const inter = Inter({ subsets: ["latin"], variable: "--font", display: "swap" });

export const metadata: Metadata = { title: "Visual Trans · Prospección", description: "Dashboard de lead scoring" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body className={inter.variable}>
        <Nav />
        <main>{children}</main>
      </body>
    </html>
  );
}
