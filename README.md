# llminbox

A queryable index over markdown coordination logs for AI agent fleets — with
a per-agent inbox and cursor, so "what's new for me" doesn't mean re-reading
the last N lines and filtering by eye.

> Markdown stays the source of truth. This is a **derived**, disposable index
> and an optional validating writer. If it dies, nobody is blocked — that's
> tested (killed the service outright, confirmed `tail`/`grep`/writing still
> worked and it came back in 2s — falsifier T5, full table in the design
> notes), not just promised.

**Who this is for:** if your agents already coordinate by appending
timestamped notes to a shared `.md` file and catching up with `tail`/`grep`,
this replaces that read path with an indexed, per-agent inbox — without
changing how anything writes.

## Quick start

Requires Docker and Docker Compose. Nothing else — no accounts, no cloud, no telemetry.

```bash
git clone <this-repo-url> llminbox && cd llminbox
./llmi init      # finds your ledgers, writes the config, generates a token
./llmi up        # builds and starts the container
./llmi inbox <your-agent-name>
```

`init` scans your working directory, your git repo and your home directory for
markdown files that look like ledgers, then **shows you what it found and asks
before mounting anything**. Say no to whatever isn't yours: a ledger belonging to
a client or to another team should not be indexed here — mounting it, even
read-only, exposes its contents to anything that reaches the port. Add permanent
exclusions to `.llminbox-excluir` (one pattern per line, git-ignored).

Then open **<http://127.0.0.1:8077/ui>** and paste the token from
`~/.llminbox.token`.

### No ledger of your own yet?

`init` offers to write a demo one. Take it — two or three entries won't produce
the "aha": the inbox only visibly beats `tail` once there is enough traffic
addressed to more than one agent. With the demo in place, compare for yourself:

```bash
./llmi inbox alice-backend     # what's addressed to her, since she last looked
tail -500 <the-same-file>         # the same window, by eye
```

That comparison is the whole product. If it doesn't convince you, this tool
probably isn't for you yet — see [the honest threshold](#when-does-this-actually-help-the-honest-threshold).

## The problem, measured

Numbers below are from this project's own production deployment — six
ledgers, 37,260 entries total, measured 2026-07-27 — not a synthetic
benchmark. Internal project names are omitted; the shape and the numbers are
real.

- The largest ledger in that deployment: 54 MB / 23,491 entries / 13.5M
  tokens ≈ **68 context windows** (at a 200K-token window).
- The fleet reads it with `tail` (13,169 invocations logged) and `grep`
  (8,733), and writes with raw `>>` (5,276).
- A `tail -500` costs **27,983 tokens**. In 5,580 of 6,432 consecutive
  re-reads within the same session, entries relevant to that session had
  landed outside that window.
- `GET /inbox/<agent>` answers "what's new for me" in **2,778 tokens** — about
  10x less — because it returns entries addressed to that agent, not the last
  500 lines of everything.

## Related work — and where the gap still is

Coordinating a fleet of AI agents by writing to a shared markdown file is not
a new idea, and this project doesn't claim to have invented it. By mid-2026 at
least four other projects had independently converged on close variants of
the same primitive: **agent-relay** (a shared ledger file between Claude Code
and Codex CLI), **LedgerSync** (Metacog-AI's append-only `ledger.jsonl`),
**tick-md** (Purple Horizons' markdown-based agent coordination), and
**sean2077/agent-ledger**. tick-md states the underlying bet plainly: *"every
LLM understands Markdown without custom parsers or API integrations"* — that's
now table stakes for this category, not a differentiator.

We looked closely at two of the four. Neither solves reading the log back at
scale:

- **tick-md** has no cursor and no read-state; its reading model is "open the
  whole file." Its own roadmap lists "better support for large-scale agent
  swarms" as still in development.
- **LedgerSync**'s answer to scale is a config line, `maxEntriesToLoad: 20` —
  the same `tail -N` shape under a different name, and exactly the gap
  measured above in 5,580 of 6,432 re-reads. Its entries also aren't
  addressed to anyone specific: *"every agent reads the same grounding docs
  and the same ledger."*

(We haven't tested agent-relay or sean2077/agent-ledger to the same depth, so
no specific claim is made about them beyond sharing the same markdown
substrate.)

So the honest comparison for this project isn't a chat tool — it's
`maxEntriesToLoad: 20`. Every project we've found in this space currently
answers "how do I catch up" with "load the last N." This project measured
what that costs and gave each agent a cursor instead:
`GET /inbox/<agent>` + `POST /inbox/<agent>/leido`.

## When does this actually help? (the honest threshold)

The 10x saving shows up at a certain **write rate** — not at a certain agent
count, and not at a certain file size. Measured on this project's real
deployment:

| write rate | what a `tail -500` covers |
|---|---|
| 22 entries/hour (median) | ~1.7 hours |
| 101 entries/hour (p90) | ~22 minutes |
| 303 entries/hour (peak) | ~7 minutes |

This also depends on how verbose your entries are. With one-line entries, a
`tail -500` shows around 250 of them and covers days. With this project's own
entries — a median of 13 lines each — it shows about 37 and covers minutes.

The line we'd want told to us, and the one we're telling you: **this starts
to matter once your agents are writing more than roughly 20 long entries an
hour** — not "you need 30 agents," and not "your log needs to be huge."

## How agents write

An entry is a markdown header plus free text — no SDK, no client library
required. The exact grammar (header syntax, the fixed set of entry types,
what happens to an entry that doesn't parse) is documented in
[`PROTOCOL.md`](./PROTOCOL.md).

## What this serves

- `GET /inbox/<agent>` — entries addressed to `<agent>` since its cursor.
  Read-only; advances nothing by itself.
- `POST /inbox/<agent>/leido` — the only call that advances the cursor, and
  only up to what was actually read.
- `GET /entries`, `GET /lint`, `GET /chain/verify`, `GET /stat` — search,
  a per-field typing-debt census, an append-only integrity check, and a
  mount-drift detector.
- **`POST /append` (experimental).** A validated write path — it exists and
  is tested, but mounts are `:ro` by default and this is *not* the primary
  way to write: in this project's own deployment, raw `>>` still outnumbers
  it roughly 8 to 1. Treat it as optional, not as "how you're supposed to
  write now."
- A small read-only web UI at `/ui`, useful if you want to look at a ledger
  yourself instead of through an agent. It's a convenience, not the product —
  the client this is built for is an agent calling the HTTP API.

## What this deliberately does not do

- **Is not a source of truth.** It stores nothing that isn't already in the
  markdown. The database can be deleted entirely and rebuilds in ~12 seconds.
  Stop the service, and everyone falls back to `tail`/`grep`/`>>` — nothing
  blocks on this being up.
- **Does not sign anything cryptographically.** Investigated and dropped:
  the incident that raised the question happened outside the ledger, and
  without real key custody a signature doesn't reduce the attack surface —
  it just relocates it to key management. Attribution today comes from
  harness-level tooling outside this repo's scope. The roster format leaves
  an empty per-agent key field for the day this needs to change, without a
  format migration.
- **Is not the default write path.** See `POST /append` above.
- **Does not index your wiki, knowledge base, or docs corpus.** Coordination,
  not corpus, by design. A knowledge base's value is a citation graph checked
  against the filesystem; treating every edit as a new timestamped event is a
  bad model for a document meant to converge, not accumulate.
- **Is not an LLM observability or tracing tool.** It never sees a model
  call — no token cost, no latency, no evals. It indexes coordination text
  written between agents, not calls made to a model. If you're looking for
  LLM observability, this isn't that category.

## Teams: multiple humans, each with their own agents

Tested with two independent git clones and four agents writing concurrently.
It works, but three assumptions that only held on a single machine had to be
rebuilt:

- **Entry position isn't identity.** A union merge (`*.md merge=union` in
  `.gitattributes`) keeps every entry byte-for-byte but not their order — a
  late entry can land in the middle of the file after a merge. Identity is
  the hash of an entry's content; the inbox cursor tracks local arrival
  order, so a reordered entry still shows up for whoever hadn't seen it yet.
- **The agent roster has to be data, not code.** With one human it can be a
  constant; with several, every new agent would mean a redeploy. It's a JSON
  file now (`roster.json`, gitignored — start from `roster.example.json`),
  and it carries an empty key field per agent for future per-agent signing.
- **How a ledger gets mounted depends on how it gets written.** Git does not
  append in place — it writes a new file and renames it over the old one. A
  file-level bind mount pins to the inode, so after a `git pull` the
  container can end up still reading the old file. Ledgers that live in a
  git repo need a directory mount; ledgers written only with raw `>>` (which
  preserves the inode) can stay file-to-file. `llmi stat` compares host
  and container byte counts as a tripwire for exactly this.

What's left isn't code: where the shared repo lives, and whether each person
runs their own instance against their own clone (the simple option, and the
one actually tested) or there's one shared instance. Either way, a
force-push-protection rule on the git remote is what actually prevents
history rewrites — this service doesn't do that job.

## Security & privacy

- **Local by design.** No telemetry, no outbound network calls at runtime —
  this only reads local files and serves HTTP on loopback.
- **Token required, fails closed.** Every route except `/health` requires an
  `X-Llminbox-Token` header; without a valid token, nothing is served,
  including on first boot.
- **Loopback alone is not isolation.** A `127.0.0.1`-only binding looks safe
  but isn't, at least on Docker Desktop for macOS: another container on the
  same machine can reach a loopback-published port via `host.docker.internal`
  regardless of which Docker network it's on. This was verified directly —
  a container with no declared relationship to this service reached its
  status endpoint over `host.docker.internal` and read the entire index
  before the token requirement was added. The token is what actually closes
  this; the port binding alone does not.
- **The token protects the network, not the host.** Anyone who already has
  access to the Docker daemon on this machine — the `docker` group, which on
  Linux is equivalent to root — can read the token in plain text via `docker
  inspect` or `/proc/<pid>/environ`, no network access required. On a server
  shared by more than one person, that's a real boundary the token does not
  cover. The threat model here is "another process on the network," not
  "another user of this Docker daemon."
- **Mounts are read-only and scoped to individual files or directories** —
  never the home directory — and stay `:ro` unless you opt into the
  experimental write path.
- **Untrusted content is marked, not filtered.** Ledger entries are free
  text written by other LLMs. `/inbox` is the one place that text reaches
  another agent automatically without a human reading it first, so its
  response carries an explicit warning that the payload is data, not
  instructions. Reading the same content via `GET /entries` does not carry
  that marker yet — if you build a script around `/entries` instead of
  `/inbox`, add that marking yourself.

## What we found while building this

The short version: a hash-chain integrity check was designed, measured, and
retired because it turned out to be inert — it always matched itself. Two
real bugs (an index that fossilized on file rotation, and an event-loop
stall of a few seconds) passed the first six falsifiers we wrote and only
surfaced under adversarial review, which is why the falsifiers exist as a
table, not a claim: twelve currently run clean, and the one that matters
most is the one that can go red — change one word inside a sealed entry and
the integrity check names the entry, its line, and its header.

The full account — every measurement, both false starts on the hash chain,
and the three team-coordination assumptions that broke under a second
machine — lives in [`docs/DESIGN-NOTES.es.md`](./docs/DESIGN-NOTES.es.md)
(Spanish; this is where the project was designed and the numbers were
first measured).

## License & lineage

Apache License 2.0 — see [`LICENSE`](./LICENSE).

This project's design was shaped by ideas from
[`block/buzz`](https://github.com/block/buzz) (also Apache-2.0) — the
relay-owns-the-log shape, typed and addressed events, validating at more
than one point in the pipeline, and the hash-chain approach that was tried
and retired. No code was copied or ported; see [`NOTICE`](./NOTICE) for the
full, verified account of what was borrowed as an idea versus what was
independently built.
