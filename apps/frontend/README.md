# Requirements Bot Frontend

Next.js web interface for AI-powered requirements gathering.

## Quick Start

```bash
# From monorepo root
npm run dev:frontend

# Or from this directory
npm install
npm run dev
```

Opens at `http://localhost:3000` (backend must be running at port 8080)

**Prerequisites**: Node.js 18+, backend running

## Environment Setup

```bash
cp .env.local.example .env.local
```

Edit `.env.local`:
```bash
NEXT_PUBLIC_API_URL=http://localhost:8080
GOOGLE_CLIENT_ID=your-google-oauth-client-id
```

## Stack

- Next.js 15.5+ (App Router)
- React 19.1+
- TypeScript 5.9+ (strict)
- Tailwind CSS 4.1+
- Auto-generated types from `@req-bot/shared-types`

## Scripts

```bash
npm run dev          # Dev server with Turbopack
npm run build        # Production build
npm run start        # Production server
npm run lint         # ESLint
npm run type-check   # TypeScript check
```

## Type Safety

```typescript
import type { paths, components } from '@req-bot/shared-types';

type SessionResponse = components['schemas']['SessionResponse'];
type CreateSessionRequest = components['schemas']['CreateSessionRequest'];
```

Backend API changes → run `npm run generate:types` from monorepo root

<details>
<summary>Project Structure</summary>

```
apps/frontend/src/
├── app/                    # Next.js pages
│   ├── auth/              # OAuth handling
│   ├── interview/         # Interview flow
│   └── login/             # Login page
├── components/
│   ├── auth/              # Auth components
│   ├── interview/         # Interview UI
│   ├── layout/            # Nav, Footer
│   └── ui/                # Reusable components
├── lib/                   # API clients, utils
├── hooks/                 # Custom React hooks
└── types/                 # TypeScript types
```

</details>

## Common Issues

**Type errors from `@req-bot/shared-types`**
```bash
cd ../..  # Go to monorepo root
npm run generate:types
```

**Can't connect to backend**
- Ensure backend running at port 8080
- Check `NEXT_PUBLIC_API_URL` in `.env.local`
- Verify CORS settings in backend

**OAuth issues**
- Verify `GOOGLE_CLIENT_ID` matches backend
- Check redirect URI in Google Console
- Ensure backend has `OAUTH_CLIENT_ID` and `OAUTH_CLIENT_SECRET`

## More Info

- [Main README](../../README.md) - Full project overview
- [DEVELOPMENT.md](../../DEVELOPMENT.md) - Development workflows
- [CONTRIBUTING.md](../../CONTRIBUTING.md) - Code standards

## License

MIT License
