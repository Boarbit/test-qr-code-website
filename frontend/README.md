# sv

Everything you need to build a Svelte project, powered by [`sv`](https://github.com/sveltejs/cli).

## Creating a project

If you're seeing this, you've probably already done this step. Congrats!

```sh
# create a new project in the current directory
npx sv create

# create a new project in my-app
npx sv create my-app
```

## Developing

Once you've created a project and installed dependencies with `npm install` (or `pnpm install` or `yarn`), start a development server:

```sh
npm run dev

# or start the server and open the app in a new browser tab
npm run dev -- --open
```

## Building

To create a production version of your app:

```sh
npm run build
```

You can preview the production build with `npm run preview`.

> To deploy your app, you may need to install an [adapter](https://svelte.dev/docs/kit/adapters) for your target environment.

## CSV exports

- Visit `/export` in the frontend to pick container/item columns, control how detail fields are handled, and optionally filter which items are included before downloading a CSV.
- The backend also exposes `GET /containers/export`, which accepts repeated `container_fields`, `item_fields`, `detail_keys`, and `item_filter` query params. Filters follow a `field:value` syntax where fields can be `name`, `quantity`, or `detail.<label>`.

## Data storage

- The backend now persists containers in a SQLite database (default path `backend/app/containers.db`). Set `DATABASE_URL` to point elsewhere if needed.
- On first launch the tables are created automatically and seeded with the same sample containers that previously lived in memory.

## Docker

Run everything (frontend + backend + SQLite) from the repo root (the directory that contains the `frontend/` and `backend/` folders):

```sh
cd /path/to/test-qr-code-website
docker compose -f frontend/docker-compose.yml up --build
```

- Frontend is served at http://localhost:5173
- Backend/API is at http://localhost:8000
- Container data persists in the `backend-data` volume (a SQLite file on the backend container). Use `docker compose -f frontend/docker-compose.yml down` (add `-v` to drop the volume) when you’re done.
