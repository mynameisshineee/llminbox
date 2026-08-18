"""Lo que una reconstrucción de índice NO puede llevarse por delante.

El 2026-08-15T22:47:55 el índice se corrompió (`quick_check: wrong # of entries in
index i_who`), el servicio se curó como debía —esa cura es una propiedad del producto,
con su prueba en el humo— y en el viaje se llevó **96 claims, 70 de ellos abiertos**:
el estado de reparto de trabajo de los 15 agentes. `claims` nació DESPUÉS de
`_rescatar()` y nadie la añadió a su lista.

Y el remate: `/doctor ③` publicó la pérdida como **«0 sin cerrar ni relevar»**, que es
la mejor nota posible. Una pérdida de datos con cara de disciplina perfecta.
"""
from __future__ import annotations

import re
import sqlite3

from conftest import construir


def test_rescate_cubre_lo_no_derivable(servicio):
    """EL GUARDA ESTRUCTURAL, y es el que de verdad arregla esto: la lista de rescate
    se compara contra el ESQUEMA. Toda tabla que no se re-derive tiene que estar
    rescatada; si alguien añade una tabla de estado nueva y no decide qué pasa con
    ella, esto se pone rojo con su nombre.

    FALSADOR: quitar `claims` de `TABLAS_RESCATADAS` tiene que romper este test —es
    exactamente el estado en que el repo estuvo desde que se creó la tabla hasta el
    incidente.
    """
    del_esquema = set(re.findall(r"CREATE TABLE IF NOT EXISTS (\w+)", servicio.SCHEMA))
    rescatadas = {t for t, _ in servicio.TABLAS_RESCATADAS}
    huerfanas = del_esquema - set(servicio.DERIVADAS) - rescatadas
    assert not huerfanas, (
        f"tablas que ni se re-derivan ni se rescatan: {sorted(huerfanas)} — "
        "decide: ¿sale del markdown, o se pierde en la próxima corrupción?")


def test_las_columnas_declaradas_existen_de_verdad(servicio):
    """La lista nombra columnas, y una columna mal escrita convierte el rescate en un
    `OperationalError` que se traga el `except` de al lado: el rescate 'funciona' y no
    trae nada. Se comprueba contra el esquema real, no contra la memoria de quien lo
    escribió."""
    con = sqlite3.connect(":memory:")
    con.executescript(servicio.SCHEMA)
    for tabla, cols in servicio.TABLAS_RESCATADAS:
        reales = {r[1] for r in con.execute(f"PRAGMA table_info({tabla})")}
        pedidas = set(cols.split(","))
        assert pedidas <= reales, f"{tabla}: no existen {sorted(pedidas - reales)}"
    con.close()


def test_los_claims_sobreviven_a_una_reconstruccion(cliente, servicio):
    """El caso REAL, extremo a extremo: se coge un claim, se reconstruye el índice como
    lo hace la cura de corrupción, y el claim tiene que seguir ahí.

    FALSADOR: sin `claims` en la lista de rescate, la base nueva sale con la tabla
    vacía y esto da 0 — que es literalmente lo que pasó en producción.
    """
    cliente.post("/claim", json={"tema": "no_me_pierdas", "rol": "ejecuta",
                                 "agent": "backend"})
    con = servicio.db()
    antes = con.execute("SELECT COUNT(*) FROM claims").fetchone()[0]
    con.close()
    assert antes == 1, "precondición: el claim tiene que existir antes de reconstruir"

    assert servicio.reconstruir_indice("prueba de rescate") is True

    con = servicio.db()
    fila = con.execute("SELECT tema, rol, agent FROM claims").fetchall()
    con.close()
    assert [tuple(r) for r in fila] == [("no_me_pierdas", "ejecuta", "be")], fila
