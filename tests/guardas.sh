#!/usr/bin/env bash
# ── LAS GUARDAS DEL ARNÉS, PROBADAS CON SU ENTRADA MALA ───────────────────────
#
# Por qué existe este fichero, con su fecha y su coste: el 2026-08-11, ocho
# comprobaciones del humo llevaban DOS DÍAS certificando en verde una reconstrucción
# del índice que nunca ocurría. Los pasos de preparación reventaban en Linux y el
# bloque seguía corriendo. Y los 16 mutantes que este repo mantiene no lo vieron
# nunca, por una razón estructural: **los 16 mutan `servicio.py` o `ledger_parse.py`
# — el PRODUCTO. Nadie mutaba el ANDAMIO.** Un mutante no encuentra una puerta que no
# se llega a ejecutar.
#
# Así que aquí no se prueba el producto: se prueba que **las guardas del arnés saben
# decir que NO** cuando les llega su entrada mala. Cada una con su control positivo al
# lado, porque una guarda que dice «mal» a todo tampoco sirve.
#
# Rápido a propósito (<1 min, sin levantar el servicio): una prueba de los
# instrumentos que tarda como la de la corrección se salta igual que ella.
set -uo pipefail
cd "$(dirname "$0")/.."
IMAGEN="${IMAGEN:-llminbox:test}"
FALLOS=0
. tests/guardas.lib.sh

# `ok`/`fallo`/`no_medido` escriben en FALLOS, así que las pruebas de ABAJO no pueden
# usarlas para juzgar: se juzgarían con lo que están midiendo. Contadores aparte.
MALOS=0
bien() { printf "  ✓ %s\n" "$1"; }
mal()  { printf "  ✗ %s\n     esperado: %s · obtenido: %s\n" "$1" "$2" "$3"; MALOS=$((MALOS+1)); }
igual(){ [ "$2" = "$3" ] && bien "$1" || mal "$1" "$2" "$3"; }

echo "── un paso de preparación que falla NO puede pasar desapercibido ──"
# La avería exacta del 2026-08-09: `set -uo pipefail` sin `-e`, un `python3 -c` que
# revienta, y el bloque siguiendo como si nada. 5 verdes falsos.
SAL=$( FALLOS=0; paso "un paso inventado" false 2>&1; echo "rc=$?" )
case "$SAL" in *"NO SE MIDIÓ"*) bien "un paso que falla se declara NO MEDIDO" ;;
               *) mal "un paso que falla se declara NO MEDIDO" "NO SE MIDIÓ" "$SAL" ;; esac
case "$SAL" in *"rc=1"*) bien "y devuelve 1, para que quien llama pueda cortar" ;;
               *) mal "y devuelve 1" "rc=1" "$SAL" ;; esac
# CONTROL POSITIVO: si dijera «no medido» también con un paso BUENO, no distinguiría nada.
SAL=$( FALLOS=0; paso "un paso que va" true 2>&1; echo "rc=$?" )
case "$SAL" in *"NO SE MIDIÓ"*) mal "un paso que VA no dice nada" "silencio" "$SAL" ;;
               *"rc=0"*) bien "y un paso que VA pasa callado (la guarda no muerde a todo)" ;;
               *) mal "un paso que VA devuelve 0" "rc=0" "$SAL" ;; esac

echo "── «no medido» tiene que CONTAR como fallo ──"
# Si no contara, romper el transporte apagaría la suite entera: la avería que
# elegiría alguien con prisa por poner el CI en verde.
N=$( FALLOS=0; no_medido "x" "y" >/dev/null; echo "$FALLOS" )
igual "un NO MEDIDO incrementa el contador de fallos" "1" "$N"

echo "── comparar contra el vacío no es comparar ──"
SAL=$( FALLOS=0; comp "algo" "" "" 2>&1 )
case "$SAL" in *"NO SE MIDIÓ"*) bien "dos lados vacíos NO se confirman entre sí" ;;
               *) mal "dos lados vacíos dan NO MEDIDO" "NO SE MIDIÓ" "$SAL" ;; esac
SAL=$( FALLOS=0; comp "algo" "5" "" 2>&1 )
case "$SAL" in *"NO SE MIDIÓ"*) bien "y un lado vacío tampoco es «otro valor»" ;;
               *) mal "un lado vacío da NO MEDIDO" "NO SE MIDIÓ" "$SAL" ;; esac
SAL=$( FALLOS=0; comp "algo" "5" "5" 2>&1 )
case "$SAL" in *"✓"*) bien "y dos valores iguales sí comparan (no muerde a todo)" ;;
               *) mal "dos iguales dan verde" "✓" "$SAL" ;; esac

echo "── la espera a /health sabe agotarse ──"
# Un puerto donde no hay nadie. Antes eran bucles `for … && break` sin brazo de `||`:
# se agotaban EN SILENCIO y lo que venía después medía un servicio ausente.
SAL=$( FALLOS=0; esperar_salud "http://127.0.0.1:1" 2 "un servicio que no existe" 2>&1; echo "rc=$?" )
case "$SAL" in *"NO SE MIDIÓ"*) bien "contra un puerto muerto se declara NO MEDIDO" ;;
               *) mal "puerto muerto da NO MEDIDO" "NO SE MIDIÓ" "$SAL" ;; esac
case "$SAL" in *"rc=1"*) bien "y devuelve 1" ;; *) mal "y devuelve 1" "rc=1" "$SAL" ;; esac

echo "── junto a la base no puede haber ficheros de otro uid ──"
# ⚠️ ALCANCE: sobre bind-mounts de macOS esto sería INERTE (Docker Desktop virtualiza
# la propiedad). Por eso la prueba usa un VOLUMEN NOMBRADO, donde la propiedad es real
# igual que en el runner de Linux: la guarda se ejercita de verdad en las dos
# plataformas. Es la guarda que el 2026-08-11 no existía, y la que habría convertido
# tres corridas de CI en una.
VOL="guardas-$$"
if docker volume create "$VOL" >/dev/null 2>&1; then
  docker run --rm -u 0 -v "$VOL:/datos" "$IMAGEN" sh -c \
    'python3 -c "open(\"/datos/h.sqlite\",\"w\").write(\"x\")" && chown 1000:1000 /datos/h.sqlite && chmod 777 /datos' >/dev/null 2>&1
  # ① control POSITIVO primero: sin intrusos tiene que callarse. Si esto falla, el ✗
  #    de abajo no probaría nada — sería una guarda que se queja de todo.
  if ajenos_en_datos "$VOL" >/dev/null 2>&1; then
    bien "sin intrusos, la guarda calla"
  else
    mal "sin intrusos la guarda calla" "silencio + rc=0" "$(ajenos_en_datos "$VOL" 2>&1)"
  fi
  # ② y ahora el intruso: un fichero de root al lado de una base del uid 1000.
  docker run --rm -u 0 -v "$VOL:/datos" "$IMAGEN" \
    python3 -c 'open("/datos/intruso","w").write("x")' >/dev/null 2>&1
  SAL=$(ajenos_en_datos "$VOL" 2>&1; echo "rc=$?")
  case "$SAL" in *"intruso(uid=0)"*) bien "con un fichero de root al lado, lo NOMBRA" ;;
                 *) mal "nombra al intruso" "intruso(uid=0)" "$SAL" ;; esac
  case "$SAL" in *"rc=1"*) bien "y devuelve 1, para declarar el bloque NO MEDIDO" ;;
                 *) mal "y devuelve 1" "rc=1" "$SAL" ;; esac
  docker volume rm "$VOL" >/dev/null 2>&1
else
  mal "la guarda de propiedad" "un volumen para probarla" "docker volume create falló"
fi

echo "── escribir la base del servicio se hace COMO SU DUEÑO ──"
# El uid no se elige: se lee del fichero. Se prueba con un dueño RARO (4242), que no
# es ni root ni el `USER` de la imagen: si la función tuviera cableado cualquiera de
# los dos, aquí se rompe. Las dos opciones «de sentido común» fallaron en producción.
VOL2="guardas2-$$"
if docker volume create "$VOL2" >/dev/null 2>&1; then
  docker run --rm -u 0 -v "$VOL2:/datos" "$IMAGEN" sh -c \
    'python3 -c "open(\"/datos/h.sqlite\",\"w\").write(\"\")" && chown 4242:4242 /datos/h.sqlite && chmod 755 /datos && chmod 600 /datos/h.sqlite' >/dev/null 2>&1
  QUIEN=$(en_contenedor "$VOL2" "import os; print(os.getuid())" 2>/dev/null)
  igual "escribe con el uid que es DUEÑO de la base, no con el suyo" "4242" "$QUIEN"
  # Y que además pueda escribirla de verdad: un 0600 de 4242 no lo toca nadie más.
  SAL=$(en_contenedor "$VOL2" "
open('/datos/h.sqlite','w').write('tocado')
print(open('/datos/h.sqlite').read())" 2>&1)
  igual "y la escribe de verdad (0600 de un dueño ajeno)" "tocado" "$(printf '%s' "$SAL" | tail -1)"
  docker volume rm "$VOL2" >/dev/null 2>&1
else
  mal "el descubridor de dueño" "un volumen para probarlo" "docker volume create falló"
fi

echo
[ "$MALOS" -eq 0 ] && echo "guardas: TODO VERDE" || echo "guardas: $MALOS fallo(s)"
exit $((MALOS > 0))
