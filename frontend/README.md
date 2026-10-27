# Frontend

React SPA for the interview dashboard. Vite, React Router, Tailwind.

See the [root README](../README.md) for how to run both halves together
(`./dev.sh`), or run this half alone:

```bash
bun install
bun run dev        # http://localhost:5173
```

Reads `VITE_API_URL`, defaulting to `http://localhost:8000`. See `.env.example`.

```bash
bun run typecheck
bun run lint
bun run test
```
