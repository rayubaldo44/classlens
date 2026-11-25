# ClassLens frontend

React and TypeScript implement the teacher workflow. Start with the repository
[README](../README.md) for backend configuration and the synthetic demo.

Use Node 22 from `.nvmrc`, then run from this directory:

```bash
npm ci
npm run dev
```

Vite defaults to `http://localhost:5173`. If needed, copy `.env.example` to `.env`
and set the public API origin in `VITE_API_URL`; it defaults to
`http://localhost:8000`. **Every `VITE_*` value is public.** Keep Gemini keys and
database credentials on the backend only. The root demo runner sets matching
frontend/backend origins automatically.

```bash
npm test
npm run lint
npm run build
npx playwright install chromium
npm run test:e2e
```

The Chromium smoke starts its own frontend and intercepts API calls with synthetic
contract fixtures. It needs no Gemini key, database, or model download and does
not verify live AI output. `npm run build` writes the static bundle to `dist/`.
