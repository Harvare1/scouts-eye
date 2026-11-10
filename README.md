# Andrablicken

Andrablicken är en svensk pilotplattform för fotbollsscouting. Den samlar klubbuppdrag, behöriga externa videolänkar, scoutrapporter, administrativ granskning, PDF-export och en mindre utbildningsdel.

Serverroller, trafikflöde och GitHub Actions beskrivs med diagram i [docs/ARKITEKTUR.md](docs/ARKITEKTUR.md).

## Lokal utveckling

```sh
python -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q
.venv/bin/python -m uvicorn app:app --host 127.0.0.1 --port 8000
```

Demokonton är avstängda som standard. För en separat lokal testdatabas kan de aktiveras explicit:

```sh
ANDRABLICKEN_SEED_DEMO=1 \
ANDRABLICKEN_DEMO_PASSWORD='välj-ett-lokalt-lösenord' \
.venv/bin/python -m uvicorn app:app --host 127.0.0.1 --port 8000
```

Demokonton kan aldrig aktiveras när `ANDRABLICKEN_ENV=production`.

## Produktionskonfiguration

Den hostade pilotmiljön kräver:

- `ANDRABLICKEN_ENV=production`
- `ANDRABLICKEN_STORAGE=/app/data`
- `ANDRABLICKEN_SESSION_SECRET`, minst 32 tecken
- `ANDRABLICKEN_ALLOWED_HOSTS`, kommaseparerade värdnamn
- `ANDRABLICKEN_ALLOW_REGISTRATION=0`
- `ANDRABLICKEN_SEED_DEMO=0`

På en tom databas krävs dessutom en engångsbootstrap via `ANDRABLICKEN_BOOTSTRAP_ADMIN_EMAIL` och `ANDRABLICKEN_BOOTSTRAP_ADMIN_PASSWORD`. Lösenordet lagras endast som PBKDF2-hash i databasen och ska tas bort ur processmiljön efter första starten.

SQLite-databasen och uppladdningar lagras beständigt i `/opt/andrablicken/data` på appservern. Den nuvarande piloten kör därför en appinstans. Horisontell replikering kräver först migrering till PostgreSQL och delad objektlagring.

## Säkerhetsgränser

- Öppen registrering är avstängd i hostad pilot.
- Demokonton seedas inte i produktion.
- Sessionscookies är Secure och värdnamn valideras.
- Klubbdata, rapporter, bilagor och uppdrag kontrolleras per roll och klubb.
- Matchvideo hostas inte av Andrablicken; endast behöriga externa länkar får användas.
- Detta är fortfarande en pilot. E-postverifiering, återställning av lösenord, revisionslogg, databasmigrationer, backupautomatik och full GDPR-process återstår före bred lansering.
