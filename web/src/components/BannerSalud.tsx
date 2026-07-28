import type { Estado, Salud } from "@/lib/api";
import { cn } from "@/lib/utils";

/** Un servicio degradado no se calla — ley de la casa desde el incidente real que
 *  la sostiene: `/health` decía `ok` con el indexador muerto [servicio.py, comentario
 *  "Me lo autoinfligí el 2026-07-27"]. `role="status"` (no `alert`): es un estado
 *  del sistema que se anuncia, no un error del usuario que interrumpe [brief §5.7].
 *
 *  El contenedor se monta SIEMPRE (nunca condicionalmente) para que el rol de live
 *  region esté presente desde el primer render — si se inyectase ya con contenido
 *  tras la carga, algunos lectores de pantalla no lo anuncian [brief §7, "top
 *  gotchas"]. Se oculta con `hidden`, no se desmonta. */
export function BannerSalud({ salud, estado }: { salud: Salud | undefined; estado: Estado[] | undefined }) {
  const desaparecidas = (estado ?? []).reduce((a, x) => a + x.desaparecidas, 0);
  const hayAviso = Boolean(salud) && (!salud!.ok || desaparecidas > 0);
  // Dos causas distintas, mismo componente — la desaparición de entradas manda
  // sobre el indexador desfasado si ambas ocurren a la vez [ui.html `arrancar`].
  const mensaje = !hayAviso
    ? null
    : desaparecidas > 0
      ? `${desaparecidas} entrada${desaparecidas === 1 ? "" : "s"} que estuvieron y ya no están. Un ledger de sólo-apéndice no pierde entradas: mira \`llmi verify\`.`
      : `El indexador no está al día (${salud?.indexador.error ?? "sin detalle"}). Lo que ves puede no reflejar el fichero.`;
  return (
    <div
      role="status"
      className={cn(
        "mx-4 mt-2.5 rounded-r border-l-[3px] border-aviso bg-lacre-d px-2.5 py-2 text-xs text-tinta [overflow-wrap:anywhere]",
        !mensaje && "hidden",
      )}
    >
      {mensaje && <>⚠ {mensaje}</>}
    </div>
  );
}
