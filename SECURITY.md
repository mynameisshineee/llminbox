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
- **`flock` only protects writers that take it.** An agent appending with `>>` does
  not. Measured: an entry written across several shell commands *will* interleave
  with another agent's — 8 of 16 bodies landed under the wrong header in a test with
  realistic delays. Write an entry in one command, or use the validating writer.

## Reporting

Open a private security advisory on the repository, or email the address in the
commit metadata. Please include what you did, what you expected, and what happened.
We would rather receive a report that turns out to be a non-issue than not receive one.
