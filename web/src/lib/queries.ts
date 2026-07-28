import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

/** Hooks TQ — un fichero, porque la app es una sola vista. queryKey = ruta del
 *  endpoint como prefijo, convención ya establecida en el skeleton (`["stat"]`). */

export function useSalud(entrado: boolean) {
  return useQuery({ queryKey: ["health"], queryFn: api.salud, enabled: entrado });
}

export function useEstado(entrado: boolean) {
  return useQuery({ queryKey: ["stat"], queryFn: api.estado, enabled: entrado });
}

export function useRoster(entrado: boolean) {
  return useQuery({ queryKey: ["roster"], queryFn: api.roster, enabled: entrado });
}

/** Solo lectura — nunca el POST que avanza el cursor (ver `api.ts`). Deshabilitado
 *  sin agente elegido en "leer como": sin YO no hay separador que pintar. */
export function useCursores(agente: string, entrado: boolean) {
  return useQuery({
    queryKey: ["cursor", agente],
    queryFn: () => api.cursor(agente),
    enabled: entrado && Boolean(agente),
  });
}

export type FiltrosEntradas = {
  ledger: string;
  q: string;
  tipo: string;
  soloMias: boolean;
  yo: string;
};

export function useEntradas(f: FiltrosEntradas, entrado: boolean) {
  return useQuery({
    queryKey: ["entries", f],
    queryFn: () =>
      api.entradas({
        ledger: f.ledger || undefined,
        limit: 120,
        cuerpo: true,
        q: f.q || undefined,
        tipo: f.tipo || undefined,
        to: f.soloMias && f.yo ? f.yo : undefined,
      }),
    enabled: entrado,
  });
}

/** Muestra amplia, independiente de los filtros activos — sirve solo para poblar
 *  las opciones de "tipo" y "leer como". Si se derivasen de la lista ya filtrada
 *  (como hacía el skeleton), filtrar por ledger encoge esas opciones y el valor
 *  elegido en "leer como" puede dejar de tener <option> — bug ya resuelto en
 *  `ui.html`, que muestrea 400 aparte al arrancar. */
export function useMuestra(entrado: boolean) {
  return useQuery({
    queryKey: ["entries-muestra"],
    queryFn: () => api.entradas({ limit: 400 }),
    enabled: entrado,
  });
}
