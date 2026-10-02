import Link from "next/link";
import { notFound } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { loadAccount } from "@/lib/account";
import AccountDetail from "@/components/AccountDetail";
import { DbError } from "@/components/ui";

export const dynamic = "force-dynamic";

export default async function CuentaFicha({ params }: { params: { id: string } }) {
  try {
    const data = await loadAccount(createClient(), decodeURIComponent(params.id));
    if (!data) notFound();
    return (
      <>
        <p><Link href="/cuentas">← Cuentas</Link></p>
        <AccountDetail data={data} showHistory />
      </>
    );
  } catch (e) {
    if (e && typeof e === "object" && "digest" in e) throw e;
    return <DbError error={e} />;
  }
}
