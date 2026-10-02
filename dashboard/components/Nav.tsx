"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";

const ITEMS = [
  { href: "/", label: "Semana siguiente", match: (p: string) => p === "/" || p.startsWith("/cuenta/") },
  { href: "/cuentas", label: "Cuentas", match: (p: string) => p.startsWith("/cuentas") },
  { href: "/oportunidades", label: "Oportunidades", match: (p: string) => p.startsWith("/oportunidades") },
  { href: "/tasas", label: "Tasas", match: (p: string) => p.startsWith("/tasas") },
];

export default function Nav() {
  const path = usePathname();
  const router = useRouter();
  if (path.startsWith("/login")) return null;
  async function salir() {
    await createClient().auth.signOut();
    router.push("/login");
    router.refresh();
  }
  return (
    <header className="topbar">
      <div className="topbar-in">
        <span className="brand">Visual Trans <span className="muted" style={{ fontWeight: 500 }}>Prospección</span></span>
        <nav className="nav">
          {ITEMS.map((i) => (
            <Link key={i.href} href={i.href} className={i.match(path) ? "active" : ""}>
              {i.label}
            </Link>
          ))}
        </nav>
        <button className="link" onClick={salir}>Salir</button>
      </div>
    </header>
  );
}
