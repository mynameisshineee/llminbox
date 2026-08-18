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

En sentido inverso, uno: `engineering-manager` existe en el organigrama y **no tiene identidad** en llminbox. Hoy `/inbox/engineering-manager` → 422. *Se puede crear un rol que no puede recibir trabajo.*

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

**Veredicto: «la ballena es el read-path» queda FALSADA en su forma literal.** La lectura media son 1,8 KB — los agentes hacen `tail`, no `cat`; nadie pasta 357k líneas. Contra el denominador honesto —toda la ingesta por `tool_result`, que sufre la misma amplificación por caché que el numerador— el ledger es el **11,8 %**; el otro 88 % es trabajar con código. El 0,35 % contra `cache_creation` se da como **cota inferior**: un `tool_result` permanece en contexto el resto de la sesión y se re-lee en cada turno, así que el coste real de una lectura no son 444 tokens sino 444 × turnos restantes. El número defendible es el 11,8 %.

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
| `role` | sí | **sí** | **sí, obligatorio** | sí |
| `agent` | sí | **sí** | vía su `role` | vía su `role` |
| `service` | sí | no | **no** | **sí, obligatorio** |
| `alias` | hereda | hereda | hereda | hereda |
| `group` | sí | no | no | sí |
| `project` | sí | no | no | sí |
| `legacy` | sí | no | no | opcional |

Con esto desaparece la anomalía semántica: un `group` recibe mensajes sin tener jefe; un `project` es destino lógico sin reclamar trabajo; un `service` opera herramientas sin formar parte del organigrama; un `alias` no tiene autoridad propia, hereda identidad; un `agent` ejecuta un `role`.

### Regla de admisión al work plane — **invariante duro**

```
principal.type ∈ {role, agent}
        ∧ lifecycle = active
        ∧ contrato organizativo válido (§6)
        ⇒ puede entrar al work plane

en cualquier otro caso  ⇒  409 not_a_work_principal  + evento
```

**Falsador F-P1** — un principal `type=service` intenta `POST /jobs/{id}/claim` ⇒ `409`, evento `principal.claim_denied`, y el job permanece `READY`. Si el claim prospera, el modelo de principal no está enforzado y todo lo que se apoya en él (§6, §7, §9) es decorativo.

**Falsador F-P2 (control negativo)** — un principal `type=role` con contrato válido y `lifecycle=active` **sí** reclama. Sin este control, F-P1 pasaría con un sistema que deniega a todo el mundo.

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
```

Esto es obligatorio: **SoT + generación sin detector de deriva produce N copias rancias**, que es exactamente el estado actual (`roster.json` + 7 `.bak` + `roster.discovered.json` + `roles-por-alias.json` + `ORGANIGRAMA.md`).

Precedente reutilizable en el repo: `llmi stat` ya tiene un detector de deriva de montaje. Mismo patrón, otro objeto.

### 4.3 · Carga y frescura en el servicio

El fallo de §1.4 tiene tres causas y las tres se cierran:

1. **Bind-mount de fichero único** → se monta el **directorio**, nunca el fichero. Un rename en el host deja de romper el mount.
2. **Carga en tiempo de import** (`lp.JERARQUIA` es un global) → se recarga por mtime+hash, o se recarga bajo demanda con caché corta.
3. **El aviso sólo cubre "ilegible", no "rancio"** → `/organigrama` devuelve siempre `org_revision`, `content_sha256` y `loaded_at`; si el hash en disco difiere del cargado, `stale: true` **en la respuesta**.

**Falsador F-O1** — modificar la fuente en el host y volver a pedir `/organigrama` sin reiniciar ⇒ o refleja el cambio, o devuelve `stale: true`. Servir contenido viejo con `stale: false` es el fallo que hoy ocurre y que este falsador prohíbe.

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

Un compilado cuya fuente no tiene atestación vigente **no se despliega**: el control plane arranca con la última revisión atestada y avisa; nunca con contenido sin aprobar. Esto sustituye a `gate_delegado_por: ALBERT` como mecanismo — la delegación de gate pasa a ser **una concesión permanente registrada una vez** (§6.4), no una dependencia del operador en cada aprobación.

**Falsador F-A1** — editar un byte de la fuente y desplegar sin re-atestar ⇒ el arranque rechaza el compilado. Si arranca, la atestación es decorativa.

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
{ "matched_policy": "POL-127", "gates": [] }
{ "matched_policy": "POL-921", "gates": ["qa", "security"] }
```

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

**Sólo el servidor persiste transiciones.** El agente solicita; el servidor comprueba lease válido · actor autorizado · artefacto presente y del tipo esperado · presupuesto · estado origen legal. Un Job sin criterios de aceptación no pasa a `READY` salvo tipos explícitamente exploratorios.

---

# §10 · Lease atómico y fencing — desde el primer claim

**No se introduce Postgres todavía.** Para ~16 agentes, una instalación y pocos claims por segundo, SQLite en WAL con transacción corta ejecuta el piloto perfectamente. Postgres entra cuando haya varias réplicas, multi-host, o contención medible.

**El lease es atómico y con fencing desde el día uno.** Un `claim` sin exclusión es una semántica provisional que después hay que romper.

```sql
BEGIN IMMEDIATE;

SELECT id FROM jobs
 WHERE status = 'READY'
   AND project_id = :project
   AND owner_role = :role
   AND id NOT IN (SELECT job_id FROM job_dependencies WHERE satisfied = 0)
 ORDER BY priority DESC, created_at ASC
 LIMIT 1;

UPDATE jobs
   SET status = 'CLAIMED',
       lease_generation = lease_generation + 1
 WHERE id = :job AND status = 'READY';     -- guardia: 0 filas ⇒ otro ganó

INSERT INTO job_leases (job_id, principal_id, lease_generation, claimed_at, expires_at)
VALUES (:job, :principal, :gen, :now, :now + :ttl);

COMMIT;
```

El token que se entrega al worker contiene `job_id · principal_id · lease_generation`.

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

**Invalidación:** si una dependencia crítica cambia tras generar el pack, `stale = true`; refresco obligatorio antes de acción irreversible.

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
  org_revision INTEGER NOT NULL
);

CREATE TABLE org_relations (
  principal_id TEXT NOT NULL,
  reports_to TEXT, delivery_manager TEXT,
  technical_authority TEXT, product_authority TEXT,
  org_revision INTEGER NOT NULL,
  PRIMARY KEY (principal_id, org_revision)
);

CREATE TABLE org_attestations (
  org_revision INTEGER PRIMARY KEY,
  content_sha256 TEXT NOT NULL,
  approved_by TEXT NOT NULL, approved_at TEXT NOT NULL,
  scope TEXT NOT NULL
);

-- AUTORIDAD (cuatro conceptos, cuatro tablas — §6)
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
  matched_policy TEXT, required_gates TEXT,             -- los fija el Gate Engine, §7
  budget TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);

CREATE TABLE job_dependencies (
  job_id TEXT, depends_on TEXT, satisfied INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (job_id, depends_on));

CREATE TABLE job_leases (
  job_id TEXT NOT NULL, principal_id TEXT NOT NULL,
  lease_generation INTEGER NOT NULL,
  claimed_at TEXT NOT NULL, expires_at TEXT NOT NULL, released_at TEXT,
  PRIMARY KEY (job_id, lease_generation));

-- GOBERNANZA
CREATE TABLE reviews (
  id TEXT PRIMARY KEY, job_id TEXT NOT NULL, gate TEXT NOT NULL,
  reviewer_principal TEXT, verdict TEXT
    CHECK (verdict IN ('APPROVED','CHANGES_REQUESTED','BLOCKED')),
  decided_at TEXT);

CREATE TABLE consults (
  id TEXT PRIMARY KEY, job_id TEXT NOT NULL,
  from_principal TEXT NOT NULL, to_principal TEXT NOT NULL,
  question TEXT NOT NULL, answer TEXT,
  ttl_at TEXT NOT NULL, answered_at TEXT, closed INTEGER NOT NULL DEFAULT 0);

-- AUDIT
CREATE TABLE events (
  event_id TEXT PRIMARY KEY, event_type TEXT NOT NULL, occurred_at TEXT NOT NULL,
  actor_principal TEXT, project_id TEXT, job_id TEXT,
  correlation_id TEXT, causation_id TEXT, idempotency_key TEXT,
  payload TEXT);

CREATE TABLE outbox (
  id INTEGER PRIMARY KEY AUTOINCREMENT, event_id TEXT NOT NULL,
  delivered_at TEXT);
```

**Sin event-sourcing completo en v1:** `jobs` es el estado actual, `events` es cómo se llegó. El log sirve para auditoría, depuración, analítica y provenance, no para reconstruir el sistema.

**Outbox transaccional:** toda mutación que requiera notificación externa escribe estado + evento + outbox **en la misma transacción**. Nunca «actualizo y luego envío».

---

# §16 · Superficie de API y CLI

### 16.1 · API

```
GET  /whoami                     → principal resuelto del token (nunca del payload)
GET  /org                        → { org_revision, content_sha256, loaded_at, stale }
GET  /org/principals/{id}

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

# §17 · Qué se reutiliza y qué se deprecia

Verificado contra el código vivo. **Nada de esto se reconstruye.**

| Ya existe | Estado |
|---|---|
| Identidad fail-closed (`422` a nombre fuera de censo) | **Se conserva.** Es el precedente del modelo de §3. |
| Carriles (`carriles.tsv`) como SoT de proyecto | **Se conserva.** `project_id` se deriva de ahí. |
| Ledger append-only + `llmi verify` (integridad del canon) | **Se conserva** como audit plane. |
| `GET /organigrama` | **Se amplía** con `org_revision`, `sha256`, `stale` (§4.3). |
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
