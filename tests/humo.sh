#!/usr/bin/env bash
# Prueba de humo: levanta el servicio de cero y comprueba las propiedades que este
# producto promete. Corre en CI y en local; no necesita nada del disco del operador.
#
# Cada comprobación tiene su FALSADOR escrito al lado: qué se vería si la propiedad
# estuviera rota. Una comprobación que no puede fallar no comprueba nada — la
# lección más cara de este proyecto.
set -uo pipefail
PUERTO="${PUERTO:-8199}"; NOMBRE="humo-$$"; TOK="humo-$(date +%s)"
TMP="$(mktemp -d)"; FALLOS=0
limpiar() { docker rm -f "$NOMBRE" >/dev/null 2>&1; rm -rf "$TMP"; }
trap limpiar EXIT

ok()   { printf "  ✓ %s\n" "$1"; }
fallo(){ printf "  ✗ %s\n     esperado: %s · obtenido: %s\n" "$1" "$2" "$3"; FALLOS=$((FALLOS+1)); }
comp() { [ "$2" = "$3" ] && ok "$1" || fallo "$1" "$2" "$3"; }

printf '# t\n\n### [alice-backend → bob-reviewer · REQUEST] primera\ncuerpo uno\n' > "$TMP/l.md"
printf '\n### [bob-reviewer → alice-backend · ACK] segunda\ncuerpo dos\n' >> "$TMP/l.md"

docker run -d --name "$NOMBRE" -p "127.0.0.1:$PUERTO:8077" \
  -e LLMINBOX_LEDGERS="t=/l/l.md" -e LLMINBOX_TOKEN="$TOK" \
  -e LLMINBOX_DB=/tmp/h.sqlite -e LLMINBOX_POLL=1 -e LLMINBOX_ROSTER=/censo.json \
  -v "$TMP:/l:ro" -v "$PWD/roster.example.json:/censo.json:ro" \
  "${IMAGEN:-llminbox:test}" >/dev/null || { echo "no arrancó el contenedor"; exit 1; }

for _ in $(seq 1 40); do curl -sf -m 2 "http://127.0.0.1:$PUERTO/health" >/dev/null 2>&1 && break; sleep 1; done
sleep 3
A=(-H "X-Llminbox-Token: $TOK"); U="http://127.0.0.1:$PUERTO"

echo "── autenticación ──"
# falsador: si el gate no existiera, esto daría 200 y serviría el canon entero
comp "sin token → 401"        "401" "$(curl -s -o /dev/null -w '%{http_code}' "$U/stat")"
comp "token malo → 401"       "401" "$(curl -s -o /dev/null -w '%{http_code}' -H 'X-Llminbox-Token: no' "$U/stat")"
comp "token bueno → 200"      "200" "$(curl -s -o /dev/null -w '%{http_code}' "${A[@]}" "$U/stat")"
# falsador: /docs abierto fue un agujero real; si vuelve, esto da 200
comp "/docs cerrado → 404"    "404" "$(curl -s -o /dev/null -w '%{http_code}' "$U/docs")"
comp "/openapi cerrado → 404" "404" "$(curl -s -o /dev/null -w '%{http_code}' "$U/openapi.json")"

echo "── indexado ──"
comp "indexa las 2 entradas" "2" "$(curl -s "${A[@]}" "$U/stat" | python3 -c 'import sys,json;print(json.load(sys.stdin)[0]["entradas"])')"
# falsador: sin censo cargado el extractor devolvería actor=None y esto sería 0
# Se piden LAS DOS y se comparan ordenadas: con limit=1 esta prueba comparaba la
# entrada más reciente contra el actor de la otra y fallaba por culpa del test.
comp "extrae los dos actores" "alice-backend,bob-reviewer" \
  "$(curl -s "${A[@]}" "$U/entries?ledger=t" | python3 -c 'import sys,json;print(",".join(sorted({x["actor"] or "?" for x in json.load(sys.stdin)})))')"
# falsador: sin censo cargado, el extractor devuelve None y esto sería "?"
comp "extrae destinatarios" "alice-backend,bob-reviewer" \
  "$(curl -s "${A[@]}" "$U/entries?ledger=t" | python3 -c 'import sys,json;print(",".join(sorted({w for x in json.load(sys.stdin) for w in (x.get("to") or [])})))')"

echo "── la bandeja, que es el producto ──"
n=$(curl -s "${A[@]}" "$U/inbox/alice-backend" | grep -c "para ti")
comp "alice tiene bandeja" "1" "$n"
# falsador: si el GET mutara el cursor (bug real, corregido), la 2ª lectura saldría vacía
n2=$(curl -s "${A[@]}" "$U/inbox/alice-backend" | grep -c "para ti")
comp "el GET no consume" "1" "$n2"
# y el POST sí avanza
curl -s "${A[@]}" -H 'Content-Type: application/json' -d '{"hasta":{"t":99}}' -o /dev/null "$U/inbox/alice-backend/leido"
comp "el POST sí avanza" "0" "$(curl -s "${A[@]}" "$U/inbox/alice-backend" | grep -c 'para ti')"

echo "── integridad: distinguir escribir de borrar ──"
printf '\n### [alice-backend → bob-reviewer · FYI] tercera a medias\n' >> "$TMP/l.md"; sleep 3
printf 'el cuerpo llega tarde\n' >> "$TMP/l.md"; sleep 3
# falsador: antes esto gritaba «entrada que ESTUVO y ya no está» por escribir en 2 pasos
comp "escribir a trozos NO alarma" "0" "$(curl -s "${A[@]}" "$U/chain/verify" | grep -c '✗')"
python3 -c "
p='$TMP/l.md'; L=open(p).read().split(chr(10)); open(p,'w').write(chr(10).join(L[:4]))"; sleep 4
# falsador: si no detectara borrados, esto seguiría en 0 y la promesa del producto es falsa
[ "$(curl -s "${A[@]}" "$U/chain/verify" | grep -c '✗')" -ge 1 ] \
  && ok "borrar SÍ alarma" || fallo "borrar SÍ alarma" "≥1 línea con ✗" "0"

echo "── nadie se bloquea si el servicio muere ──"
docker stop "$NOMBRE" >/dev/null 2>&1
tail -2 "$TMP/l.md" >/dev/null 2>&1 && ok "tail sigue funcionando con el servicio parado" \
  || fallo "tail sigue funcionando" "sí" "no"

echo
[ "$FALLOS" -eq 0 ] && { echo "humo: TODO VERDE"; exit 0; } || { echo "humo: $FALLOS fallo(s)"; exit 1; }
