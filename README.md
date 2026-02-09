## Docker

Run everything (frontend + backend + SQLite) from the repo root (the directory that contains the `frontend/` and `backend/` folders):

```sh
cd /path/to/test-qr-code-website
docker compose -f frontend/docker-compose.yml up --build
```

### What that command does

- `docker compose` invokes Docker Compose, which can start several related containers with a single command.
- `-f frontend/docker-compose.yml` tells Compose to use the file that lives in the `frontend/` folder (run the command from the repo root so the path resolves correctly).
- `up` creates any missing containers, starts them, and tails their logs. The `--build` flag ensures the images are rebuilt from the current source before the containers start; drop `--build` once the images are current.

After the stack is running:

- Frontend is served at http://localhost:5173
- Backend/API is at http://localhost:8000
- Container data persists in the `backend-data` volume (a SQLite file on the backend container).

### Common Docker Compose commands

| Command | When to use it |
| --- | --- |
| `docker compose -f frontend/docker-compose.yml up` | Start the stack using the existing images. If the SQLite file already exists it will be reused; only the containers start up. |
| `docker compose -f frontend/docker-compose.yml up --build` | Rebuild the frontend/backend images and then start them. |
| `docker compose -f frontend/docker-compose.yml down` | Stop the running containers but keep the persistent `backend-data` volume so your database contents remain intact. |
| `docker compose -f frontend/docker-compose.yml down -v` | Stop everything **and** delete the `backend-data` volume. Use this for a clean slate when you want to reset the database entirely. |

## Other Notes

The Docker stack exposes the frontend to the host machine only:

- Local: http://localhost:5173/

Open that address in a browser on the same machine that is running Docker to use the app. The port binding intentionally rejects other devices on your network. 

## Feedback Follow-ups

- Added a "Main Menu" nav tab by renaming the Dashboard link (`frontend/src/routes/+layout.svelte`).
- Quick Load now pulls the latest containers from the API so newly created containers appear (`frontend/src/routes/+page.svelte`).
- Tightened the "Manage access" panel sizing to be less dominant in the header (`frontend/src/routes/+layout.svelte`).
- Moved the "View container" results block above the scanner so results appear higher on the dashboard (`frontend/src/routes/+page.svelte`).
- Renamed "Search All QR Codes" to "Search All Containers" (`frontend/src/routes/+page.svelte`).
- Export CSV now allows selecting specific containers, with a new `container_qr` filter and UI selection list (`backend/app/main.py`, `frontend/src/routes/export/+page.svelte`).
