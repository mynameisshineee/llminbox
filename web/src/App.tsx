import { Fragment, useEffect, useRef, useState } from "react";
import { getToken, type Entrada } from "@/lib/api";
import { construirCenso } from "@/lib/censo";
import { calcularSeparador } from "@/lib/separador";
import { motivoVacio } from "@/lib/titular";
import { useCursores, useEntradas, useEstado, useMuestra, useRoster, useSalud } from "@/lib/queries";
import { Puerta } from "@/components/Puerta";
import { Sidebar } from "@/components/Sidebar";
import { Header } from "@/components/Header";
import { BannerSalud } from "@/components/BannerSalud";
import { EstadoVacio } from "@/components/EstadoVacio";
import { Separador } from "@/components/Separador";
import { Fila } from "@/components/Fila";

export default function App() {
  const [entrado, setEntrado] = useState(Boolean(getToken()));
  const [ledger, setLedger] = useState("");
  const [yo, setYo] = useState(localStorage.getItem("llminbox.yo") ?? "");
  const [buscar, setBuscar] = useState("");
  const [buscarDebounced, setBuscarDebounced] = useState("");
  const [tipo, setTipo] = useState("");
  const [soloMias, setSoloMias] = useState(false);
  const [menuAbierto, setMenuAbierto] = useState(false);
  const sidebarRef = useRef<HTMLElement>(null);

  // Búsqueda debounced 260ms — mismo umbral que ui.html, para no disparar una
  // consulta por cada tecla sobre un ledger de miles de entradas.
  useEffect(() => {
    const t = setTimeout(() => setBuscarDebounced(buscar), 260);
    return () => clearTimeout(t);
  }, [buscar]);

  const salud = useSalud(entrado);
  const estado = useEstado(entrado);
  const roster = useRoster(entrado);
  const ledgersConfigurados = estado.data?.length ?? 0;
  const muestra = useMuestra(entrado && ledgersConfigurados > 0);
  const cursores = useCursores(yo, entrado);
  const filas = useEntradas({ ledger, q: buscarDebounced, tipo, soloMias, yo }, entrado);

  const abrirMenu = () => setMenuAbierto(true);
  const cerrarMenu = () => {
    setMenuAbierto(false);
    document.getElementById("abrir-menu")?.focus();
  };
  useEffect(() => {
    if (menuAbierto) sidebarRef.current?.querySelector<HTMLElement>("button, a, select, input")?.focus();
  }, [menuAbierto]);
  useEffect(() => {
    if (!entrado || !menuAbierto) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") cerrarMenu();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [entrado, menuAbierto]);

  if (!entrado) return <Puerta onEntrar={() => setEntrado(true)} />;

  const censo = construirCenso(roster.data);
  const tipos = [...new Set((muestra.data ?? []).map((x) => x.tipo).filter((t): t is string => Boolean(t)))].sort();
  const agentes = [
    ...new Set((muestra.data ?? []).flatMap((x) => [x.actor, ...(x.to ?? [])]).filter((a): a is string => Boolean(a))),
  ].sort();
  const filtrosActivos = buscar !== "" || tipo !== "" || soloMias;
  const cuentaTexto = filas.data ? `${filas.data.length}${filas.data.length === 120 ? "+" : ""} entradas` : "";
  const { marcas, n: nuevas } = calcularSeparador(filas.data ?? [], yo, cursores.data);

  const seleccionarLedger = (l: string) => {
    setLedger(l);
    cerrarMenu();
  };
  const cambiarYo = (nombre: string) => {
    setYo(nombre);
    localStorage.setItem("llminbox.yo", nombre);
  };
  const quitarFiltros = () => {
    setBuscar("");
    setBuscarDebounced("");
    setTipo("");
    setSoloMias(false);
  };

  return (
    <div className="grid h-full min-[760px]:grid-cols-[244px_1fr]">
      {menuAbierto && (
        <button
          type="button"
          aria-label="Cerrar el menú"
          onClick={cerrarMenu}
          className="fixed inset-0 z-[15] cursor-pointer border-0 bg-black/45 p-0 outline-none transition-opacity duration-[var(--motion-duration-drawer)] ease-[var(--motion-ease-standard)] motion-reduce:transition-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-lacre min-[760px]:hidden"
        />
      )}
      <Sidebar
        ref={sidebarRef}
        ledgers={estado.data ?? []}
        totalLedgers={ledgersConfigurados}
        ledgerActivo={ledger}
        onSeleccionar={seleccionarLedger}
        agentes={agentes}
        yo={yo}
        onCambiarYo={cambiarYo}
        abierta={menuAbierto}
      />
      <main className="flex flex-col overflow-hidden">
        <Header
          ledger={ledger}
          tipos={tipos}
          buscar={buscar}
          onBuscarChange={setBuscar}
          tipo={tipo}
          onTipoChange={setTipo}
          soloMias={soloMias}
          onSoloMiasChange={setSoloMias}
          cuenta={cuentaTexto}
          deshabilitado={ledgersConfigurados === 0}
          menuAbierto={menuAbierto}
          onAbrirMenu={abrirMenu}
        />
        <BannerSalud salud={salud.data} estado={estado.data} />
        <div className="flex-1 overflow-y-auto">
          {filas.isLoading ? (
            <p role="status" className="p-10 text-center text-sm text-apagado">
              cargando…
            </p>
          ) : !filas.data || filas.data.length === 0 ? (
            <EstadoVacio
              motivo={motivoVacio({
                ledgersConfigurados,
                filtrosActivos,
                estado: estado.data ?? [],
                ledgerSeleccionado: ledger,
              })}
              onQuitarFiltros={quitarFiltros}
            />
          ) : (
            filas.data.map((e: Entrada, i: number) => (
              <Fragment key={`${e.ledger}:${e.eid}`}>
                {(marcas[i] ?? false) && <Separador n={nuevas} />}
                <Fila e={e} yo={yo} censo={censo} />
              </Fragment>
            ))
          )}
        </div>
      </main>
    </div>
  );
}
