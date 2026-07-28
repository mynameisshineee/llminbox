import { forwardRef } from "react";
import { cn } from "@/lib/utils";

type FilaLedger = { ledger: string; entradas: number };

/** Sidebar — marca, lista de ledgers ("todos" siempre primero) y "leer como".
 *  Doble uso: columna fija en desktop (≥760px), drawer `position:fixed` en móvil
 *  [brief §5.1]. El `ref` es para que el padre pueda mover el foco al primer
 *  elemento al abrir el drawer [brief §7, "Dialog no-modal-ligero"]. */
export const Sidebar = forwardRef<HTMLElement, {
  ledgers: FilaLedger[];
  totalLedgers: number;
  ledgerActivo: string;
  onSeleccionar: (ledger: string) => void;
  agentes: string[];
  yo: string;
  onCambiarYo: (nombre: string) => void;
  abierta: boolean;
}>(function Sidebar({ ledgers, totalLedgers, ledgerActivo, onSeleccionar, agentes, yo, onCambiarYo, abierta }, ref) {
  const total = ledgers.reduce((a, x) => a + x.entradas, 0);
  const resumen = totalLedgers > 0 ? `${total.toLocaleString("es")} entradas · ${totalLedgers} ledgers` : "0 ledgers configurados";
  const todas: FilaLedger[] = [{ ledger: "", entradas: total }, ...ledgers];

  return (
    <aside
      id="barra-lateral"
      ref={ref}
      className={cn(
        "fixed inset-y-0 left-0 z-20 flex w-[min(244px,82vw)] -translate-x-full flex-col overflow-y-auto border-r border-linea bg-panel transition-transform duration-[var(--motion-duration-drawer)] ease-[var(--motion-ease-standard)] motion-reduce:transition-none",
        "min-[760px]:static min-[760px]:z-auto min-[760px]:w-auto min-[760px]:translate-x-0 min-[760px]:transition-none",
        abierta && "translate-x-0",
      )}
    >
      <div className="border-b border-linea px-3.5 py-3">
        <b className="font-mono text-[13px] tracking-[-.02em]">llminbox</b>
        <p className="mt-0.5 text-[11px] text-apagado">{resumen}</p>
      </div>
      <nav aria-label="Ledgers" className="p-2">
        <h2 className="mb-1.5 ml-1.5 font-mono text-[10px] uppercase tracking-[.12em] text-apagado">Ledgers</h2>
        {todas.map((x) => (
          <button
            key={x.ledger || "todos"}
            type="button"
            onClick={() => onSeleccionar(x.ledger)}
            aria-current={ledgerActivo === x.ledger || undefined}
            className={cn(
              "flex w-full items-center gap-2 rounded-md px-2 py-[5px] text-left text-sm text-apagado outline-none transition-colors duration-[var(--motion-duration-quick)] ease-[var(--motion-ease-standard)] hover:bg-alzado hover:text-tinta motion-reduce:transition-none focus-visible:ring-2 focus-visible:ring-lacre focus-visible:ring-offset-1",
              ledgerActivo === x.ledger && "bg-lacre-d text-tinta",
            )}
          >
            <span className="flex-1 truncate">{x.ledger || "todos"}</span>
            <span className="font-mono text-[11px] tabular-nums text-apagado">{x.entradas.toLocaleString("es")}</span>
          </button>
        ))}
      </nav>
      <div className="p-2">
        <label htmlFor="leer-como" className="mb-1 ml-2 block font-mono text-[10px] uppercase tracking-[.12em] text-apagado">
          Leer como
        </label>
        <select
          id="leer-como"
          value={yo}
          onChange={(e) => onCambiarYo(e.target.value)}
          className="w-full rounded-md border border-linea bg-papel px-2 py-[6px] text-sm text-tinta outline-none focus-visible:ring-2 focus-visible:ring-lacre focus-visible:ring-offset-1"
        >
          <option value="">— nadie —</option>
          {agentes.map((a) => (
            <option key={a} value={a}>
              {a}
            </option>
          ))}
        </select>
      </div>
    </aside>
  );
});
