# Security

## What this software touches

`llminbox` reads the markdown files where your agents coordinate, indexes them, and
serves that index over HTTP on loopback. Two things follow from that:

- **The content it serves is your coordination record.** For most teams that is
  operational detail — decisions, findings, infrastructure notes. Treat access to
  the port as equivalent to read access to those files.
- **It is written by LLMs and read by LLMs.** Entry bodies are untrusted text. The
  API marks them (`X-Llminbox-Untrusted`) and the inbox prefixes them with a notice,
  but nothing can stop a downstream agent from following instructions it reads. If
  you pipe `llmi inbox` into another agent's context, that agent must treat the
  content as data, never as instructions.

## What is enforced

| | |
|---|---|
| Auth | Every endpoint that returns data requires `X-Llminbox-Token`. Without a token the service starts **mute** and returns 503 rather than serving. |
| Exposure | Binds to `127.0.0.1` only. |
| Writes | Ledgers are mounted read-only by default. The validating writer (`POST /append`) is opt-in and experimental. |
| Schema | `/docs` and `/openapi.json` are disabled — they leaked the API map, including ledger names, without a token. |

## What is NOT enforced, and you should know

- **Loopback is not isolation on Docker Desktop for macOS.** Verified: a container on
  an unrelated network reached the published port through `host.docker.internal`.
  That is why the token exists and why it is mandatory, not optional.
- **The token is visible in `docker inspect` and in the container environment.**
  Anyone who can run Docker commands on the host can read it.
- **`actor` is self-declared.** Nothing verifies that an agent writing as `alice-backend`
  is that agent. `roster.json` has an empty `clave` field per agent — that is the
  reserved place for signatures if you ever need the ledger to serve as evidence
  rather than coordination. It is not implemented.
- **Lanes are not a boundary. Any caller with the token reads every ledger.**
  `--carril` / `BIK_CARRIL` scope *consumption* (whose cursor advances), never
  *access*. Measured on a real 12-ledger, ~69-agent installation on 2026-08-22 —
  same token, three requests for another lane's ledger:

  ```
  X-Llminbox-Carril: <own lane>    → 200
  X-Llminbox-Carril: <other lane>  → 200
  no header at all                 → 200
  ```

  `/entries?ledger=` does not consult the header at all. There is no request that
  returns 403 for a lane you are not in, because that check does not exist. If you
  need a lane to be a wall, this is not the tool — and adding the header to a
  request does not make it one.

- **`X-Llminbox-Carril` is a scoping hint, not an identity.** The caller fills it
  in. It prevents *accidents* — draining the wrong lane's cursor — which is worth
  having, but it is self-declared like `actor` and nothing verifies it.

- **One shared token means the service cannot tell its callers apart.** There is a
  single `LLMINBOX_TOKEN`; every agent presents the same secret, so "which agent is
  asking" is not a question the service can answer. Per-agent authorization is
  therefore not something you can configure — it is absent by design at this stage.

  On the reference installation the token file is `0600`, which sounds like
  isolation and is not: **all agent sessions run as the same OS user**, so the mode
  bits separate them from other accounts on the machine, not from each other.

- **Before treating any of this as a vulnerability, measure the alternative path.**
  On that same installation, every ledger is `-rw-r--r--` and owned by the user the
  agents run as, so a process that can call the API can also `cat` the file. The
  service exposes nothing the caller could not already read, and the honest
  conclusion is *"no isolation between agents at the host level"*, not *"llminbox
  leaks"*.

  **That conclusion is about that deployment, not about this software.** If you run
  agents in containers, under separate users, or with per-agent mounts — so that a
  caller can reach the port but *cannot* open another lane's file — then the shared
  token makes this service the bridge between those domains, and that is a real
  finding. Re-measure both halves before concluding either way.

- **`flock` only protects writers that take it.** An agent appending with `>>` does
  not. Measured: an entry written across several shell commands *will* interleave
  with another agent's — 8 of 16 bodies landed under the wrong header in a test with
  realistic delays. Write an entry in one command, or use the validating writer.

## Reporting

Open a private security advisory on the repository, or email the address in the
commit metadata. Please include what you did, what you expected, and what happened.
We would rather receive a report that turns out to be a non-issue than not receive one.
