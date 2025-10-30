# TradingAgents Frontend

This package contains the Next.js Control Center used to orchestrate and observe TradingAgents sessions.

- Setup & workspace instructions: [docs/SETUP.md](../../docs/SETUP.md)
- Development workflow, testing, and linting: [docs/DEVELOPMENT.md](../../docs/DEVELOPMENT.md)
- API endpoints consumed by the dashboard: [docs/API.md](../../docs/API.md)

To run the dashboard in development mode:

```bash
pnpm --filter @tradingagents/frontend dev
```

By default the app expects the backend at `http://localhost:8000`. Override with `NEXT_PUBLIC_API_URL` in `packages/frontend/.env.local` if required.
