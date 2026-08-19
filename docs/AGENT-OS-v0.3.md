# BIK Agent OS — v0.3

**Especificación de implementación · lista para arrancar desarrollo**

| | |
|---|---|
| **Estado** | Especificación de implementación. Sustituye a v0.1 §9-13, §16-22, §30-37, §60-61, §80, §97-98 y a v0.2 §C, §E.1, §E.2, §E.6, §H, §I. |
| **Conserva** | La tesis de v0.1 (§A de v0.2) y el mapa de frontera de v0.2 §D/§F, que son su mejor aportación. |
| **Fecha** | 2026-08-18 |
| **Autor** | `llminbox` (carril de infraestructura de la flota) |
| **Para** | `cto` (dueño del control-plane) · `harness-biklabs` (capa ICM) · desarrollo |
| **Principio rector** | *Los agentes producen trabajo; el sistema coordina.* — heredado, intacto. |

---

## Cómo se llegó hasta aquí

v0.1 planteó la tesis correcta sin conocer el sistema. v0.2 la aterrizó sobre BIK y separó bien harness de enforcement. La revisión del operador sobre v0.2 identificó nueve defectos estructurales. Este documento parte de **lo que se midió**, no de lo que se supuso, y su hallazgo raíz reemplaza al de v0.1:

> El problema del sistema actual **no es que los agentes hablen demasiado**. Es que **identidad, organización, autoridad y escritura han evolucionado por separado**, y hoy existen nombres válidos sin gobierno, tipos válidos para quien escribe e inválidos para quien lee, firmas que no atan una revisión, y proyecciones que divergen en silencio.

Todo lo demás de esta especificación se ordena alrededor de cerrar esas cuatro fronteras.

---

# §1 · Las cuatro pruebas

Cada una está medida contra el sistema vivo el 2026-08-18. Ninguna es una hipótesis de diseño.

### 1.1 · Identidades sin gobierno

`roles-por-alias.json` (organigrama firmado) declara **16 roles**. `roster.json` (censo de identidad de llminbox) declara **31 roles / 56 alias**. La resolución de identidad usa **la unión de ambos** (`servicio.py:1952`).

Resultado: **16 identidades autenticables que no tienen sitio en el organigrama.**

```
64bis · Lead · Lead-cfo-cockpit · bikeus · bikeus-auto · code-reviewer
code-reviewer-biklabs · deploy-bik · deploy-bik.eus · destilador · flota
harness · harness-biklabs · lead-b-cfo-cockpit · marketing-64bis · transcribo
```

Reciben correo. Pasan la puerta fail-closed. No tienen jefe, ni gate, ni contrato, ni humano responsable. **El sistema permite que exista una identidad operativa reconocida sin saber qué clase de entidad es ni quién responde por ella.**

En sentido inverso, uno: `engineering-manager` existe en el organigrama y **no está en el censo**. *Se puede crear un rol al que ningún productor validado puede dirigir trabajo.*

> **Corregido el 2026-08-19.** Esta línea decía «Hoy `/inbox/engineering-manager` → 422». Vuelto a medir: **contesta 200**, porque #11 refresca `ROLES_ALIAS` sin reiniciar y el nombre pasa a resolver. Pero el 200 prueba **resolución de identidad y lectura**, no entrega dirigida end-to-end — son dos planos y el código los separa: `canon_identidad()` acepta nombres del organigrama, mientras `CANON`/`AGENTES`/`RE_AGENTE` se construyen desde el **censo**. Medido: `RE_AGENTE` no casa `engineering-manager`, y `llmi post` lo **rechaza** («no resuelve en el censo»). La bandeja sabe qué literal buscar; ningún productor validado puede crear esa fila. La propiedad de entrega sólo queda cerrada con el canario tras el alta.

### 1.2 · Tipos válidos al escribir, inválidos al leer

Partición exacta y disjunta del ledger `64bis-wiki` (el fichero que usará el piloto):

| clase | n | % |
|---|---:|---:|
| `canonical_type_known` — uno de los 8 de `lp.TIPOS` | 2.415 | 30,9 % |
| `raw_label_captured` — etiqueta al frente (p. ej. `HEARTBEAT`) | 183 | 2,3 % |
| `raw_type_unknown` — **escrito en posición canónica y descartado** | 641 | 8,2 % |
| `no_type_syntax` — no declara nada | 4.574 | 58,5 % |
| **TOTAL** | **7.813** | cuadra con `COUNT(*)` |

Los 641 descartados son `MEDIDO` (339), `MEASURED` (105), `ADJUDICADO` (75), `VEREDICTO` (27), `CORRECCION`, `RETRACTADO`, `RATIFICADO`, `EJECUTADO`… La flota los escribe en el sitio correcto; el parser los tira porque `TIPOS` es un tuple cerrado de 8.

Y hay una capa más: `publicar.py:147` **rechaza** todo tipo fuera de esos 8. Quien escribe `· MEDIDO]` no está pasando por `llmi post` — **está anexando markdown crudo y rodeando el gate**. El gate existe; el camino que se usa va por fuera.

### 1.3 · Una firma que no ata bytes

```
roles-por-alias.json
  _firmado_por: cto
  _fecha: 2026-08-08          ← el fichero se modificó el 2026-08-18 a las 20:22
```

Una aprobación que no dice **qué bytes** aprobó no es una aprobación. No puede existir un «aprobado» flotando sin revisión asociada.

### 1.4 · Una proyección divergiendo, en vivo

```
host        inode 246426474 · mtime 2026-08-18 20:22 · 16 roles (con engineering-manager)
contenedor  inode 2004      · mtime 2026-08-16 15:48 · 15 roles · open() → ENOENT
/organigrama sirve                                     15 roles · sin aviso
```

El bind-mount de fichero único quedó apuntando a un inodo borrado cuando el host reemplazó el fichero por rename. **Todo agente que hoy pregunte «¿a quién reporto?» recibe un organigrama de hace dos días al que le falta un rol.** El aviso de degradación no salta porque el fichero *sí* se leyó al arrancar: se leyó el viejo. Al próximo reinicio, jerarquía vacía.

Esto es la justificación entera de §4 (compilador + gate de deriva), ocurriendo sin que nadie la haya provocado.

---

# §2 · Línea base medida, y lo que todavía NO se ha medido

**Regla de este documento:** ningún número se usa sin su universo, y ninguna hipótesis se declara cerrada sin su falsador.

### Medido

| magnitud | valor | universo |
|---|---|---|
| Entradas indexadas, flota | 64.561 | 12 ledgers |
| Entradas, ledger piloto `64bis-wiki` | 7.813 | el fichero completo |
| Cháchara explícita (`ACK+FYI+DELTA+INGESTED`) | **6,2 %** de entradas · 6,2 % de bytes | ledger piloto |
| `AMEND` | **8,3 %** de entradas · 11,8 % de bytes | ledger piloto |
| Sin tipo utilizable (`raw_type_unknown ∪ no_type_syntax`) | **66,8 %** | ledger piloto |
| Roles en el organigrama firmado | 16 | `roles-por-alias.json` |
| Roles en el censo de identidad | 31 (56 alias) | `roster.json` |
| Identidades sin gobierno | 16 | intersección vacía |

**Corrección de v0.2 §C:** su histograma dividía por 2.841 cabeceras con tipo reconocible en vez de por las 7.813 entradas reales. Su recuento era bueno (650 `AMEND` frente a 648 indexados); el divisor no. Las cifras de arriba reemplazan a las suyas. Su conclusión cualitativa —la cháchara no es el titular— **sobrevive reforzada**: es la mitad de lo que dijo.

**`AMEND` no se elimina de la instrumentación.** 8,3 % no demuestra patología, pero tampoco demuestra salud. Se degrada de hallazgo a **métrica diagnóstica**: importa si son correcciones triviales o si cada `AMEND` obliga a tres agentes a releer contexto y rehacer trabajo. Se mide en Fase 0-B.

### Fase 0-A — cerrada (2026-08-18)

Barrido completo de los transcripts de la flota. **Universo: 46.423 ficheros `.jsonl`, 27,7 GB, 0 ilegibles.** Nada recortado. Los bytes son los **efectivamente devueltos**, emparejando cada `tool_use` con su `tool_result` por `tool_use_id`; no hay estimación en el numerador ni en el denominador.

| magnitud | valor |
|---|---:|
| Sesiones que **leen** el ledger (de 7.921 que lo mencionan) | 3.139 |
| Llamadas de lectura al ledger | 125.412 |
| Bytes devueltos por ellas | 222,6 MB |
| **Media por llamada** | **1,8 KB ≈ 444 tokens** |
| Ingesta total de la flota por `tool_result` | 1.889,3 MB |
| **► Lectura de ledger / ingesta total** | **11,78 %** |
| Tokens reales de contexto nuevo (`cache_creation`) | 16.121 M |
| ► Tokens de ledger (est.) / contexto nuevo real | 0,35 % |
| **Relecturas del mismo objetivo en la misma sesión** | **63.612 = 50,7 % de las llamadas** |
| Arranque → primera escritura (n=1.413) | p50 **5,7 min** · p90 59,1 min |

**Veredicto: «la ballena es el read-path» queda FALSADA en su forma literal.** La lectura media son 1,8 KB — los agentes hacen `tail`, no `cat`; nadie pasta 357k líneas. Contra el denominador honesto —toda la ingesta por `tool_result`, que sufre la misma amplificación por caché que el numerador— el ledger es el **11,8 %**; el 88 % restante son `tool_result` **no atribuibles al ledger**, que es todo lo que el dato permite afirmar. Llamarlo «trabajar con código» —como decía este párrafo— era una atribución que la medición no sostiene: ese 88 % incluye lecturas de código, sí, pero también web, documentos, salidas de tests y cualquier otra herramienta, y nada en la medición los separa. §2 abre diciendo que ninguna hipótesis se presenta como cerrada sin medida; ésta se presentaba así. El 0,35 % contra `cache_creation` se da como **cota inferior**: un `tool_result` permanece en contexto el resto de la sesión y se re-lee en cada turno, así que el coste real de una lectura no son 444 tokens sino 444 × turnos restantes. El número defendible es el 11,8 %.

**Pero la prioridad del Context Pack sobrevive, por otro motivo:** el **50,7 %** de las lecturas relee algo que esa misma sesión ya había leído. El desperdicio no es tamaño, es **falta de memoria de lo ya leído** — exactamente lo que elimina un pack inmutable por job (§11). v0.2 acertó al ponerlo primero y se equivocó en la razón.

### Sigue abierto

| hipótesis | estado | qué la cerraría |
|---|---|---|
| `tokens_comunicación / tokens_totales_flota` (v0.1 §80) | **no calculable** | Fase 0-B. El proxy de bytes escritos (~8,5 %) **tiene otro denominador** y no autoriza a decir que el objetivo esté cumplido. Métrica secundaria de todos modos (§14). |

---

# §3 · Principal — el modelo que faltaba (P0)

**El error de raíz es tratar `roster` como si fuera `roles`.** `backend`, `harness-biklabs`, `flota`, `64bis`, `code-reviewer`, `bikeus-auto` y `Lead` no son la misma clase de cosa, y hoy el sistema no distingue.

Todo nombre autenticable es un **Principal** y declara su clase.

```yaml
principal:
  id: harness-biklabs
  type: service                    # ver tabla de tipos
  accountable_by: human:albert     # obligatorio salvo type=human
  can_receive_messages: true
  can_claim_jobs: false
  lifecycle: active                # proposed | active | disabled | retired
  project_scope: [llminbox]        # de carriles.tsv; [] = sin ámbito de trabajo
```

### Tipos

| type | recibe mensajes | reclama jobs | está en el organigrama | tiene humano responsable |
|---|---|---|---|---|
| `human` | sí | no | sí (raíz) | es él mismo |
| `role` | sí | **no** | **sí, obligatorio** | sí |
| `agent` | sí | **sí** | vía su `role` | vía su `role` |
| `service` | sí | no | **no** | **sí, obligatorio** |
| `alias` | hereda | **no** (ver abajo) | hereda | hereda |
| `group` | sí | no | no | sí |
| `project` | sí | no | no | sí |
| `legacy` | sí | no | no | opcional |

**Un alias no toma un lease COMO alias.** «Hereda» valía para recibir mensajes y para la autoridad, y contradecía «sólo `agent` reclama» en cuanto se leía literalmente: un alias de un agente parecía poder reclamar. Lo que ocurre es otra cosa — el alias **se canonicaliza primero** al principal al que apunta, y el lease queda firmado por ese principal canónico. Nunca hay una fila de `job_leases` a nombre de un alias.

No es formalismo: el fencing, el watchdog y `agent-hour` (§14) cuentan por `principal_id`. Dos alias del mismo agente firmando leases serían dos ejecutores donde hay uno, y la métrica contaría doble el trabajo de un solo proceso.

Con esto desaparece la anomalía semántica: un `group` recibe mensajes sin tener jefe; un `project` es destino lógico sin reclamar trabajo; un `service` opera herramientas sin formar parte del organigrama; un `alias` no tiene autoridad propia, hereda identidad; un `agent` ejecuta un `role`.

### Regla de admisión al work plane — **invariante duro**

```
principal.type = agent                      ← SÓLO agent. Un rol NO ejecuta.
        ∧ lifecycle = active
        ∧ can_claim_jobs = 1
        ∧ contrato organizativo válido (§6)
        ⇒ puede entrar al work plane

en cualquier otro caso  ⇒  409 not_a_work_principal  + evento
```

**Un rol no ejecuta; un agente ejecuta EN NOMBRE de un rol.** La versión anterior admitía `type ∈ {role, agent}`, y eso vuelve a mezclar identidad organizativa con principal de ejecución **justo después** de que §3 las separe. Las dos cosas viven en columnas distintas y nunca en la misma:

```
Job.owner_role        = backend        ← identidad organizativa · destino de scheduling
lease.principal_id    = backend#03     ← principal concreto que EJECUTA
```

Por qué importa, y no es purismo: si un `role` puede tomar el lease, el fencing pierde su sujeto. `backend` no es un proceso — no muere, no hace heartbeat, no se le puede expirar un lease ni atribuir un agent-hour. Un lease a nombre de un rol es un lease que nadie sostiene y nadie puede perder, así que el watchdog no tiene a quién desalojar y la métrica no tiene a quién contar. Y en la auditoría, «lo hizo backend» deja de responder *quién* lo hizo cuando hay tres agentes bajo ese rol.

`role` conserva todo lo demás: recibe mensajes, es el destino al que se dirige el trabajo (`owner_role`), y es el nivel al que se declara la autoridad. Lo único que pierde es reclamar.

**Falsador F-P1** — un principal `type=service` intenta `POST /jobs/{id}/claim` ⇒ `409`, evento `principal.claim_denied`, y el job permanece `READY`. Si el claim prospera, el modelo de principal no está enforzado y todo lo que se apoya en él (§6, §7, §9) es decorativo.

**Falsador F-P2 (control negativo)** — un principal `type=agent` con contrato válido, `lifecycle=active` y `can_claim_jobs=1` **sí** reclama. Sin este control, F-P1 pasaría con un sistema que deniega a todo el mundo.

**Falsador F-AL1** — un `alias` de `backend#03` reclama un job de `backend` ⇒ **se concede**, y la fila de `job_leases` sale a nombre de `backend#03`, **no** del alias. Sin la canonicalización, el alias recibe un 409 y la spec dice una cosa mientras el sistema hace otra.

**Falsador F-AL2** — un `alias` que apunta a un `role` (no a un `agent`) intenta reclamar ⇒ `409`. Es el que impide que la canonicalización se convierta en un rodeo para que un rol reclame.

**Falsador F-P4** — `backend#03` (agente de `backend`, con alcance en el proyecto) intenta reclamar un job cuyo `owner_role` es `db-migrations` ⇒ `409`. Sin él, «un agente ejecuta en nombre de UN rol» es una frase: el alcance por proyecto no acota el rol, y cualquier agente del proyecto podría tomar cualquier job de él.

**Falsador F-P3** — un principal `type=role`, con contrato válido y activo, intenta `claim` ⇒ `409`. Es el que impide que la separación de §3 se deshaga por la puerta de atrás: sin él, «sólo agent reclama» es una frase del documento y no una propiedad del sistema. Sin este control, F-P1 pasaría con un sistema que deniega a todo el mundo.

### Clasificación de los 16 huérfanos

**No se hace automáticamente.** La asignación de `type` y `accountable_by` es decisión de organigrama, no de código. Lo que hace el código: **exponerlos como deuda clasificable** (§16.3) y **negarles el work plane hasta que la tengan** (regla de admisión, que ya los excluye por no tener contrato).

---

# §4 · Fuente única de organización, compilador y gate de deriva

### 4.1 · Se promueve, no se sustituye

`roles-por-alias.json` ya contiene estado, relaciones, el EM pendiente y las reglas reales de gate. **Crear un `org/*.yaml` paralelo sería fabricar un quinto medio-SoT.** Se promueve el artefacto existente y se cambia su naturaleza: pasa de fichero consultado a **fuente canónica compilada**.

```
                 roles-por-alias.json
                  (CANONICAL ORG SOURCE)
                          │
                       compiler
                          │
       ┌────────┬─────────┼─────────┬──────────┐
       ▼        ▼         ▼         ▼          ▼
    roster   API/org   harnesses  docs     doctor
   (generado)(generado)(generado)(generado)(consume)
```

**Ningún consumidor modifica una proyección.** Editar `roster.json` a mano deja de ser una operación válida.

### 4.2 · El gate de deriva

```bash
llmi org compile          # regenera todo bajo generated/
git diff --exit-code generated/
# ≠0 ⇒ CI FAIL: "una proyección diverge de la fuente"

# Y la mitad que `git diff` NO ve: un fichero NUEVO sin rastrear. El compilador
# puede emitir una proyección de más —una que nadie declaró— y el diff pasa en
# verde, porque git no compara lo que no conoce. Un detector de deriva ciego a
# las adiciones deja entrar exactamente la copia rancia que viene a prohibir.
test -z "$(git status --porcelain --ignored -- generated/)"
# ≠0 ⇒ CI FAIL: "hay ficheros sin rastrear o IGNORADOS bajo generated/"

# `--ignored` no es celo: sin él, un `.gitignore` que cubra `generated/` deja al
# compilador emitir una proyección de más y el gate sigue en verde — el agujero
# más ancho de los tres, porque ignorar ese directorio es una decisión que alguien
# puede tomar por comodidad sin ver que desarma el detector.
#
# Y por encima de los tres, la LISTA CERRADA: el gate compara el conjunto de
# ficheros bajo generated/ contra los artefactos DECLARADOS en la atestación
# (§5). Un fichero que nadie declaró es deriva aunque esté rastreado y limpio.
diff <(cd generated && find . -type f | sort) <(llmi org artifacts --declarados)
# ≠0 ⇒ CI FAIL: "generated/ no coincide con los artefactos declarados"
```

Esto es obligatorio: **SoT + generación sin detector de deriva produce N copias rancias**, que es exactamente el estado actual (`roster.json` + 7 `.bak` + `roster.discovered.json` + `roles-por-alias.json` + `ORGANIGRAMA.md`).

**Falsador F-D1** — añadir `generated/` a `.gitignore` y dejar que el compilador emita un fichero de más ⇒ el gate falla igual. Con `git diff` a secas y sin `--ignored`, ese caso pasa en verde: es el falsador que distingue un detector de deriva de un adorno.

Precedente reutilizable en el repo: `llmi stat` ya tiene un detector de deriva de montaje. Mismo patrón, otro objeto.

### 4.3 · Carga y frescura en el servicio

El fallo de §1.4 tiene tres causas y las tres se cierran:

1. **Bind-mount de fichero único** → se monta el **directorio**, nunca el fichero. Un rename en el host deja de romper el mount.
2. **Carga en tiempo de import** (`lp.JERARQUIA` es un global) → se recarga por mtime+hash, o se recarga bajo demanda con caché corta.
3. **El aviso sólo cubre "ilegible", no "rancio"** → `/organigrama` devuelve siempre `org_revision`, `content_sha256` y `loaded_at`; si el hash en disco difiere del cargado, `stale: true` **en la respuesta**.

**Falsador F-O1** — modificar la fuente en el host y volver a pedir `/organigrama` sin reiniciar ⇒ o refleja el cambio, o devuelve `stale: true`. Servir contenido viejo con `stale: false` es el fallo que hoy ocurre y que este falsador prohíbe.

**Y sin TTL, que no es un detalle de implementación sino parte del contrato.** F-O1 tal como está admite una tercera salida que lo cumple y traiciona su propósito: una caché con TTL corto devuelve contenido viejo con `stale: false` durante toda la ventana, y el falsador pasa si se prueba fuera de ella. Por eso `stale: false` sólo se puede afirmar **habiendo leído la fuente en ESTA petición y coincidiendo el hash**; cualquier otra cosa —ilegible, distinta, no montada, cacheada sin verificar— es `stale: true`. La frescura se comprueba por respuesta, no por reloj.

> Ya implementado y medido: `refrescar_organigrama()` (PR #11) lee **por RUTA en cada petición** y no tiene TTL. Leer por ruta y no por descriptor es lo que derrota al inodo muerto — un bind-mount de FICHERO se queda clavado al inode viejo cuando el host reescribe por `rename`, y ése fue el fallo real: el organigrama estuvo dos días rancio sirviéndose como bueno.

**Falsador F-O1b** — servir dos peticiones separadas por menos que cualquier TTL plausible, con la fuente cambiada entre medias, y exigir que la segunda YA lo refleje. Un caché de N segundos pone esto en rojo; F-O1 a secas no lo distingue.

---

# §5 · Atestación: la aprobación se ata a bytes

La cabecera `_firmado_por / _fecha` se elimina. La aprobación vive **fuera del contenido que aprueba**, en el control plane (tabla `org_attestations`) y espejada en el commit de Git.

```yaml
org_revision: 42
content_sha256: 9f2c…            # de la fuente canónica en esa revisión
approved_by: human:albert
approved_at: 2026-08-18T20:22:00Z
scope: organization              # organization | policy | project
```

```
contenido cambia → hash cambia → la aprobación deja de aplicar
```

### `source_revision` ≠ `active_org_revision`

La propiedad que faltaba no es «rehashear el filesystem en cada claim» — eso pondría la lectura de `roles-por-alias.json` y de todo `generated/` en el camino caliente de cada reclamo, y además ataría la autoridad de la empresa a lo que haya en disco **ahora**: bastaría con que alguien empezara a editar una fuente todavía sin aprobar para que **nadie** pudiera reclamar trabajo. Un editor de texto abierto no puede ser un incidente.

La separación correcta es entre **lo que hay** y **lo que gobierna**:

```
source nueva
   ↓ compile
generated
   ↓ attest          (fuente + artefactos + compilador, juntos)
revisión aprobada
   ↓ activate        (atómico)
active_org_revision  ←──── el work plane consume SÓLO esto
```

Con una revisión 43 en disco mientras la 42 sigue siendo la última atestada:

```
source_revision      = 43
active_org_revision  = 42

→ /organigrama informa pending · unattested · drift
→ los claims siguen gobernados por la 42
→ NADIE obtiene autoridad de la 43
```

Y al revés, el caso en que **sí** hay que parar: si la proyección **activa** no se puede demostrar contra su atestación —artefacto editado, hash que no cuadra— entonces **fail closed y no hay claim**. La diferencia importa: una fuente nueva sin atestar es trabajo en curso; una activa que no se sostiene es corrupción.

```sql
CREATE TABLE org_activation (             -- una sola fila, la verdad del work plane
  singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
  active_org_revision INTEGER NOT NULL REFERENCES org_attestations(org_revision),
  activated_at_epoch INTEGER NOT NULL);
```

**Falsador F-A3** — dejar una revisión 43 sin atestar en disco: los claims siguen concediéndose bajo la 42, y `/organigrama` la reporta `pending`. Si los claims paran, la autoridad está atada al disco y no a lo activado.

**Falsador F-A4** — editar un byte de un artefacto de la revisión **activa**: el claim siguiente falla cerrado.

Un compilado cuya fuente no tiene atestación vigente **no se despliega**: el control plane arranca con la última revisión atestada y avisa; nunca con contenido sin aprobar. Esto sustituye a `gate_delegado_por: ALBERT` como mecanismo — la delegación de gate pasa a ser **una concesión permanente registrada una vez** (§6.4), no una dependencia del operador en cada aprobación.

**La atestación cubre la fuente Y la salida, o no cubre nada.** `content_sha256` identifica la fuente canónica y sólo eso. Entre `compile` y `deploy` hay una brecha: la proyección bajo `generated/` puede quedarse atrás —o editarse a mano— mientras la atestación de la fuente sigue siendo válida y el arranque la acepta. Se estaría verificando la firma de un original que nadie sirve. Por eso la atestación registra las tres cosas y el arranque las comprueba juntas:

```json
{ "org_revision":     42,
  "content_sha256":   "<sha de la FUENTE canónica>",
  "artifacts": { "generated/roster.json":        "<sha256>",
                 "generated/roles-por-alias.json":"<sha256>" },
  "compiler_version": "<sha del compilador que las produjo>" }
```

El arranque recomputa el hash de cada artefacto en disco y lo compara con el atestado. Divergencia ⇒ no arranca. Y `compiler_version` va dentro porque un compilador distinto sobre la misma fuente puede emitir otra proyección: sin él, «la fuente está firmada» no implica «esta salida se deriva de ella».

**Falsador F-A1** — editar un byte de la fuente y desplegar sin re-atestar ⇒ el arranque rechaza el compilado.

**Falsador F-A2** — dejar la fuente y su atestación INTACTAS y editar un byte de `generated/roster.json` ⇒ el arranque rechaza igual. Sin este segundo falsador, F-A1 pasa en verde con la mitad del contrato sin cubrir. Si arranca, la atestación es decorativa.

---

# §6 · Autoridad: cuatro conceptos, cuatro tablas

La matriz de v0.2 §E.2 mezclaba decisiones, ejecución, gates y operaciones (`Merge / fusión`) en una sola tabla. Se separa, porque son cosas distintas con dueños distintos:

### 6.1 · `decision_authority` — quién decide una clase

Clases: `LOCAL_IMPLEMENTATION · INTERFACE · DATA_MODEL · ARCHITECTURE · PRODUCT · SECURITY · INFRA · FINANCIAL · LEGAL · PRODUCTION`.

Valores: `decide` · `recommend` · `consult` · `request` · `none`.

### 6.2 · `execution_permission` — qué operaciones puede ejecutar

`merge` no es una clase de decisión: es una **operación protegida por condiciones**. Aquí viven `merge`, `deploy_prod`, `migrate_schema`, `rotate_secret`, `publish_external`. Cada una con sus precondiciones (gates satisfechos, atestación vigente, ventana).

### 6.3 · `required_review` — qué gates exige un trabajo

**No lo declara el rol. Lo decide el Gate Engine (§7).** El rol sólo declara qué gates *puede ejercer*.

### 6.4 · `risk_acceptance` — quién acepta el riesgo residual

Distinto de bloquear. **`security` puede bloquear por riesgo; `security` no acepta el riesgo residual.** Esa autoridad es del operador o de quien él la haya delegado, registrada como concesión permanente:

```yaml
risk_acceptance:
  SECURITY:  human:albert
  FINANCIAL: human:albert
  ARCHITECTURE: role:cto        # concesión permanente, revisión 42
```

### 6.5 · Relaciones organizativas

`reporta_a` es demasiado pobre. El caso de `infra` ya lo demuestra: reporta al CTO y recibe trabajo de deployment vía EM.

```yaml
id: backend
organization:
  reports_to: engineering-manager      # línea organizativa
  delivery_manager: engineering-manager # quién secuencia y reordena su trabajo
  technical_authority: cto              # quién decide arquitectura sobre él
  product_authority: cpo                # quién decide alcance
escalation:
  architecture: cto
  product: cpo
  security: security
  budget: cfo
gate:
  can_exercise: []                      # los gates que puede EJERCER, no los que exige
```

**Invariante:** `delivery_manager` **nunca** implica autoridad de gate. Un manager reordena; no levanta un gate ajeno. La capa de gate (`security`, `qa`, `sdet`) no cuelga del EM.

**Falsador F-6.1** — un IC intenta una decisión de clase `ARCHITECTURE` ⇒ `403` + evento `authority.denied`.
**Falsador F-6.2** — el autor de un artefacto intenta aprobar su propio gate independiente ⇒ denegado.
**Falsador F-6.3** — `security` intenta *aceptar* riesgo residual (no sólo bloquear) ⇒ `403`: no es suyo.

---

# §7 · Gate Engine: fallar por policy, no por gates

**El fallo no es «esta ruta tiene cero gates».** Hay trabajos que legítimamente deben tener cero gates. El fallo es **«esta ruta no casó con ninguna policy»**.

El Gate Engine devuelve **siempre** una policy identificada:

```json
{ "matched_policy": "POL-127", "policy_revision": 7,
  "policy_sha256": "<sha de los bytes evaluados>", "gates": [] }
{ "matched_policy": "POL-921", "policy_revision": 3,
  "policy_sha256": "<sha de los bytes evaluados>", "gates": ["qa", "security"] }
```

**El identificador solo no basta, y es un fallo de auditoría, no de estilo.** `POL-127` nombra una policy, no unos bytes. Si mañana se edita, el job de ayer queda registrado como «lo aprobó POL-127» y ya no se puede demostrar POR QUÉ avanzó: la policy que se lee hoy no es la que corrió. La pregunta que el audit plane tiene que poder responder —«¿qué regla exacta dejó pasar esto?»— se vuelve incontestable justo cuando alguien la hace, que es después del incidente.

Por eso el job persiste `policy_revision` y `policy_sha256` **junto al veredicto**, no una referencia a un registro mutable. Con eso, reevaluar un job histórico con su policy original es reproducible; sin eso, el registro es una etiqueta.

**Falsador F-G3** — evaluar un job, editar la policy que casó, y reconstruir la decisión desde lo persistido en el job. Si no se puede recuperar el texto exacto que corrió, el registro no sirve para auditar.

Y nunca:

```json
{ "gates": [] }        // ← "no encontré regla, supongo cero"
```

Sin coincidencia:

```
NO_POLICY_MATCH  →  fail closed  →  el job no avanza a REVIEW_PENDING
```

Así existe `NO_GATE` **explícito** en lugar de cero por accidente. Entradas de la decisión: `job.type · risk_tags · changed_paths · artifact.kind · project_policy · environment`.

**Falsador F-7.1** — un job cuyos `changed_paths` no casan con ninguna policy ⇒ `NO_POLICY_MATCH`, el job se bloquea y se emite evento. Si avanza con `gates: []`, el motor está adivinando.
**Falsador F-7.2 (control)** — un job que casa con una policy de cero gates avanza sin revisión y su `matched_policy` queda registrado.

---

# §8 · Tipos: cerrar el camino, no abrir el vocabulario

**Decisión del operador (2026-08-18): no se abre un vocabulario libre.** Los 641 tipos inventados son la prueba de por qué. Pero tampoco se conservan mágicamente ocho palabras eternas.

### 8.1 · Tres cosas separadas

```
canonical semantic kind   +   structured payload   +   raw legacy label
```

Registro canónico **versionado**; los nuevos kinds se añaden al registro, **no se inventan en Markdown**:

| escrito hoy | canonical kind |
|---|---|
| `MEDIDO` · `MEASURED` | `MEASUREMENT` |
| `ADJUDICADO` | `DECISION` |
| `VEREDICTO` | `REVIEW_RESULT` |
| `HEARTBEAT` | `RUNTIME_EVENT` |
| `PRODUCED` | `ARTIFACT_PRODUCED` |
| `AMEND` | `CORRECTION` |

### 8.2 · Nada se descarta

```
raw type desconocido  →  kind = LEGACY_UNKNOWN
                          raw_type = "FOOBAR"     ← se conserva SIEMPRE
```

**Las tres capas viven en tres columnas, y la tercera es la que hace reproducible a las otras dos:**

```sql
ALTER TABLE entries ADD COLUMN raw_tipo          TEXT;     -- el lexema escrito
ALTER TABLE entries ADD COLUMN canonical_kind    TEXT;     -- la interpretación
ALTER TABLE entries ADD COLUMN kind_registry_rev INTEGER;  -- BAJO QUÉ registro
```

`kind_registry_rev` no es metadato decorativo. El registro de tipos es versionado y va a cambiar: sin grabar bajo qué revisión se interpretó cada entrada, una actualización del registro **reinterpreta el pasado en silencio** — una entrada archivada como `LEGACY_UNKNOWN` en la rev 3 pasa a `MEASURED` en la rev 4 sin que nada lo registre, y los informes históricos cambian de valor sin que nadie haya tocado un dato. Con la revisión grabada, reinterpretar es una migración explícita y fechada, no un efecto lateral.

Separación de responsabilidades entre las tres: `raw_tipo` es **derivable** del `head` guardado en cualquier momento (es sintaxis); `canonical_kind` y `kind_registry_rev` **NO lo son** (son interpretación, y su revisión), así que se persisten y no se recalculan.

> Ya en producción: las tres columnas se añadieron en PR #9 por la vía aditiva —no tocan `huella_esquema()`, así que los cursores sobreviven al despliegue— y la migración de `raw_tipo` recomputa el corpus entero desde el `head` guardado, sellada en `meta`. Medido: 32.725 entradas recalculadas, 2.037 de ellas rescatadas de un `tipo` que el lector tiraba. `canonical_kind` y `kind_registry_rev` quedan creadas y **vacías**, esperando al registro de §8.

El comportamiento actual (`tipo = NULL` y la etiqueta se pierde) se elimina. Es lo que hace que 641 entradas parezcan no declarar nada cuando declaran de sobra, y lo que rompe cualquier instrumento que clasifique por tipo.

### 8.3 · El markdown crudo deja de ser una puerta lateral

Un append directo al Markdown **puede** seguir entrando en audit/legacy — la resiliencia histórica del ledger se conserva. Lo que **nunca** puede hacer:

```
crear Job · resolver Decision · levantar Gate · cambiar autoridad · marcar DONE
```

Para eso, necesariamente API/CLI validada. Esto conserva la propiedad de que el ledger funciona con el servicio caído, sin permitir que sea un rodeo al Agent OS.

**Falsador F-8.1** — anexar al Markdown una entrada con forma de `DONE` sobre un job real ⇒ el job no cambia de estado; la entrada queda como `legacy_event`.
**Falsador F-8.2** — publicar `· FOOBAR]` ⇒ se indexa como `LEGACY_UNKNOWN` con `raw_type="FOOBAR"`; `lint` lo cuenta en su clase, no como «sin tipo».

---

# §9 · Job y máquina de estados

```
DRAFT → QUEUED → READY → CLAIMED → RUNNING → RESULT_SUBMITTED
                                      ↓ ↑         ↓
                                    BLOCKED   REVIEW_PENDING
                                                  ↓        ↓
                                            APPROVED  CHANGES_REQUESTED
                                                  ↓        ↓
                                               DONE     RUNNING
```

Terminales adicionales: `FAILED` · `CANCELLED`. `ESCALATED` **no es un estado**: es una dimensión independiente (`escalation_open: bool`) que convive con `RUNNING` o `BLOCKED`.

**`unblock` es una transición con contrato, no un botón.** La API expone `POST /jobs/{id}/unblock` y §9 no decía de dónde sale ni adónde va, que es justo lo que un worker necesita saber para no quedarse esperando un lease que ya no tiene:

| | |
|---|---|
| estado origen | `BLOCKED`, y **sólo** `BLOCKED`. Desde cualquier otro ⇒ `409`. |
| estado destino | `READY`. No vuelve a `CLAIMED`: el que lo bloqueó puede llevar horas muerto. |
| lease | **se libera** en la misma transacción, y `lease_generation` se incrementa. |
| quién puede | el actor autorizado por la policy del gate que lo bloqueó, no necesariamente quien lo reclamó. |

Que vuelva a `READY` y no a `CLAIMED` es la decisión que importa: devolverlo a su dueño anterior supone que ese dueño sigue vivo y sigue siendo el correcto, y las dos suposiciones fallan justo en el caso que motiva un bloqueo. Volviendo a `READY` el job se vuelve a reclamar por las reglas normales, y el incremento de generación invalida cualquier token viejo que ande suelto — sin él, un worker resucitado podría enviar resultado sobre un job que ya reclamó otro.

**Falsador F-J2** — bloquear un job, desbloquearlo, y que el worker original intente `submit` con su token de antes ⇒ rechazo por generación. Si lo acepta, el fencing no cubre el desbloqueo.

**Sólo el servidor persiste transiciones.** El agente solicita; el servidor comprueba lease válido · actor autorizado · artefacto presente y del tipo esperado · presupuesto · estado origen legal. Un Job sin criterios de aceptación no pasa a `READY` salvo tipos explícitamente exploratorios.

---

# §10 · Lease atómico y fencing — desde el primer claim

**No se introduce Postgres todavía.** Para ~16 agentes, una instalación y pocos claims por segundo, SQLite en WAL con transacción corta ejecuta el piloto perfectamente. Postgres entra cuando haya varias réplicas, multi-host, o contención medible.

**El lease es atómico y con fencing desde el día uno.** Un `claim` sin exclusión es una semántica provisional que después hay que romper.

```sql
BEGIN IMMEDIATE;

-- CANONICALIZACIÓN DEL ALIAS, PRIMERO Y DENTRO DE LA TRANSACCIÓN. §3 dice que un
-- alias no reclama COMO alias, y eso hasta aquí era prosa: el flujo usaba
-- `:principal` tal cual contra `principal_scopes`, `principals` y `job_leases`,
-- así que un alias simplemente fallaba `p.type='agent'` y recibía un 409 opaco —
-- «no puedes reclamar» en vez de resolverse al agente que representa.
--
-- Se resuelve UN SALTO, no una cadena: `aliases_of` apuntando a otro alias es un
-- ciclo esperando a existir, y el compilador del Org SoT (§4) ya rechaza esa
-- forma. Si tras el salto no hay un `agent`, se rechaza explícitamente.
-- LA REVISIÓN QUE GOBIERNA, leída UNA vez y usada en todo el bloque. No se
-- rehashea nada del filesystem aquí: `active_org_revision` ya es el resultado de
-- haber verificado fuente + artefactos + compilador en la ACTIVACIÓN (§5).
activa = SELECT active_org_revision FROM org_activation WHERE singleton = 1;

canonico = SELECT COALESCE(p.aliases_of, p.id) FROM principals p
            WHERE p.id = :principal AND p.org_revision = activa;
if canonico is None:
    ROLLBACK; return 409 unknown_principal

-- A partir de aquí TODO usa `canonico`, nunca `:principal`. El lease lo firma el
-- principal canónico: si lo firmara el alias, el fencing, el watchdog y
-- `agent-hour` contarían dos ejecutores donde hay un proceso.

-- ⚠️ EL `:job` VA EN EL SELECT. Sin él, este bloque autoriza un job y reclama
-- OTRO: todas las comprobaciones de abajo —proyecto, rol, dependencias, alcance,
-- admisión— caen sobre la fila que el SELECT elige, mientras el UPDATE toca la
-- que el cliente nombró en `POST /jobs/{id}/claim`. Un worker pasaba el id de un
-- job de otro proyecto o de otro rol y se lo llevaba: el UPDATE sólo miraba
-- `status='READY'`. Era un bypass de autorización completo, y lo introduje yo al
-- meter las comprobaciones en el SELECT sin atar el objetivo.
--
-- `:job` es NULL en `/work/next` (el servidor elige) y lleva valor en
-- `POST /jobs/{id}/claim` (lo elige el cliente). El resto es idéntico.
SELECT id FROM jobs
 WHERE status = 'READY'
   AND (:job IS NULL OR id = :job)                     -- ← el objetivo, atado
   AND project_id = :project
   AND owner_role = :role
   AND id NOT IN (SELECT job_id FROM job_dependencies WHERE satisfied = 0)
    -- TODO dato organizativo que participe en autorización va atado a la revisión
   -- ACTIVA, no a la última que exista. Sin esto se puede activar la 43 y seguir
   -- concediendo por una fila de alcance de la 42 que nadie retiró: la
   -- reorganización se aplicaría a medias, y la mitad que no se aplica es
   -- justamente la que otorga permisos.
   AND EXISTS (SELECT 1 FROM principal_scopes ps          -- §6: aislamiento EJECUTABLE
                WHERE ps.principal_id = canonico
                  AND ps.project_id   = jobs.project_id
                  AND ps.org_revision = activa)
   -- Y LA ADMISIÓN AL WORK PLANE, EN LA MISMA TRANSACCIÓN. El alcance dice a QUÉ
   -- proyectos, no SI puede reclamar: un principal deshabilitado o un `role` que
   -- conserve su fila de alcance reclamaría igual. La invariante de §3 vive aquí
   -- o no vive en ninguna parte — comprobarla en la capa de aplicación deja una
   -- ventana entre la comprobación y el UPDATE.
   AND EXISTS (SELECT 1 FROM principals p
                WHERE p.id = canonico
                  AND p.type           = 'agent'        -- §3: un rol NO ejecuta
                  AND p.lifecycle      = 'active'
                  AND p.can_claim_jobs = 1
                  AND p.role_id        = jobs.owner_role   -- EN NOMBRE DE QUIÉN
                  AND p.org_revision   = activa)
 ORDER BY priority DESC, created_at ASC
 LIMIT 1;

elegido = <la fila del SELECT>
if elegido is None:
    ROLLBACK
    return 409                              -- no hay job autorizado que reclamar

-- Y EL UPDATE APUNTA A ESA FILA, no a `:job`. Repetir aquí `status='READY'` no es
-- redundante: es lo que detecta que otro worker ganó entre el SELECT y esta
-- línea. Lo que no puede repetirse es el objetivo — tiene que ser el MISMO.
row = UPDATE jobs
         SET status = 'CLAIMED',
             lease_generation = lease_generation + 1
       WHERE id = elegido.id AND status = 'READY'
   RETURNING lease_generation;

-- UN SOLO MECANISMO demuestra que se ganó el claim: la fila devuelta. Si no hay
-- fila, otro worker ganó la carrera entre el SELECT y el UPDATE y no hay nada que
-- arrendar. (Nada de `changes()` en paralelo: dos mecanismos para la misma
-- pregunta es una oportunidad de que discrepen.)
if row is None:
    ROLLBACK
    return 409                              -- «otro se lo llevó», no un 500

gen = row.lease_generation                  -- la generación REAL, capturada

-- El lease REGISTRA bajo qué revisión se autorizó. No se congela el JOB a una
-- revisión vieja —una reorganización debe afectar a quién está autorizado AHORA—,
-- pero después se puede demostrar «backend#03 reclamó esto bajo la org rev 42».
-- Congelar el job perdería lo primero; no registrar nada perdería lo segundo.
INSERT INTO job_leases (job_id, principal_id, lease_generation,
                        claimed_at_epoch, expires_at_epoch, ttl_seconds, org_revision)
VALUES (elegido.id, canonico, gen, :now_epoch, :now_epoch + :ttl_seconds, :ttl_seconds, activa);

COMMIT;
```

**Dos correcciones que la versión anterior de este bloque no tenía, y las dos producían corrupción silenciosa:**

**① El guarda estaba escrito como comentario.** Decía `-- guardia: 0 filas ⇒ otro ganó` y luego seguía al `INSERT` y al `COMMIT` pase lo que pase. Con dos workers en la carrera, el perdedor insertaba un lease sobre un job que **ya tenía dueño** y se llevaba un token que el fencing daría por bueno: exactamente el doble claim que §10 existe para impedir. Una comprobación que vive en un comentario no comprueba nada — el mismo defecto que el resto de esta spec persigue, cometido en su propio pseudocódigo.

**② `:gen` no venía de ninguna parte.** No lo devolvía el `SELECT` ni el `UPDATE`: era un parámetro libre, y el `INSERT` podía grabar una generación distinta de la que el `UPDATE` acababa de escribir. El fencing compara generaciones; si la del lease no es la del job, compara contra basura. Ahora sale del `RETURNING` del propio `UPDATE`, que es el único sitio donde ese número existe de verdad.

**③ `:now + :ttl` no es aritmética de fechas.** Si `:now` llega como ISO 8601, SQLite lo **coacciona a número** para poder sumar: `'2026-08-19T14:00:00Z' + 3600` da `3600`, no una fecha. El lease nacería caducado en 1970 y el barrido de expirados se lo llevaría de inmediato — un lease que se evapora sin que nadie vea un error. Se fija la unidad: `ttl_segundos` es un entero de segundos, y la suma se hace en epoch (`unixepoch()`). La alternativa equivalente es `datetime(:now, '+' || :ttl_segundos || ' seconds')`; lo que no vale es `+` a secas sobre un texto.

El token que se entrega al worker contiene `job_id · principal_id · lease_generation`.

**Falsador F-L1** — dos workers reclamando el MISMO job a la vez: exactamente uno recibe token, el otro recibe `409`. Si los dos reciben token, el guarda no está.

**Falsador F-L2** — reclamar un job y leer `expires_at`: tiene que caer en el futuro, a `ttl_segundos` de `:now`. Un `expires_at` en 1970 es la suma sobre texto, y pasa desapercibida porque el lease simplemente «desaparece».

### El lease vencido: quién lo recoge

`unblock` (§9) sólo cubre `BLOCKED → READY`, que es el bloqueo **deliberado**. Falta el caso que de verdad ocurre solo: un agente muere con el lease tomado, en `CLAIMED` o `RUNNING`. Sin nadie que lo recoja, ese job **no se puede reclamar nunca más** — y no hay error, ni evento, ni nada que lo delate: simplemente deja de avanzar.

```
watchdog, en una transacción por lease. Las CUATRO condiciones, simultáneas:

  lease.expires_at_epoch  <= now_epoch
  ∧ lease.released_at_epoch IS NULL
  ∧ job.status IN ('CLAIMED','RUNNING')                  -- NUNCA un terminal
  ∧ lease.lease_generation = job.lease_generation        -- sólo el VIGENTE

    → job.status = READY
    → job.lease_generation += 1        -- invalida el token del muerto
    → lease.released_at_epoch = min(now_epoch, lease.expires_at_epoch)
    → evento lease.expired
```

**Y la invariante general, que es la que hace del watchdog una red y no el mecanismo:**

```
toda transición que ABANDONE {CLAIMED, RUNNING}
    → libera el lease vigente EN LA MISMA TRANSACCIÓN
```

Incluye `RESULT_SUBMITTED`, `BLOCKED`, `FAILED`, `CANCELLED` y `DONE` — todas. El watchdog recupera **workers muertos**; no arregla estados terminales mal persistidos. Si es lo único que sella leases, el estado normal del sistema pasa a ser «leases colgando», y una red que se usa siempre deja de ser una red.

**Las dos condiciones de más no son celo, son la diferencia entre recoger y destruir.** Un job que llegó a `DONE`, `FAILED` o `CANCELLED` puede conservar su lease abierto —porque la transición terminal se olvidó de sellarlo, que es justo el descuido que este watchdog existe para tolerar— y sin el filtro de estado el watchdog lo **resucita a `READY`**: un trabajo ya entregado vuelve a la cola y se hace dos veces. Y sin el filtro de generación, un lease viejo de una ronda anterior desaloja al dueño ACTUAL, que está vivo y trabajando.

Corolario, y va en el servidor: **toda transición terminal libera su lease en la misma transacción**. El watchdog es la red, no el mecanismo — si es lo único que sella leases, entonces el estado normal del sistema es «leases colgando», y una red que se usa siempre deja de ser una red.

**Falsador F-L5** — un job en `DONE` con un lease sin `released_at` y ya expirado: tras pasar el watchdog sigue en `DONE`. Si vuelve a `READY`, el filtro no está.

Tres detalles que no son de forma:

- **`released_at = min(now, expires_at)`**, no `now`: el lease dejó de estar sostenido cuando expiró, no cuando el watchdog pasó a mirarlo. Sellarlo con `now` regalaría agent-hour proporcional al retraso del watchdog (§14).
- **`lease_generation += 1`** aquí también: si el proceso «muerto» resucita y envía resultado, su token es de la generación anterior y el fencing lo rechaza. Sin esto, el watchdog crea el doble claim que §10 evita en el camino normal.
- **evento `lease.expired`**, porque un job que vuelve a `READY` sin rastro es indistinguible de uno que nunca se reclamó, y eso borra la única señal de que hay un agente cayéndose.

**Falsador F-L3** — reclamar un job, matar al worker sin liberar, esperar a `expires_at` ⇒ el job vuelve a `READY` y **otro** worker lo reclama. Sin watchdog el job se queda muerto para siempre y F-10.2 no es implementable.

**Falsador F-L4** — el worker «muerto» resucita tras el desalojo y envía `submit` con su token ⇒ rechazo por generación.

### Fencing — el caso feo del failover

```
Backend A trabaja offline (control plane caído)
      → vuelve el servidor → el lease de A parece expirado
      → se reasigna a Backend B con lease_generation = 8
      → vuelve A e intenta entregar con generation = 7
```

```
submit(generation=7) cuando jobs.lease_generation = 8
        ↓
   STALE_FENCE
```

El commit de A **se conserva como artefacto recuperable** (nada de trabajo se tira), pero **no puede mutar el Job**: no adquiere autoridad. Es la invariante que faltaba en v0.1 y v0.2.

**Falsador F-10.1** — 20 workers reclaman simultáneamente un job `READY` ⇒ exactamente un lease válido; 19 reciben `409 already_claimed`.
**Falsador F-10.2** — matar el proceso poseedor ⇒ el job vuelve a ser reclamable sin intervención humana.
**Falsador F-10.3** — `submit` con `lease_generation` vieja ⇒ `STALE_FENCE`, el artefacto se registra, el Job no cambia de estado.

### Heartbeats

Los emite el **runtime**, no el LLM. Cero tokens. Un LLM no escribe nunca «sigo trabajando».

---

# §11 · Context Pack

Inmutable, versionado, generado al reclamar.

**Por qué es prioritario — medido, no supuesto (§2, Fase 0-A):** no porque el ledger sea grande (la lectura media son 1,8 KB), sino porque **el 50,7 % de las lecturas relee algo que la misma sesión ya había leído**. Un pack inmutable por job elimina esa clase entera: lo que el job necesita se entrega una vez, con provenance, y no se vuelve a buscar.

**Contiene:** rol · job · objetivo · criterios de aceptación · autoridad efectiva · resumen del padre (≤400 tok) · resultados de dependencias **por referencia** · decisiones/ADR relevantes con `ref+version+hash` · entrypoints de código · worktree · artefacto esperado.

**No contiene automáticamente:** ledger · inbox histórico · conversaciones de otros equipos · toda la wiki · todos los jobs del epic · pensamientos de otros agentes.

**Presupuesto:** coordinación base **≤12k tokens**. Más contexto exige retrieval explícito y justificado.

**Frontera de carril:** el pack de un job del proyecto `P` no incluye material de otro proyecto. `project_id` se deriva de `carriles.tsv`, que ya es el SoT de carriles y no se reinventa.

**Invalidación:** si una dependencia crítica cambia tras generar el pack, se **INSERTA** su invalidación (§15) y el refresco es obligatorio antes de cualquier acción irreversible. `stale` **no es un campo que se escriba**, es una propiedad **derivada**:

```
stale(pack) ≡ EXISTS (SELECT 1 FROM context_pack_invalidations WHERE pack_id = pack.id)
```

Y refrescar **crea otro `context_pack`**, no edita el anterior. Una versión previa de esta línea decía literalmente `stale = true`, que contradice la inmutabilidad de §15: un pack que se marca a sí mismo rancio es un pack que se edita, y entonces «esto es lo que el agente recibió» deja de ser reconstruible — que es la única razón por la que se persiste.

**Falsador F-11.1** — un proyecto con millones de tokens de historia; un job nuevo recibe pack acotado y no la historia. Medido en tokens reales del pack, no en su descripción.

---

# §12 · CONSULT acotado

Sin protocolo estricto, CONSULT reconstruye Slack en dos semanas. Y hay evidencia de que **esta flota extiende cualquier canal abierto que se le dé**: los 641 tipos inventados lo demuestran empíricamente.

```yaml
consult:
  shape: one_question_one_answer   # invariante
  max_tokens_question: 700
  max_tokens_answer: 1200
  ttl: 4h
  follow_ups_allowed: 0
```

Si hace falta una segunda iteración significativa, **se convierte en Child Job o en Decision**. No hay hilo.

**Falsador F-12.1** — intentar un follow-up sobre un CONSULT respondido ⇒ `409`, con el puntero a crear Child Job o Decision.

---

# §13 · Engineering Manager: ciclo de vida, no liveness

Organización y liveness son conceptos distintos. **La jerarquía no cambia porque haya un proceso corriendo.**

```yaml
engineering-manager:
  lifecycle: proposed | active | disabled
```

La transición `proposed → active` es **administrativa y la aprueba el operador**, con atestación (§5). Una vez `active`:

```
backend.delivery_manager   = engineering-manager
backend.technical_authority = cto
```

…aunque el proceso EM esté temporalmente muerto. Si lo está:

```
decisiones de management → pending
scheduler                → sigue sirviendo READY
```

Fallback opcional y **explícito**, nunca consecuencia accidental de un heartbeat:

```yaml
acting_manager: cto
after: 30m
```

**Falsador F-13.1** — matar el LLM del EM ⇒ los jobs `READY` se siguen ejecutando; sólo queda pendiente lo que exige juicio de management.

*Nota:* el estado actual del fichero ya resuelve bien la mitad de esto (`estado: pendiente_arranque`, `be/fe/db-migrations` siguen en `cto`, con `reporta_a_al_arrancar_em` y la condición escrita: *«no se enruta a un jefe que no corre»*). Lo que cambia es que la activación pasa a ser **administrativa y atestada**, no derivada de que un proceso arranque.

---

# §14 · Métricas y North Star

El KPI de v0.1 §80 invita a Goodhart: `communication_tokens / total_tokens` mejora sólo con que un agente genere mucho más código, aunque siga coordinándose mal. **Se degrada a métrica de eficiencia secundaria.**

### North Star

```
accepted_jobs / agent-hour
median(READY → ACCEPTED)
tokens_or_cost / accepted_job
```

**`ACCEPTED` ≡ `DONE`.** No es un predicado que se evalúe después, y esa era la parte que estaba mal en la versión anterior de este bloque: definirlo como «`DONE` que además cumplía X» obliga a **reinterpretar retrospectivamente** si un `DONE` era aceptado de verdad, y deja convivir en la tabla `DONE`s válidos e inválidos distinguibles sólo por una consulta que hay que acordarse de escribir igual en todas partes.

**La regla se mueve al servidor: un `DONE` inválido tiene que ser IMPOSIBLE, no excluido de una métrica después.** El servidor rechaza la transición a `DONE` si falta cualquiera de las tres:

```
acceptance_criteria satisfechos
∧ artefacto entregado conforme a artifact_contract
∧ TODOS los required_gates en APPROVED
⇒ se permite DONE

en cualquier otro caso ⇒ 409, y el job NO transiciona
```

`FAILED` y `CANCELLED` **no son formas de `DONE`**: son terminales alternativos de la propia máquina de estados de §9. Un job que fracasa no llega a `DONE` y por tanto no aparece en el KPI — sin necesidad de excluirlo.

| sello | cuándo | regla |
|---|---|---|
| `jobs.ready_at_epoch` | primera entrada en `READY` | **no se reescribe** al volver de un `unblock`. Si se reescribiera, bloquear un job mejoraría su latencia y la métrica premiaría bloquear. |
| `jobs.done_at_epoch` | transición a `DONE` | única, terminal. |

**Denominador de `agent-hour`:** tiempo de lease **efectivamente sostenido**, no tiempo de reloj ni sesiones abiertas. Un agente con el proceso arrancado y sin lease no consume agent-hour — si contara, apagar agentes ociosos «mejoraría» la productividad sin entregar nada más.

Y hay que decir **cómo se calcula un lease que sigue vivo**, porque `released_at − claimed_at` sobre un lease activo da NULL y lo excluye del sumatorio en silencio:

```
Σ ( min( COALESCE(released_at_epoch, now_epoch), expires_at_epoch ) − claimed_at_epoch ) / 3600.0
      ^^^                                              ^^^^^^^^^^^^^^^^      ^^^^^^^^
      el tope se aplica SIEMPRE, no sólo a los vivos                 la resta da SEGUNDOS
```

El tope va **fuera** del `COALESCE`, y eso es lo que arregla el caso que la versión anterior regalaba: si una transición terminal ocurre **después** de que el lease expirara pero antes de que el watchdog pase, `released_at_epoch` queda posterior a `expires_at_epoch` y se contabiliza tiempo que el lease ya no sostenía. Con el tope sólo sobre la rama viva, ese hueco quedaba abierto justo cuando el sistema va con retraso, que es cuando más importa.

La propiedad correspondiente en la escritura, que es la otra mitad:

```
released_at_epoch <= expires_at_epoch        -- invariante
toda liberación escribe  min(now_epoch, expires_at_epoch)
```

La división por 3.600 no es cosmética: sin ella el denominador va inflado ×3.600 y `accepted_jobs / agent-hour` sale **3.600 veces** menor de lo que es. Un North Star con un factor constante mal puesto no se detecta comparándolo consigo mismo — sólo cuando alguien intenta contrastarlo con la realidad, meses después.

Y los dos extremos del otro KPI van también en **epoch INTEGER** (`ready_at_epoch`, `done_at_epoch`): `median(READY → ACCEPTED)` necesita restar, y restar exige una unidad. Con `TEXT` la resta o falla o —peor— coacciona y da un número.

Con dos exigencias más que lo hacen calculable: el **instante de corte** de un lease vivo es `min(now, expires_at)` —nunca más allá de su expiración, o un proceso muerto acumularía horas para siempre—, y el **watchdog escribe `released_at`** al expirar (ver §10), de modo que un lease sólo permanece sin sellar mientras de verdad está sostenido.

**Falsador F-N1** — un job que termina en `FAILED` y otro al que le falta un gate: ninguno de los dos puede llegar a `DONE`. Si alguno llega, la regla está en la métrica y no en el servidor, que es donde la versión anterior la puso.

**Falsador F-N2** — un agente con proceso arrancado y sin ningún lease durante una hora: su `agent-hour` es **0**.

*Se quiere una empresa que entregue más, no una empresa que hable menos.* Si el Agent OS gasta los mismos tokens y termina el doble de trabajo en la mitad de tiempo, ha ganado aunque el ratio no baje.

### Secundarias

`coordination_tokens / completed_job` · `blocked_time` · `review_loops` · `rework_rate` · `reopen_rate` · `consults_per_job` · `delegations_per_job` · `escalations_per_job` · **`amend_rate`** (diagnóstica, §2).

---

# §15 · Modelo de datos (piloto, SQLite)

```sql
-- ORGANIZACIÓN (proyecciones compiladas; la fuente es roles-por-alias.json)
CREATE TABLE principals (
  id TEXT PRIMARY KEY,
  type TEXT NOT NULL CHECK (type IN
    ('human','role','agent','service','alias','group','project','legacy')),
  accountable_by TEXT,                       -- principal.id, NULL sólo si type='human'
  can_receive_messages INTEGER NOT NULL DEFAULT 1,
  can_claim_jobs INTEGER NOT NULL DEFAULT 0,
  lifecycle TEXT NOT NULL DEFAULT 'active'
    CHECK (lifecycle IN ('proposed','active','disabled','retired')),
  aliases_of TEXT,                           -- si type='alias'
  -- §3 dice que un `agent` está en el organigrama «vía su role», y esa relación
  -- no estaba en ninguna columna: sin ella, `backend#03` reclama un job de
  -- `db-migrations` sin más que pasar `:role=db-migrations`, porque el alcance
  -- dice a QUÉ proyectos, no EN NOMBRE DE QUIÉN.
  role_id TEXT REFERENCES principals(id),    -- obligatorio si type='agent', NULL en el resto
  org_revision INTEGER NOT NULL,

  -- COMBINACIONES IMPOSIBLES, impuestas por la base y no por la prosa. El modelo
  -- de §3 las prohibía en texto y el DDL las dejaba pasar todas: un `service` con
  -- can_claim_jobs=1, un `alias` sin `aliases_of`, un `role` con `role_id`, un no
  -- humano sin responsable. Una tabla que admite estados que el modelo declara
  -- imposibles convierte cada consulta en una comprobación defensiva.
  CHECK ((type = 'agent') = (role_id IS NOT NULL)),
  CHECK ((type = 'alias') = (aliases_of IS NOT NULL)),
  CHECK ((type = 'human') = (accountable_by IS NULL)),
  CHECK (can_claim_jobs = 0 OR type = 'agent'),          -- §3: sólo agent reclama
  CHECK (type <> 'service' OR accountable_by IS NOT NULL)
);
-- `role_id` REFERENCES principals(id) sólo garantiza que existe, no que sea un
-- ROL: SQLite no expresa «FK a las filas con type='role'». Lo valida el compilador
-- del Org SoT (§4) en la misma pasada de admisión que estos CHECK, y es un fallo
-- de compilación, no un aviso — un agente que dice actuar en nombre de algo que
-- no es un rol no se despliega.

CREATE TABLE org_relations (
  principal_id TEXT NOT NULL,
  reports_to TEXT, delivery_manager TEXT,
  technical_authority TEXT, product_authority TEXT,
  org_revision INTEGER NOT NULL,
  PRIMARY KEY (principal_id, org_revision)
);

CREATE TABLE org_attestations (
  org_revision INTEGER PRIMARY KEY,
  content_sha256 TEXT NOT NULL,                -- la FUENTE canónica
  -- §5 dice que la atestación cubre fuente Y salida Y compilador, y la tabla sólo
  -- guardaba la fuente: la mitad del contrato no tenía dónde escribirse, así que
  -- «verificamos los artefactos» era una frase sin respaldo en el esquema.
  artifacts_json TEXT NOT NULL,                -- {ruta: sha256} canónico
  artifacts_manifest_sha256 TEXT NOT NULL,     -- hash del propio manifiesto
  compiler_version TEXT NOT NULL,              -- otro compilador ⇒ otra salida
  approved_by TEXT NOT NULL, approved_at TEXT NOT NULL,
  scope TEXT NOT NULL
);

-- AUTORIDAD (cuatro conceptos, cuatro tablas — §6)
-- ALCANCE POR PROYECTO. `project_scope` vivía sólo en el YAML del modelo, y la
-- invariante de seguridad exige aislamiento entre proyectos: una autoridad que
-- no está en el DDL no la puede aplicar ninguna consulta, así que el aislamiento
-- quedaba dependiendo de que cada `WHERE` se acordara. Aquí se vuelve ejecutable.
--
-- ⚠️ Y NO se infiere del nombre. Que un alias sea `em-bikeus` NO otorga alcance
-- sobre `bikeus`: eso sería que el software se invente la autoridad leyendo una
-- cadena. El alcance se declara, fila a fila, o no existe.
CREATE TABLE principal_scopes (
  principal_id TEXT NOT NULL, project_id TEXT NOT NULL,
  granted_by TEXT NOT NULL,               -- quién lo otorgó: sin esto no es auditable
  granted_at TEXT NOT NULL,
  -- REVISIONADO como el resto de lo organizativo. Sin `org_revision` se podía
  -- activar la 43 y conservar una concesión de proyecto de la 42: la parte de la
  -- reorganización que NO se aplica sería justamente la que da permisos.
  org_revision INTEGER NOT NULL,
  PRIMARY KEY (principal_id, project_id, org_revision));

CREATE TABLE decision_authority (
  principal_id TEXT, decision_class TEXT, level TEXT
    CHECK (level IN ('decide','recommend','consult','request','none')),
  org_revision INTEGER, PRIMARY KEY (principal_id, decision_class, org_revision));

CREATE TABLE execution_permission (
  principal_id TEXT, operation TEXT, conditions TEXT,   -- JSON
  org_revision INTEGER, PRIMARY KEY (principal_id, operation, org_revision));

CREATE TABLE gate_capability (                          -- qué gate PUEDE ejercer
  principal_id TEXT, gate TEXT, delegated_by TEXT,
  org_revision INTEGER, PRIMARY KEY (principal_id, gate, org_revision));

CREATE TABLE risk_acceptance (
  decision_class TEXT PRIMARY KEY, principal_id TEXT NOT NULL,
  org_revision INTEGER NOT NULL);

-- TRABAJO
CREATE TABLE jobs (
  id TEXT PRIMARY KEY, project_id TEXT NOT NULL, parent_id TEXT,
  title TEXT NOT NULL, type TEXT NOT NULL, objective TEXT NOT NULL,
  requested_by TEXT NOT NULL, manager_role TEXT, owner_role TEXT NOT NULL,
  priority INTEGER NOT NULL DEFAULT 50,
  status TEXT NOT NULL, escalation_open INTEGER NOT NULL DEFAULT 0,
  lease_generation INTEGER NOT NULL DEFAULT 0,          -- fencing, §10
  acceptance_criteria TEXT NOT NULL,                    -- JSON, no vacío salvo exploratorio
  artifact_contract TEXT NOT NULL, risk_tags TEXT,
  -- §7 EXIGE persistir revisión y bytes de la policy para poder reconstruir por
  -- qué avanzó un job, y el DDL sólo guardaba el identificador: la afirmación de
  -- §7 no se podía representar en esta tabla.
  matched_policy  TEXT    NOT NULL,                    -- los fija el Gate Engine, §7
  policy_revision INTEGER NOT NULL,
  policy_sha256   TEXT    NOT NULL,
  required_gates  TEXT    NOT NULL,
  budget TEXT,
  -- La FK sola prueba que el pack EXISTE, no que sea de ESTE job: `job-A` podía
  -- apuntar al pack de `job-B` y la base lo aceptaba. Se impone la pertenencia
  -- con una FK COMPUESTA contra una clave que incluye el job.
  context_pack_id TEXT,                                 -- §11: QUÉ contexto recibió
  FOREIGN KEY (id, context_pack_id) REFERENCES context_packs(job_id, id),
  ready_at_epoch INTEGER, done_at_epoch INTEGER,         -- §14: los dos extremos del KPI
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL);

CREATE TABLE job_dependencies (
  job_id TEXT, depends_on TEXT, satisfied INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (job_id, depends_on));

-- TIEMPOS EN EPOCH INTEGER, TODOS. La versión anterior mezclaba `claimed_at` en
-- ISO con un `expires_at` calculado en epoch, y luego el watchdog y las métricas
-- comparaban los dos mundos. Mezclar representaciones temporales DENTRO de una
-- misma entidad es cómo se cuela una comparación lexicográfica entre un texto y
-- un número: no falla, da un resultado — y el lease se evapora o no caduca nunca.
CREATE TABLE job_leases (
  job_id TEXT NOT NULL REFERENCES jobs(id),
  principal_id TEXT NOT NULL REFERENCES principals(id),
  lease_generation INTEGER NOT NULL,
  claimed_at_epoch  INTEGER NOT NULL,
  expires_at_epoch  INTEGER NOT NULL,
  released_at_epoch INTEGER,                -- NULL = sostenido
  ttl_seconds       INTEGER NOT NULL CHECK (ttl_seconds > 0),
  org_revision      INTEGER NOT NULL,       -- bajo QUÉ organización se autorizó
  CHECK (released_at_epoch IS NULL OR released_at_epoch <= expires_at_epoch),
  -- `NOT NULL` no impide 0 ni negativos, y con cualquiera de los dos el lease
  -- nace ya expirado: el watchdog lo desaloja en su primera pasada y el job entra
  -- en un ciclo de claim-y-desalojo que parece contención y es aritmética.
  CHECK (expires_at_epoch > claimed_at_epoch),
  PRIMARY KEY (job_id, lease_generation));

-- GOBERNANZA
CREATE TABLE reviews (
  id TEXT PRIMARY KEY, job_id TEXT NOT NULL, gate TEXT NOT NULL,
  reviewer_principal TEXT, verdict TEXT
    CHECK (verdict IN ('APPROVED','CHANGES_REQUESTED','BLOCKED')),
  -- UN VEREDICTO SIN ACTOR NI SELLO NO ES UNA DECISIÓN. La tabla admitía
  -- `verdict='APPROVED'` con `reviewer_principal` y `decided_at` en NULL: una
  -- aprobación que nadie firmó y que no ocurrió en ningún momento. Es justo lo
  -- que el audit plane tiene que poder responder —quién y cuándo— y era
  -- exactamente lo que se podía dejar vacío.
  CHECK ((verdict IS NULL) = (reviewer_principal IS NULL)),
  CHECK ((verdict IS NULL) = (decided_at IS NULL)),
  -- LA INVARIANTE 10 EXIGE ESTO Y LA TABLA NO LO TENÍA: un veredicto atado a un
  -- `job_id` aprueba el JOB, no unos BYTES. Entre la aprobación y la entrega el
  -- artefacto puede cambiar, y el APPROVED de ayer se lee como si cubriera lo de
  -- hoy. Es la firma en blanco que la invariante prohíbe.
  --
  -- Una aprobación cubre UNA revisión: si aparece una revisión nueva del mismo
  -- artefacto, la aprobación anterior DEJA DE APLICAR y el gate vuelve a pedirse.
  -- Genérico A PROPÓSITO. `commit sha` sirve para código y Agent OS va a gobernar
  -- documentos, contratos, migraciones, informes, diseños, datasets — cosas que no
  -- viven en git. Un contrato de revisión atado a git obliga a meter en git lo que
  -- no le corresponde, o a dejar sin cubrir todo lo demás.
  artifact_id       TEXT NOT NULL,        -- QUÉ artefacto
  artifact_revision TEXT NOT NULL,        -- QUÉ revisión de él
  content_sha256    TEXT NOT NULL,        -- y los BYTES exactos
  decided_at TEXT);

-- CONTEXTO. §11 exige `stale`, refresco, procedencia y poder RECONSTRUIR lo que
-- un agente recibió. Nada de eso es posible sin persistirlo: sin esta tabla, «el
-- pack estaba rancio» es una afirmación que nadie puede comprobar después, y la
-- invalidación no tiene sobre qué actuar. Un pack que sólo existió en memoria
-- convierte cualquier post-mortem en una reconstrucción de memoria.
CREATE TABLE context_packs (
  id TEXT PRIMARY KEY,
  job_id TEXT NOT NULL REFERENCES jobs(id),
  pack_version INTEGER NOT NULL,
  content_sha256 TEXT NOT NULL,          -- los bytes que el agente recibió
  sources TEXT NOT NULL,                 -- JSON: [{ref, sha256}] — procedencia
  token_count INTEGER NOT NULL,          -- contra el presupuesto de ≤12k
  generated_at TEXT NOT NULL,
  UNIQUE (job_id, pack_version),
  UNIQUE (job_id, id));                  -- soporta la FK compuesta desde `jobs`

-- APPEND-ONLY DE VERDAD: la fila NO SE TOCA NUNCA. Mi versión anterior dejaba
-- `invalidated_at` en esta tabla y un trigger que sólo abortaba si la fila ya
-- estaba invalidada o si cambiaba `content_sha256` — o sea que permitía editar
-- `sources`, `token_count` y `generated_at`, y permitía la PRIMERA invalidación
-- por UPDATE. Un append-only con una excepción no es un append-only: es una
-- tabla mutable con una convención, y la convención se rompe sola.
CREATE TRIGGER context_packs_inmutable BEFORE UPDATE ON context_packs
  BEGIN SELECT RAISE(ABORT, 'context_packs es append-only: crea otra versión'); END;
CREATE TRIGGER context_packs_no_delete BEFORE DELETE ON context_packs
  BEGIN SELECT RAISE(ABORT, 'context_packs es append-only'); END;

-- La invalidación pasa a ser un HECHO INSERTADO, no un campo mutado. Vigente =
-- «no tiene fila aquí». Y así la invalidación conserva su propia procedencia:
-- cuándo y por qué evento dejó de valer, sin sobrescribir nada.
CREATE TABLE context_pack_invalidations (
  pack_id TEXT PRIMARY KEY REFERENCES context_packs(id),
  invalidated_at TEXT NOT NULL,
  invalidated_by_event TEXT NOT NULL REFERENCES events(event_id),
  reason TEXT NOT NULL);                 -- QUÉ dependencia cambió, en claro
CREATE TRIGGER cpi_no_update BEFORE UPDATE ON context_pack_invalidations
  BEGIN SELECT RAISE(ABORT, 'la invalidación es un hecho, no se edita'); END;
-- Y TAMPOCO SE BORRA: con `stale(pack)` definido como «existe fila aquí», un
-- DELETE resucita un pack invalidado sin crear versión nueva — el sistema vuelve
-- a servir contexto que se declaró caduco, y se pierde el rastro del evento que
-- lo invalidó. Prohibir el UPDATE y dejar el DELETE es cerrar una puerta y abrir
-- la de al lado.
CREATE TRIGGER cpi_no_delete BEFORE DELETE ON context_pack_invalidations
  BEGIN SELECT RAISE(ABORT, 'la invalidación no se borra: crea otra versión del pack'); END;

CREATE TABLE consults (
  id TEXT PRIMARY KEY, job_id TEXT NOT NULL,
  from_principal TEXT NOT NULL, to_principal TEXT NOT NULL,
  question TEXT NOT NULL, answer TEXT,
  ttl_at TEXT NOT NULL, answered_at TEXT, closed INTEGER NOT NULL DEFAULT 0);

-- AUDIT
CREATE TABLE events (
  event_id TEXT PRIMARY KEY, event_type TEXT NOT NULL, occurred_at TEXT NOT NULL,
  actor_principal TEXT, project_id TEXT, job_id TEXT,
  correlation_id TEXT, causation_id TEXT,
  idempotency_key TEXT NOT NULL,
  payload TEXT);

-- IDEMPOTENCIA. Guardar la clave NO es implementarla, y un índice UNIQUE tampoco:
-- con sólo UNIQUE, un reintento —que es la situación NORMAL, no la rara— no
-- devuelve el resultado de la primera vez, sino que choca contra una restricción.
-- El cliente recibe un error donde debería recibir su respuesta, y no tiene forma
-- de distinguir «ya se hizo» de «falló». Eso no es idempotente: es duplicado
-- prohibido, que es otra cosa.
--
-- Faltaban tres piezas: QUIÉN ejecutó, el HASH de la petición, y la RESPUESTA.
CREATE TABLE idempotency (
  principal_id    TEXT NOT NULL,        -- la clave de un principal no colisiona con la de otro
  operation       TEXT NOT NULL,        -- ámbito: la misma key en dos operaciones son dos cosas
  idempotency_key TEXT NOT NULL,
  request_sha256  TEXT NOT NULL,        -- sin esto no se puede detectar la REUTILIZACIÓN
  response_status  INTEGER NOT NULL,    -- lo que se devolvió
  response_payload TEXT NOT NULL,       -- para poder devolverlo OTRA VEZ, idéntico
  created_at TEXT NOT NULL,
  PRIMARY KEY (principal_id, operation, idempotency_key));

CREATE TABLE outbox (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  event_id TEXT NOT NULL UNIQUE REFERENCES events(event_id),
  delivered_at TEXT);
```

**Semántica, que es donde vive el contrato:**

```
misma key + mismo request_sha256      → se devuelve la RESPUESTA PERSISTIDA
                                         (mismo status, mismo cuerpo; no se re-ejecuta)

misma key + request_sha256 DISTINTO   → 409 IDEMPOTENCY_KEY_REUSED
                                         (el cliente reusó una clave para otra petición:
                                          devolverle la respuesta vieja sería mentirle,
                                          y ejecutar sería romper su propia garantía)

primera vez                           → estado + event + outbox + fila de idempotencia
                                         en UNA transacción
```

**Y la concurrencia se serializa con `BEGIN IMMEDIATE`, no con una fila «en curso».** El contrato de arriba, leído como «mira si existe; si no, ejecuta», tiene una carrera que se abre justo en el caso que la idempotencia existe para cubrir —dos reintentos simultáneos, que es lo que pasa cuando un cliente reintenta por timeout mientras la primera petición sigue viva—: **los dos** ven que no hay fila, **los dos** ejecutan, y sólo al final uno choca contra la PK. La mutación ya se hizo dos veces y el error llega tarde.

```
BEGIN IMMEDIATE                       -- el write lock, desde el principio

buscar (principal_id, operation, idempotency_key)

  existe + mismo request_sha256   → devolver la respuesta persistida
                                    → NO ejecutar

  existe + hash distinto          → 409 IDEMPOTENCY_KEY_REUSED

  no existe                       → ejecutar la mutación
                                    → event
                                    → outbox
                                    → fila de idempotencia con la respuesta
COMMIT
```

**`BEGIN IMMEDIATE` no espera por sí solo.** Sin `busy_timeout`, SQLite devuelve `SQLITE_BUSY` («database is locked») **de inmediato** en vez de bloquear — así que «el segundo request espera» es falso por defecto, y lo que ocurre es que el reintento del cliente recibe un error de base de datos donde esperaba su respuesta. El contrato de conexión lo fija:

```
PRAGMA busy_timeout = 5000;          -- ms: el cerrojo se ESPERA, no se rebota
reintentos: 3, backoff exponencial con jitter (50 · 2^n ms)
agotados  → 503 + Retry-After         -- «no pude serializar», NO 500
```

`503` y no `500` porque no es un fallo: es contención, el cliente puede reintentar y la operación sigue siendo idempotente. Un `500` empuja al cliente a rendirse o a reintentar sin clave, que es peor.

Con eso sí: el segundo request queda **esperando el write lock**; cuando entra, la primera ya ha commiteado y encuentra la respuesta hecha. No hace falta inventar una fila `PENDING` en v1: el cerrojo ya da la exclusión, y un estado «en curso» añadiría un modo de fallo propio —quién lo limpia si el proceso muere— a cambio de nada que el cerrojo no dé ya.

**Falsador F-I3 (concurrente, obligatorio)** — **20** peticiones simultáneas con la misma clave y el mismo cuerpo ⇒ **una** mutación, **un** event, **una** fila de outbox y **20 respuestas idénticas**, y **ninguna** de las 20 es un `SQLITE_BUSY`. Sin `busy_timeout` este falsador se pone rojo por ahí antes que por la idempotencia, que es justamente lo que hace falta ver. Es el único de los tres que se pone rojo con la versión «comprobar y luego ejecutar»: F-I1 y F-I2 pasan secuencialmente con la carrera abierta, y por eso dos falsadores en verde no bastaban.

**Falsador F-I1** — enviar dos veces la misma mutación con la misma clave y el mismo cuerpo: la segunda devuelve **el mismo status y el mismo payload** que la primera, y `events` no crece. Si la segunda devuelve `409` o un error de restricción, hay UNIQUE pero no idempotencia.

**Falsador F-I2** — misma clave, cuerpo distinto ⇒ `409 IDEMPOTENCY_KEY_REUSED`, y **no** se ejecuta la segunda.

**`PRAGMA foreign_keys = ON` en CADA conexión, y es parte del contrato de inicialización.** SQLite las trae **desactivadas por defecto**: sin este pragma, todos los `REFERENCES` de arriba son documentación. Un `jobs.context_pack_id` apuntando a un pack inexistente se inserta sin protestar, y la referencia que hace verificable «qué contexto recibió este job» deja de verificar nada. No es una opción de despliegue — una conexión sin el pragma sirve un modelo de datos distinto del que esta sección describe.

**Falsador F-C1** — invalidar un pack y luego intentar `DELETE` sobre su fila de invalidación ⇒ la base lo rechaza, y `stale(pack)` sigue siendo cierto.

**Falsador F-DB1** — insertar un `jobs.context_pack_id` que no existe en `context_packs` ⇒ la base lo rechaza. Con el pragma apagado, esa inserción pasa: el falsador mide el pragma tanto como la FK.

**Sin event-sourcing completo en v1:** `jobs` es el estado actual, `events` es cómo se llegó. El log sirve para auditoría, depuración, analítica y provenance, no para reconstruir el sistema.

**`outbox.event_id` es UNIQUE, y eso garantiza MENOS de lo que parece.** Garantiza **una sola fila de outbox por evento** — sin ello, un reintento del productor encolaba el mismo evento dos veces y la notificación salía duplicada aunque la mutación fuera idempotente. Lo que **NO** garantiza es entrega *exactly-once* al exterior: entre marcar `delivered_at` y que el destinatario acuse hay una ventana que ninguna base cierra. La entrega externa es **at-least-once** por diseño, y **el consumidor deduplica por `event_id`**. Decirlo aquí es parte del contrato: un consumidor que asuma exactly-once construirá sobre una garantía que este sistema no da.

**Outbox transaccional:** toda mutación que requiera notificación externa escribe estado + evento + outbox **en la misma transacción**. Nunca «actualizo y luego envío».

---

# §16 · Superficie de API y CLI

### 16.1 · API

```
GET  /whoami                     → principal resuelto del token (nunca del payload)
GET  /organigrama                → { org_revision, content_sha256, loaded_at, stale }
GET  /organigrama/principals/{id}
GET  /org                        → MISMO handler que /organigrama (alias, deprecado)

GET  /work/next                  POST /jobs/{id}/claim      POST /jobs/{id}/start
POST /jobs/{id}/heartbeat        POST /jobs/{id}/block      POST /jobs/{id}/unblock
POST /jobs/{id}/submit           POST /jobs/{id}/cancel
POST /jobs/{id}/delegate         GET  /jobs/{id}/children
GET  /jobs/{id}/context          POST /jobs/{id}/context/refresh

POST /consults                   GET  /consults/mine        POST /consults/{id}/answer
POST /decisions                  GET  /decisions/mine       POST /decisions/{id}/resolve
GET  /reviews/next               POST /reviews/{id}/{approve|changes|block}
```

**Identidad:** el `actor` **nunca** se acepta del payload. Se deriva de la autenticación. Toda mutación acepta `idempotency_key`.

### 16.2 · CLI

`llmi work {next|claim|show|context|start|block|submit}` · `llmi delegate` · `llmi consult` · `llmi decision request` · `llmi review {next|approve|changes}` · `llmi org {show|compile|diff}`.

**Interfaz máquina:** con `--json` o sin TTY, la salida es **JSON limpio**. Un LLM no debe parsear una interfaz humana con regex. *(El contrato de códigos de salida ya está fijado: `0` ok —ayuda incluida— · `1` hallazgo · `2` mal uso, por stderr · `3` servicio ausente · `4` identidad no resuelta.)*

### 16.3 · `doctor`: integridad organizativa

Sustituye a «16 roles huérfanos», que mezcla riesgo real con deuda de nomenclatura:

```
ORGANIZATION INTEGRITY

  16 authenticated principals lack governance

    ROLE      3      SERVICE   5      ALIAS     4
    GROUP     2      LEGACY    2

  CRITICAL   3 principals can_claim_jobs=true without Role Contract
  WARNING    5 services have no accountable human
  INFO       4 aliases should collapse to canonical principals
```

Y los antipatrones operativos: job sin owner · job sin criterios de aceptación · lease rancio · ciclo de dependencias · bloqueado demasiado tiempo · delegación excesiva · ping-pong de review · mensajes sin referencia a job/decision · intentos de broadcast de IC · presupuesto desbocado · **`NO_POLICY_MATCH` acumulados** · context pack sobredimensionado · escalado sin resolver.

---

> **Nota de reconciliación — `/org` vs `/organigrama`.** Una versión anterior de esta spec definía `GET /org` en §16 y a la vez decía en §17 que se ampliaba `GET /organigrama`. Son rutas distintas: se habrían implementado las dos, sirviendo el mismo dato desde dos sitios, que es la deriva de proyecciones que §4 prohíbe — cometida en la propia superficie de API.
>
> **Canónica: `/organigrama`.** No por gusto: ya está en producción, ya la consumen los vigías de la flota, y sus falsadores de frescura (F-O1, F-O1b) están escritos contra ella. Mover la ruta canónica obligaría a reescribir consumidores vivos y falsadores a cambio de un nombre más corto.
>
> `/org` queda como **alias registrado sobre el MISMO handler**, no como segunda implementación ni como redirección. Un alias que reimplementa es otra proyección; y un `308` tampoco sirve como contrato, porque **hay clientes máquina que no siguen redirecciones** —`curl` sin `-L`, muchos wrappers de HTTP con redirects desactivados por defecto— y para ésos «alias» se convertiría en «404 con otro nombre». Los dos paths resuelven al mismo código y devuelven el mismo cuerpo; `/org` va marcado `Deprecation` en la respuesta. Se retira cuando ningún consumidor lo use, medido en el log de acceso — no en una fecha elegida a ojo.

---

# §17 · Qué se reutiliza y qué se deprecia

Verificado contra el código vivo. **Nada de esto se reconstruye.**

| Ya existe | Estado |
|---|---|
| Identidad fail-closed (`422` a nombre fuera de censo) | **Se conserva.** Es el precedente del modelo de §3. |
| Carriles (`carriles.tsv`) como SoT de proyecto | **Se conserva.** `project_id` se deriva de ahí. |
| Ledger append-only + `llmi verify` (integridad del canon) | **Se conserva** como audit plane. |
| `GET /organigrama` | **Se amplía** con `org_revision`, `sha256`, `stale` (§4.3). **Es la ruta canónica**, ver nota. |
| `llmi stat` detector de deriva de montaje | **Se reutiliza el patrón** para el gate de deriva (§4.2). |
| `llmi doctor` ①②③⑤ | **Se amplía** con §16.3. |
| Cursores e inbox dirigido | **Se conserva** para el plano de comunicación; deja de ser el plano de trabajo. |
| `llmi post` validando destinatario + tipo + sello | **Se endurece**: pasa a ser el único camino con consecuencia operacional (§8.3). |
| `--json` en `stat` | **Se generaliza** a toda la CLI (§16.2). |

| A construir | Dueño |
|---|---|
| `principals` + regla de admisión | control-plane |
| Compilador de organización + gate de deriva | control-plane |
| Atestación | control-plane |
| Las cuatro tablas de autoridad + Policy Engine | control-plane |
| Gate Engine con `NO_POLICY_MATCH` | control-plane |
| Registro de kinds + preservación de `raw_type` | llminbox |
| ⚠️ **Trampa verificada**: `raw_tipo` es una columna nueva en `entries`, y llminbox **borra `cursors` ante cualquier cambio de huella de esquema** (`servicio.py:1755`) — desplegarlo por la vía obvia resetearía la posición de lectura de los 20 agentes y sus bandejas aparecerían llenas. Vía correcta y ya existente: `COLUMNAS_ANADIDAS` + `ALTER TABLE`, que no toca la huella. | llminbox |
| Jobs, leases, fencing, scheduler, watchdog | control-plane |
| Context Builder | control-plane |
| Event log + outbox | control-plane |
| Role Contracts, comms-policy, system prompts | harness |

**Fuera de alcance de v1** (con dueño, para que nadie los construya por su cuenta): Model Router y multi-modelo (aparcado — todo en Opus/suscripción, decisión del operador) · UI · Knowledge Plane / Canon v2 (adjudica `wiki-vault`) · estrategia de test (`qa`) y plataforma de calidad (`sdet`) · apertura de plazas y colocación en el organigrama (operador).

---

# §18 · Fases

El orden conceptual manda, y cada fase tiene su falsador **declarado antes** de recoger evidencia. **Big-bang prohibido**: si una fase no mueve su métrica, se para ahí.

| Fase | Qué | Falsador |
|---|---|---|
| **0-A** | ✅ **HECHA (2026-08-18).** Read-path medido sobre 46.423 transcripts / 27,7 GB. Resultado en §2. | Falsador satisfecho: los bytes se atribuyeron por `tool_use_id`, sin estimación. **«La ballena es el read-path» quedó falsada** (11,8 % de la ingesta; 1,8 KB por llamada). Hallazgo que la sustituye: **50,7 % de relecturas**. |
| **0-B** | **Comunicación.** Taxonomía arreglada (§8) y luego: canonical / `raw_type_unknown` / untyped · tamaño · destinatario · correlación con job. Incluye `amend_rate`. | Comunicación y ejecución deben ser separables por fuente. Si no lo son, el KPI es humo y no se reporta. |
| **1** | **Principals + Org SoT + compilador + gate de deriva + atestación.** | F-P1/F-P2 · F-O1 · F-A1. Y el control negativo: los 16 huérfanos deben salir clasificados **antes**, o el «después» no dice nada. |
| **2** | **Autoridad + Policy Engine + Gate Engine.** Aquí las reglas del harness dejan de ser advisory. | F-6.1 · F-6.2 · F-6.3 · F-7.1 · F-7.2 |
| **3** | **JOB + Context Pack + lease atómico con fencing** en un proyecto piloto (`64bis`, roles `be` · `db-migrations` · `sdet`). | F-10.1 · F-10.2 · F-10.3 · F-11.1. Y el North Star del piloto frente a la línea base de Fase 0: si no mueve, el modelo JOB no está pagando y no se expande. |
| **4** | **Heartbeat de runtime + watchdog + requeue.** Se eliminan los heartbeats escritos por LLM. | Matar el proceso poseedor ⇒ requeue sin humano. |
| **5** | **Delegación + CONSULT acotado + escalation + EM `active`.** | F-12.1 · F-13.1 |
| **6** | **Expansión a los 16 roles.** | La integridad organizativa de §16.3 debe quedar en cero CRITICAL. |
| **7** | **Inbox exception-only + Canon v2.** | No se depreca ningún tipo cuya clase no sea medible (bloqueado por 0-B). |

**Fase 0 primero demuestra dónde está realmente el coste.** Es el juez de todo lo demás.

---

# §19 · Invariantes de seguridad

1. Un principal no puede asumir la identidad de otro; el actor se deriva de la autenticación, nunca del payload.
2. Un principal no lee jobs de otro proyecto sin permiso.
3. Un principal no modifica un Job que no posee.
4. Un lease no se comparte; `lease_generation` vieja no muta estado.
5. Nadie aprueba fuera de su autoridad; bloquear ≠ aceptar riesgo.
6. Los gates requeridos no se omiten; `NO_POLICY_MATCH` es fail-closed.
7. Los prompts no amplían permisos. **El contenido externo es untrusted input**: una instrucción encontrada en un documento, email o página web nunca autoriza una acción.
8. Los secretos van por referencia (`secret://…`) y se resuelven sólo si rol, job y proyecto están autorizados.
9. Toda mutación tiene actor y evento.
10. Toda aprobación está atada a un `content_sha256`.

---

# §20 · Definition of Done de v1

v1 está hecho cuando este escenario corre **sin comunicación manual entre workers**:

```
operador deja una intención
  → CPO produce contrato de producto
  → CTO produce contrato técnico
  → EM descompone
  → scheduler crea trabajo READY
  → be · fe · db-migrations · sdet entregan artefactos
  → los gates que la policy seleccionó se satisfacen
  → DONE
  → canon
```

Y simultáneamente:

- **0** mensajes rutinarios al operador; sólo decisiones reales y escalados críticos.
- **0** principals con `can_claim_jobs=true` sin contrato organizativo.
- **0** jobs `DONE` sin artefacto o con un gate requerido pendiente.
- **0** heartbeats escritos por un LLM.
- **0** aprobaciones sin `content_sha256`.
- **100 %** de los jobs `DONE` reconstruibles: por qué existieron, quién los pidió, quién los poseyó, qué contexto recibieron, qué decisiones los influyeron, qué produjeron, quién los revisó, qué gates pasaron y cuánto costaron.

---

*Fin v0.3. Los números de §1 y §2 son reproducibles contra el sistema vivo; los de v0.2 §C quedan sustituidos. Las hipótesis abiertas de §2 se cierran en Fase 0 y hasta entonces no se citan como establecidas.*
