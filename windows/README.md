# M-PAS Windows Client

## Run locally

1. Start the API from the repository root:

```bash
docker compose up --build --wait
```

2. Run `dist/MPAS.Desktop.exe` on Windows 10/11.
3. Keep the API URL as `http://localhost:8000/` when Docker runs on the same Windows machine.
4. Use the development account:

```text
Username: demo
Password: change-me
```

For an API running on another computer, enter its reachable address in the API URL field, for example `http://192.168.1.20:8000/`.

## Rebuild

From the repository root:

```bash
make windows
```

The self-contained executable is written to `windows/dist/MPAS.Desktop.exe`.
