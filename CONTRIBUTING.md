# Contributing

## Running it from source

```bash
./llmi init --demo    # creates a sample ledger so day one is not an empty screen
./llmi build          # explicit: `up` no longer builds
./llmi up
./llmi inbox alice-backend
```

`./llmi init` scans your disk for ledgers and **asks before mounting anything**. Say
no to whatever is not yours: mounting a ledger, even read-only, exposes its contents
to anything that reaches the port. Permanent exclusions go in `.llminbox-excluir`
(one pattern per line, git-ignored).

## Working on the UI

```bash
cd web && pnpm install && pnpm dev
```

Vite proxies the API to `127.0.0.1:8077`, so run the service first. The build is
compiled into the Docker image, so users never need Node — that is deliberate and
should stay true.

## Before you open a pull request

```bash
docker build -t llminbox:test . && IMAGEN=llminbox:test ./tests/humo.sh
```

The smoke test checks 13 properties. **Each one has its falsifier written next to
it** — what you would see if the property were broken. If you add a check, add its
falsifier too: a check that cannot fail checks nothing.

## House rules that are not negotiable

1. **Entry text is rendered as text, never as HTML.** It is written by language
   models. No `dangerouslySetInnerHTML`, no markdown rendering without a security
   review of the trust boundary.
2. **No network at runtime.** No CDN fonts, no remote images, no link previews.
   Everything is compiled into the image. Self-hosted means self-hosted.
3. **Contrast is calculated, not eyeballed.** Three tokens shipped failing WCAG AA
   because they looked fine. If you touch a colour, compute the luminance ratio.
4. **Dependencies are justified.** Each one is supply-chain surface — a build here
   already failed because pnpm rejected a transitive package published three hours
   earlier. That policy is a feature; do not relax it.
5. **The markdown files stay the source of truth.** The index is derived and
   disposable. If the service dies, nobody is blocked — that property is tested,
   and any change that breaks it is a change to what this product *is*.

## Style

Code comments are in Spanish — they encode measured lessons and the team reads
them. Everything user-facing is in English.
