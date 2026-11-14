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

På en tom databas krävs dessutom en engångsbootstrap via `ANDRABLICKEN_BOOTSTRAP_ADMIN_USERNAME`, `ANDRABLICKEN_BOOTSTRAP_ADMIN_EMAIL` och `ANDRABLICKEN_BOOTSTRAP_ADMIN_PASSWORD`. Lösenordet lagras endast som PBKDF2-hash i databasen och ska tas bort ur processmiljön efter första starten.

SQLite-databasen och uppladdningar lagras beständigt i `/opt/andrablicken/data` på appservern. Den nuvarande piloten kör därför en appinstans. Horisontell replikering kräver först migrering till PostgreSQL och delad objektlagring.

## Kontohantering

Administratörer hanterar klubbar och användare på `/admin/users`. Där går det att skapa unika användarnamn, spara kontakt-e-post, ändra roll och klubbtillhörighet, stänga av eller aktivera konton och återställa lösenord. Inloggning sker med användarnamn; e-postadressen används som kontaktuppgift. Alla användare kan byta sitt eget lösenord på `/account`.

Vid start migreras äldre SQLite-databaser automatiskt med status och sessionsversion för användarkonton. Avstängning, lösenordsåterställning och kontoändringar avslutar äldre sessioner. Tillfälliga lösenord ska lämnas till användaren genom en separat säker kanal; e-postinbjudan och automatisk lösenordsåterställning ingår ännu inte i piloten.

## Mallbibliotek och rapportfiler

Inloggade användare når `/mallbibliotek` för att välja och ladda ner den 8-sidiga spelarrapportmallen eller den 16-sidiga motståndarrapportmallen. Scouter och administratörer kan därifrån ladda upp en färdig PDF till en redigerbar rapport för rätt uppdrag, match och klubb. Samma roll- och klubbkontroller gäller som i rapportflödet, och klubben ser filen först efter godkännande.

PDF-bilagor lagras tillsammans med övrig beständig appdata under `/opt/andrablicken/data` på appservern. En separat filserver behövs inte för pilotens nuvarande eninstansdrift. Vid horisontell skalning ska filerna flyttas till delad objektlagring innan fler appinstanser startas.

## Rapporteditor och scouttilldelning

Rapporteditorn byggs från samma kapitel- och frågedefinitioner som PDF-exporten, så rubrikerna kan inte glida isär. Varje rapportkapitel har en egen digital taktiktavla. Spelare kan flyttas, Lag A och Lag B numreras separat och rörelsepilar kan ritas. Endast tavlor med innehåll tas med på motsvarande PDF-sida. Taktikdata valideras och begränsas per kapitel innan den sparas.

Motståndarrapporten skiljer mellan utgångs-, uppspels- och etableringsformation, efterfrågar de tre senaste matchresultaten samt matchbild före och efter betydande byte. Editorn betonar exakt minut eller tidsstämpel och en avgränsad matchsituation per observation. Spelarrapporten frågar uttryckligen hur spelaren passar laget som scoutingen utförs för.

Klubbkonton skapar uppdrag men kan inte välja eller tilldela scout. De kan lämna ett scoutönskemål som möjlig tilläggstjänst. Scouter anmäler intresse och administratören får en tydlig notifiering i adminpanelen för att granska profil och tilldela uppdraget. Scout Academy visas endast för scout och admin; klubbrollen blockeras även på serversidan.

## Scoutprofiler och fotbolls-CV

Scouter hanterar sin profil via **Scoutprofil** i huvudmenyn. Profilen innehåller fotbollsbakgrund, erfarenhet, egna meriter, kompetenser, språk, tillgänglighet och ett valfritt PDF-CV på högst 8 MB. Hela profilen kan exporteras som en separat Andrablicken-PDF.

Egen text visas alltid som **Självuppgivet**. Uppdrag och rapporter visas separat som **Verifierat av Andrablicken** och hämtas automatiskt från administrativt godkända rapporter; scouten kan inte själv skapa eller redigera verifierade poster. En klubb kan endast se profilen för en scout som är tilldelad, har ansökt eller har en godkänd rapport för den klubben. I klubbvyn filtreras verifierad historik till den egna klubbens uppdrag för att bevara tenantisolering. Administratörer och profilens scout ser hela verifierade historiken.

CV-filer lagras under `data/uploads/cv` i samma beständiga volym som rapportbilagor. En ny fil ersätter den gamla. Åtkomst sker alltid genom applikationens rollkontroll; uppladdningskatalogen exponeras inte statiskt.

Databastabellen `scout_profiles` skapas idempotent vid start. Ingen separat manuell migrering krävs för befintliga SQLite-installationer.

## Säkerhetsgränser

- Öppen registrering är avstängd i hostad pilot.
- Demokonton seedas inte i produktion.
- Sessionscookies är Secure och värdnamn valideras.
- Klubbdata, rapporter, bilagor och uppdrag kontrolleras per roll och klubb.
- Matchvideo hostas inte av Andrablicken; endast behöriga externa länkar får användas.
- Detta är fortfarande en pilot. E-postverifiering, återställning av lösenord, revisionslogg, databasmigrationer, backupautomatik och full GDPR-process återstår före bred lansering.
