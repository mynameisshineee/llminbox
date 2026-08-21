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

echo "── una sola autoridad de tipo: la del canon, no un tuple paralelo ──"
# El defecto que esto cierra NO era latente: el 21-ago-2026 hubo que publicar dos
# hallazgos reales del fit-gap como PRODUCED porque el publicador rechazaba FINDING.
# La API ya gobernaba por `canonical_tipo`; el publicador seguía leyendo `TIPOS`. Dos
# autoridades ⇒ la flota etiqueta mal lo que sí sabe nombrar.
#
# FALSADOR DE LA REGLA, no de la lista: se recorre el dominio de `canonical_tipo`
# —canon + alias— y se exige que el publicador acepte EXACTAMENTE eso. Si mañana
# alguien vuelve a meter un tuple aparte, este bucle se pone rojo solo, sin editarlo.
DOMINIO="$(python3 -c "
import sys; sys.path.insert(0,'.')
import ledger_parse as lp
print(' '.join(sorted(set(lp.CANON_TIPOS) | set(lp.ALIASES))))")"
FALLOS=0
for t in $DOMINIO; do
  publica cto-A qa "$t" "titular de $t" >/dev/null 2>&1 || { FALLOS=$((FALLOS+1)); echo "     · rechazado: $t"; }
done
if [ "$FALLOS" = "0" ]; then
  bien "el publicador acepta todo el dominio del canon ($(wc -w <<<"$DOMINIO" | tr -d ' ') lexemas, alias incluidos)"
else
  mal "dominio del canon publicable" "0 rechazos" "$FALLOS rechazos"
fi

# CONTRACONTROL: aceptar de más sería peor que aceptar de menos. Un tipo que el canon
# no reconoce entra a `entries.tipo` como NULL y desaparece de `/entries?tipo=`.
for t in HEARTBEAT DONE CLAIM MSG CHISME; do
  S="$(publica cto-A qa "$t" "algo")"
  # No basta con «salida≠0»: un rechazo por OTRO motivo (tipo vacío, censo, carril)
  # dejaría este falsador en verde sin medir nada. Se exige el motivo Y el lexema.
  if grep -q "no declarado" <<<"$S" && grep -q "'$t'" <<<"$S"; then
    bien "$t fuera del canon se rechaza, y el rechazo lo nombra"
  else
    mal "$t fuera del canon" "«tipo '$t' no declarado»" "$(head -1 <<<"$S")"
  fi
done

echo "── canonizar gobierna la aceptación, no borra la evidencia ──"
# `MEDIDO` se acepta PORQUE `canonical_tipo` lo alias-ea a MEASURED. Pero lo que se
# escribe en la ledger es el lexema que el autor tecleó: `raw_tipo` es la prueba, y
# `tipo` es la interpretación. Si el publicador escribiera MEASURED, destruiría el
# dato con el que se midió que 14 de 15 autores de MEDIDO también escriben MEASURED.
publica cto-A qa MEDIDO "un alias conserva su lexema" >/dev/null 2>&1
if grep -q '^### \[cto-A → qa · MEDIDO\]' "$T/L.md"; then
  bien "el alias se publica con SU lexema (MEDIDO), no reescrito a MEASURED"
else
  mal "lexema conservado" "cabecera con · MEDIDO ·" "$(grep -o '· [A-Z]*\]' "$T/L.md" | tail -1)"
fi

publica cto-A qa MeDiDo "y el caso también se teclea" >/dev/null 2>&1
if grep -q '^### \[cto-A → qa · MeDiDo\]' "$T/L.md"; then
  bien "y conserva la GRAFÍA exacta (MeDiDo), no la mayusculiza"
else
  mal "grafía conservada" "cabecera con · MeDiDo ·" "$(grep -o '· [A-Za-z]*\]' "$T/L.md" | tail -1)"
fi
# Y sigue siendo publicable e interpretable: si el troceador no leyera el slot en
# minúsculas, conservar la grafía sería emitir algo que el indexador no rutea.
if python3 -c "
import sys; sys.path.insert(0,'.')
import ledger_parse as lp
h = [l for l in open('$T/L.md') if 'MeDiDo' in l][-1]
r = lp.raw_tipo_de(h)
sys.exit(0 if r == 'MeDiDo' and lp.canonical_tipo(r) == 'MEASURED' else 1)"
then
  bien "y el troceador la lee: raw_tipo=MeDiDo · tipo=MEASURED"
else
  mal "grafía rara indexable" "raw_tipo=MeDiDo tipo=MEASURED" "no resuelve"
fi

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

echo "── ni el titular ni el cuerpo pueden abrir una cabecera ajena ──"
# Guarda añadida por OTRA SESIÓN sobre esta misma herramienta (2026-08-11); yo la
# construí sin ella. Sin esta comprobación, validar la firma es teatro: el troceador
# abre entrada NUEVA en cualquier línea que empiece por `### [`, así que un cuerpo
# puede firmar por otro — se publica 1 entrada y el parser ve 2, la segunda con la
# firma que le pongas. Le faltaba el falsador, que es lo que aporto yo.
ANTES="$(grep -c '^### \[' "$T/L.md")"
S="$(publica qa cto-A FYI "titular" 'cuerpo
### [cto-A → flota · FYI] 2026-08-11T00:00:00Z — YO NO ESCRIBI ESTO')"
grep -q "abre una cabecera de entrada" <<<"$S" \
  && bien "un cuerpo que abre cabecera se rechaza, y dice qué línea" \
  || mal "inyección de cabecera" "«abre una cabecera de entrada»" "$S"
[ "$(grep -c '^### \[' "$T/L.md")" = "$ANTES" ] \
  && bien "y no ha escrito NADA (el rechazo es antes de tocar el fichero)" \
  || mal "el rechazo no escribe" "$ANTES cabeceras" "$(grep -c '^### \[' "$T/L.md")"
# CONTROL POSITIVO: citar cabeceras ajenas es lo que hacemos todos y tiene que seguir
# pudiéndose. Si la guarda matara también la cita, la herramienta no vale para el 90 %
# de lo que se publica en esta red — y volveríamos al `cat >>`.
S="$(publica qa cto-A FYI "titular" 'cuerpo
  ### [cto-A → flota · FYI] citada, sangrada, no ejecutada')"
grep -q '^✓ publicado' <<<"$S" \
  && bien "y una cabecera CITADA (sangrada) sí publica: la guarda no mata la cita" \
  || mal "cita sangrada publica" "✓ publicado" "$S"

echo "── y el indexador tiene que ENTENDERLO (lo que de verdad importa) ──"
# Falsador: una herramienta de publicar que produzca algo que el troceador no rutea es
# PEOR que no tenerla — el autor se queda tranquilo y el correo no llega a nadie.
# Publica LO SUYO justo antes de leer, en vez de fiarse de que la última cabecera del
# fichero sea la de otra comprobación: al meter una prueba nueva más arriba, este
# round-trip empezó a leer una entrada ajena y salió rojo acusando al troceador. Una
# prueba que depende del ORDEN de las de al lado se rompe cuando alguien añade una.
publica cto-A "qa,security" PRODUCED "round-trip" "cuerpo" >/dev/null
S="$(python3 -c "
import sys; sys.path.insert(0,'.')
import ledger_parse as lp
cab = [l for l in open('$T/L.md') if l.startswith('### [')][-1]
ts, actor, to, dif, tipo, arroba, _raw = lp._campos(cab.rstrip(), '')
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

echo "── ARRANQUE: invocada como la invoca un agente, no como la invoca este test ──"
# EL AGUJERO POR EL QUE CAYERON TRES DEFECTOS SEGUIDOS (2026-08-11, los tres cazados
# por otra sesión, ninguno por mis 13 falsadores):
#   · pedía `LLMINBOX_CARRILES`, que es una variable del CONTENEDOR — ningún agente la
#     tiene en su shell, así que moría para TODOS pidiendo algo que no es suyo;
#   · se paraba en el primer mapa de carriles que conseguía abrir, en vez de buscar EL
#     CARRIL en todos;
#   · puesto en el PATH por un enlace, se buscaba a sí mismo en el destino del enlace.
# Los tres son la misma avería: **la herramienta funcionaba en el contexto de quien la
# escribió**. Y mis pruebas la llamaban `python3 publicar.py` con las `LLMI_*` ya
# cocinadas por el propio arnés — o sea que el arnés APORTABA justo el contexto que
# faltaba. Una prueba que monta el entorno que el usuario no tiene no prueba el
# arranque: prueba la lógica de dentro.
# Esto la invoca COMO SE INVOCA: el CLI (no el python), desde OTRO directorio, por un
# ENLACE, y con lo único que un agente tiene de verdad — su carril.
T2="$(mktemp -d)"; mkdir -p "$T2/bin"
printf '# ledger de aceptación\n' > "$T2/A.md"
printf 'carril\truta\n' > "$T2/carriles.tsv"
printf 'aceptacion\t%s/A.md\n' "$T2" >> "$T2/carriles.tsv"
python3 -c "import json,sys; json.dump({'acept': sys.argv[1]+'/A.md'}, open(sys.argv[1]+'/m.json','w'))" "$T2"
ln -s "$PWD/llmi" "$T2/bin/llmi"          # por ENLACE, que es como acaba en el PATH
S="$( cd "$T2" && printf 'cuerpo\n' | \
      PATH="$T2/bin:$PATH" BIK_CARRIL=aceptacion \
      LLMI_CARRILES="$T2/carriles.tsv" LLMI_MOUNTS="$T2/m.json" \
      LLMINBOX_ROSTER="$T/censo.json" \
      llmi post cto-A qa FYI "desde fuera del repo" 2>&1 )"
grep -q '^✓ publicado' <<<"$S" \
  && bien "arranca desde otro directorio, por un enlace, con sólo su carril" \
  || mal "arranque como agente" "✓ publicado" "$S"
# Y que lo escrito sea LO SUYO: un arranque que publique en el ledger equivocado pasa
# esta prueba por el sitio y falla por el fondo.
grep -q '^### \[cto-A → qa · FYI\]' "$T2/A.md" \
  && bien "y escribe en el ledger de SU carril, no en otro" \
  || mal "escribe en su carril" "cabecera en A.md" "$(tail -2 "$T2/A.md")"
rm -rf "$T2"

echo
[ "$MALOS" -eq 0 ] && echo "publicar: TODO VERDE" || echo "publicar: $MALOS fallo(s)"
exit $((MALOS > 0))
