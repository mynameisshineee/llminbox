#!/usr/bin/env bash
# `llmi post` — la puerta puesta donde la flota escribe de verdad.
#
# Nace de una medición, no de una intuición (2026-08-11, red viva):
#     POST /append ...........    47 llamadas
#     entradas indexadas ..... 103.257          ⇒ el 0,05 % pasa por la puerta
#     sin nombrar a nadie ....     34 %
# El endpoint YA rechazaba lo que no dirige. La puerta estaba puesta donde no está el
# camino: la flota escribe con `cat >>`, que es lo que documenta el protocolo.
#
# Cada comprobación con su falsador. Y la última es la que importa de verdad: lo que
# esto escribe TIENE que routearlo el indexador — una herramienta de publicar que
# produzca algo que el troceador no entiende es peor que no tenerla, porque el autor
# se queda tranquilo.
set -uo pipefail
cd "$(dirname "$0")/.."
MALOS=0
bien() { printf "  ✓ %s\n" "$1"; }
mal()  { printf "  ✗ %s\n     esperado: %s · obtenido: %s\n" "$1" "$2" "$3"; MALOS=$((MALOS+1)); }

T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
printf '# ledger de prueba\n' > "$T/L.md"
python3 -c "import json,sys; json.dump({'prueba': sys.argv[1]+'/L.md'}, open(sys.argv[1]+'/m.json','w'))" "$T"

# CENSO PROPIO, y no es celo: `roster.json` lo crea `llmi init` y está en .gitignore,
# así que en el runner NO EXISTE. La primera versión de esta prueba usaba el del
# operador —verde en su Mac, 9 rojos en CI con «no pude leer roster.json … el
# extractor no reconocerá a nadie»—. Tercera vez en un día que un arnés mío mide MI
# máquina en vez del producto; la cura es la misma siempre: que la prueba se traiga su
# entorno. Y de propina, así no hay nombres de una flota real dentro de un repo público.
cat > "$T/censo.json" <<'JSON'
{"agentes": [{"nombre": "cto-A", "humano": "alguien", "clave": "", "rol": "cto"},
             {"nombre": "qa", "humano": "alguien", "clave": "", "rol": "qa"},
             {"nombre": "security", "humano": "alguien", "clave": "", "rol": "security"}],
 "humanos": [{"nombre": "alguien", "alias": []}],
 "difusion": ["equipo"]}
JSON
export LLMINBOX_ROSTER="$T/censo.json"

publica() {                       # publica <yo> <dest> <tipo> <titular> [cuerpo]
  printf '%s\n' "${5:-cuerpo}" | env -u BIK_CARRIL \
    LLMI_YO="$1" LLMI_A="$2" LLMI_TIPO="$3" LLMI_TITULAR="$4" LLMI_LEDGER=prueba \
    LLMI_MOUNTS="$T/m.json" LLMI_DIR=. LLMINBOX_ROSTER="$T/censo.json" python3 publicar.py 2>&1
}

# CONTROL DE ARRANQUE: si el censo de prueba no cargara, TODO saldría «no está en el
# censo» y las nueve comprobaciones de abajo pasarían por el motivo equivocado —que es
# justo lo que pasó en CI. Se comprueba ANTES de medir nada.
if ! python3 -c "
import os, sys; sys.path.insert(0, '.')
import ledger_parse as lp
sys.exit(0 if 'cto-A'.lower() in lp.CANON else 1)"; then
  echo "  ✗ el censo de prueba no carga: lo que siga NO mide la validación" >&2
  exit 1
fi
echo "  · censo de prueba cargado (3 agentes) — las comprobaciones miden la validación"

echo "── lo que no dirige, no se publica ──"
# El defecto exacto que mide `/doctor ②`: 34 % del corpus. Aquí se para en el origen.
publica cto-A "" FYI "algo" >/dev/null 2>&1 && mal "sin destinatario se rechaza" "salida≠0" "salida 0" \
  || bien "sin destinatario se rechaza"
# CONTROL POSITIVO: si rechazara también lo bueno, la herramienta no se usa y volvemos
# al `cat >>`. Un gate que dice que no a todo es un gate que nadie invoca.
publica cto-A qa FYI "algo" >/dev/null 2>&1 && bien "y lo que sí dirige, pasa (no muerde a todo)" \
  || mal "lo que dirige pasa" "salida 0" "rechazado"

echo "── un nombre mal tecleado parece dirigido y no llega ──"
S="$(publica cto-A securty FYI "algo")"
grep -q "no resuelve en el censo" <<<"$S" && bien "el destinatario fuera del censo se rechaza" \
  || mal "destinatario fuera del censo" "«no resuelve en el censo»" "$S"

echo "── el tipo se declara ──"
S="$(publica cto-A qa CHISME "algo")"
grep -q "no declarado" <<<"$S" && bien "un tipo inventado se rechaza, y enseña los válidos" \
  || mal "tipo inventado" "«no declarado» + lista" "$S"

echo "── el carril no es opcional ──"
# «Un carril, una ledger por sesión» deja de ser disciplina y pasa a ser mecánica.
S="$(printf 'x\n' | env -u BIK_CARRIL -u LLMI_LEDGER LLMI_YO=cto-A LLMI_A=qa LLMI_TIPO=FYI \
      LLMI_TITULAR=t LLMI_MOUNTS="$T/m.json" LLMI_DIR=. python3 publicar.py 2>&1)"
grep -q "carril declarado" <<<"$S" && bien "sin carril declarado no se publica" \
  || mal "sin carril se para" "«no hay carril declarado»" "$S"

echo "── el sello lo pone la herramienta, no el que escribe ──"
ANTES="$(grep -c '^### \[' "$T/L.md")"
publica cto-A "qa,security" PRODUCED "un titular con sello" "cuerpo de prueba" >/dev/null
DESPUES="$(grep -c '^### \[' "$T/L.md")"
[ "$((DESPUES-ANTES))" = "1" ] && bien "una publicación deja UNA cabecera (no media, ni dos)" \
  || mal "una sola cabecera" "1" "$((DESPUES-ANTES))"
grep -qE '^### \[cto-A → qa ∧ security · PRODUCED\] 2[0-9]{3}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z — ' "$T/L.md" \
  && bien "y con sello ISO puesto por el reloj, no tecleado" \
  || mal "sello ISO en la cabecera" "…T..:..:..Z —" "$(tail -2 "$T/L.md" | head -1)"
tail -1 "$T/L.md" | grep -q "cuerpo de prueba" \
  && bien "y el cuerpo va PEGADO a su cabecera (una sola escritura)" \
  || mal "cuerpo pegado" "cuerpo de prueba" "$(tail -1 "$T/L.md")"

echo "── y el indexador tiene que ENTENDERLO (lo que de verdad importa) ──"
# Falsador: una herramienta de publicar que produzca algo que el troceador no rutea es
# PEOR que no tenerla — el autor se queda tranquilo y el correo no llega a nadie.
S="$(python3 -c "
import sys; sys.path.insert(0,'.')
import ledger_parse as lp
cab = [l for l in open('$T/L.md') if l.startswith('### [')][-1]
ts, actor, to, dif, tipo, arroba = lp._campos(cab.rstrip(), '')
print(f'{actor}|{\",\".join(to)}|{tipo}|{bool(ts)}')")"
[ "$S" = "cto-A|qa,security|PRODUCED|True" ] \
  && bien "el troceador saca actor, destinatarios, tipo y sello de lo publicado" \
  || mal "round-trip por el troceador" "cto-A|qa,security|PRODUCED|True" "$S"

echo "── y funciona con el servicio MUERTO ──"
# `cat >>` gana porque nunca falla. Una publicación que dependa del contenedor se
# abandona el primer día que no esté, y volvemos al `>>` pelado.
docker ps --filter name=llminbox --format '{{.Names}}' | grep -q llminbox && VIVO=sí || VIVO=""
# `env VAR=… <función>` no existe: env sólo lanza binarios, y el fallo salía como
# «No such file or directory» — un rojo que acusaba a la publicación cuando lo roto
# era la prueba. Subshell, que sí ve la función.
S="$( unset LLMINBOX_TOKEN; export LLMINBOX_API=http://127.0.0.1:1; publica cto-A qa ACK "sin servicio" )"
grep -q '^✓ publicado' <<<"$S" \
  && bien "publica sin tocar el servicio (probado con la API apuntando a un puerto muerto)" \
  || mal "publica sin servicio" "✓ publicado" "$S"
[ -n "$VIVO" ] && echo "     (el contenedor estaba vivo: lo que prueba esto es que NO lo usa)"

echo
[ "$MALOS" -eq 0 ] && echo "publicar: TODO VERDE" || echo "publicar: $MALOS fallo(s)"
exit $((MALOS > 0))
