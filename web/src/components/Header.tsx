import { useId } from "react";
import { Menu } from "lucide-react";

/** Cabecera: título del ledger activo, filtros (búsqueda / tipo / solo lo mío),
 *  contador y el hamburguesa móvil [brief §5.9]. Filtros nativos a propósito —
 *  `<select>`/`<input>` ya dan teclado + AT gratis; inventar un combobox no suma
 *  nada aquí [brief §7]. */
export function Header({
  ledger,
  tipos,
  buscar,
  onBuscarChange,
  tipo,
  onTipoChange,
  soloMias,
  onSoloMiasChange,
  cuenta,
  deshabilitado,
  menuAbierto,
  onAbrirMenu,
}: {
  ledger: string;
  tipos: string[];
  buscar: string;
  onBuscarChange: (v: string) => void;
  tipo: string;
  onTipoChange: (v: string) => void;
  soloMias: boolean;
  onSoloMiasChange: (v: boolean) => void;
  cuenta: string;
  deshabilitado: boolean;
  menuAbierto: boolean;
  onAbrirMenu: () => void;
}) {
  const idBuscar = useId();
  const idTipo = useId();
  return (
    <header className="flex flex-wrap items-center gap-2.5 border-b border-linea bg-panel px-4 py-2.5">
      <button
        id="abrir-menu"
        type="button"
        onClick={onAbrirMenu}
        aria-label="Abrir la lista de ledgers"
        aria-expanded={menuAbierto}
        aria-controls="barra-lateral"
        className="flex size-[30px] flex-none items-center justify-center rounded-md border border-linea bg-alzado text-tinta outline-none focus-visible:ring-2 focus-visible:ring-lacre focus-visible:ring-offset-1 min-[760px]:hidden"
      >
        <Menu size={16} strokeWidth={1.5} aria-hidden="true" />
      </button>
      <h1 className="font-mono text-sm tracking-[-.01em]">{ledger || "todos"}</h1>
      <span className="flex-1" />
      <label htmlFor={idBuscar} className="sr-only">
        Buscar en el cuerpo
      </label>
      <input
        id={idBuscar}
        type="search"
        placeholder="buscar en el cuerpo…"
        value={buscar}
        onChange={(e) => onBuscarChange(e.target.value)}
        disabled={deshabilitado}
        className="min-w-[150px] max-w-full rounded-md border border-linea bg-papel px-2 py-[5px] text-[13px] text-tinta outline-none focus-visible:ring-2 focus-visible:ring-lacre focus-visible:ring-offset-1 disabled:opacity-50"
      />
      <label htmlFor={idTipo} className="sr-only">
        Filtrar por tipo
      </label>
      <select
        id={idTipo}
        value={tipo}
        onChange={(e) => onTipoChange(e.target.value)}
        disabled={deshabilitado}
        className="rounded-md border border-linea bg-papel px-2 py-[5px] text-[13px] text-tinta outline-none focus-visible:ring-2 focus-visible:ring-lacre focus-visible:ring-offset-1 disabled:opacity-50"
      >
        <option value="">todos los tipos</option>
        {tipos.map((t) => (
          <option key={t} value={t}>
            {t}
          </option>
        ))}
      </select>
      <label className="flex items-center gap-1.5 font-mono text-[11px] text-apagado">
        <input
          type="checkbox"
          checked={soloMias}
          onChange={(e) => onSoloMiasChange(e.target.checked)}
          disabled={deshabilitado}
          className="outline-none focus-visible:ring-2 focus-visible:ring-lacre focus-visible:ring-offset-1"
        />
        solo lo mío
      </label>
      <span className="font-mono text-[11px] tabular-nums text-apagado">{cuenta}</span>
    </header>
  );
}
