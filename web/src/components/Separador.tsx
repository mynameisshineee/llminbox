/** Divisor cronológico de "lo nuevo" — se apoya en el cursor que YA existe (lo
 *  avanza la CLI u otro agente); esta página solo lo lee y lo dibuja, nunca lo
 *  mueve [brief §5.6, §1.1]. */
export function Separador({ n }: { n: number }) {
  return (
    <div className="flex items-center gap-2.5 bg-lacre-d px-4 py-[7px] font-mono text-[11px] text-lacre before:h-px before:flex-1 before:content-[''] before:bg-current before:opacity-35 after:h-px after:flex-1 after:content-[''] after:bg-current after:opacity-35">
      {n} nueva{n === 1 ? "" : "s"} desde tu última visita
    </div>
  );
}
