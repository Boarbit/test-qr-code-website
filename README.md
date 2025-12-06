## Docker

Run everything (frontend + backend + SQLite) from the repo root (the directory that contains the `frontend/` and `backend/` folders):

```sh
cd /path/to/test-qr-code-website
docker compose -f frontend/docker-compose.yml up --build
```

- Frontend is served at http://localhost:5173
- Backend/API is at http://localhost:8000
- Container data persists in the `backend-data` volume (a SQLite file on the backend container). Use `docker compose -f frontend/docker-compose.yml down` (add `-v` to drop the volume) when you’re done.





## Other Notes

The Docker will open up two things for access to the website,

- Local: http://localhost:5173/

The local address is to be used by the machine that is running the program. You copy+paste the address into a browser in the machine running the program, and you will get to the website. 