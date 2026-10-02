import Link from "next/link";
import { notFound } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { loadAccount } from "@/lib/account";
import AccountDetail from "@/components/AccountDetail";
import { DbError } from "@/components/ui";

export const dynamic = "force-dynamic";

/** Detalle de una cuenta dentro de un borrador: /cuenta/[id]?draft=ID */
export default async function CuentaDeBorrador({ params, searchParams }: { params: { id: string }; searchParams: { draft?: string } }) {
  const draftId = searchParams.draft ? Number(searchParams.draft) : null;
  try {
    const data = await loadAccount(createClient(), decodeURIComponent(params.id), draftId);
    if (!data) notFound();
    return (
      <>
        <p>
          <Link href={draftId ? `/?draft=${draftId}` : "/"}>← Semana siguiente</Link>
          {" · "}<Link href={`/cuentas/${encodeURIComponent(data.company.hs_id)}`}>Ver ficha completa e histórico</Link>
        </p>
        <AccountDetail data={data} />
      </>
    );
  } catch (e) {
    if (e && typeof e === "object" && "digest" in e) throw e;
    return <DbError error={e} />;
  }
}
