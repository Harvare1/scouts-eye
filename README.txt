ANDRABLICKEN SCOUTING NETWORK – LOKAL PILOT
==========================================

Detta är en körbar webbapplikation med konto, databas, matchuppdrag,
rapportredigering, PDF-export, uppladdningar, klubbvy och minikurs.

STARTA PÅ WINDOWS
1. Installera Python 3.11 eller senare om det inte finns.
2. Packa upp ZIP-filen i en egen mapp.
3. Dubbelklicka på starta_windows.bat.
4. Gå till http://127.0.0.1:8000 i webbläsaren.
5. Stoppa servern med Ctrl+C i terminalfönstret.

MAC/LINUX
python -m pip install -r requirements.txt
python -m uvicorn app:app --host 127.0.0.1 --port 8000

DEMOINLOGGNINGAR – ENDAST FÖR LOKAL PILOT
Demokonton är avstängda som standard. Aktivera dem endast i en separat lokal
testdatabas med ANDRABLICKEN_SEED_DEMO=1 och välj ett eget lokalt lösenord i
ANDRABLICKEN_DEMO_PASSWORD. Lägg aldrig det lösenordet i Git.

TESTA DET HÄR ARBETSFLÖDET
1. Logga in som klubb, skapa ett uppdrag och klistra in en BEHÖRIG videolänk.
2. Tilldela en scout direkt, eller låt scouten ansöka om ett ledigt uppdrag.
3. Logga in som scout, öppna uppdraget och klicka på videolänken.
4. Skapa spelarrapport eller motståndarrapport och fyll i relevanta avsnitt.
5. Placera spelare på taktiktavlan, spara utkastet och hämta rapportens PDF.
6. Ladda vid behov upp en separat PDF som bilaga.
7. Skicka rapporten för administratörens granskning.
8. Som admin: godkänn rapporten eller begär komplettering.
9. Som klubb: se och ladda ner endast godkända rapporter.
10. Som scout: gå till Scout Academy och testa lektionerna och kunskapsprovet.

RAPPORTMALLAR
Spelarrapport: 8 flersidiga A4-landskapsark, PDF.
Motståndarrapport: 16 flersidiga A4-landskapsark, PDF.
Blankmallarna finns i static/ och kan laddas ner utan registrering.
Rapporter med mycket text kan få extra bilagesidor så att inget innehåll försvinner.

VIDEO
Portalen visar en länk till matchen hos dess ursprungliga leverantör.
Den delar INTE automatiskt behörigheter hos Veo, Hudl eller andra tjänster.
Den lagrar INGA videofiler. Klubben måste ordna laglig åtkomst.

UTBILDNING
Scout Academy har tre korta lektioner, en praktisk övningsbeskrivning
för varje lektion och ett femfrågors kunskapstest. Detta är endast en pilot.
Det finns inga betalningar, köpta kurser eller officiella certifikat.

SÄKERHET / INFÖR PUBLICERING
DEN HÄR DEMON FÅR INTE SÄTTAS PÅ INTERNET I NUVARANDE FORM.
Före lansering behövs bl.a. verifiering av klubbar, säkrare kontohantering,
e-postverifiering, kontoverifiering, HTTPS, lösenordsåterställning,
säkra serverinställningar, backups, loggning, dataskyddsrutiner,
ägarskap av klubbdata och avtal om matchvideo.

LAGRING
SQLite-databasen skapas automatiskt i data/portal.sqlite3.
PDF-bilagor sparas under data/uploads. De kan bara nås via portalkontroller.
Radera INTE data-mappen om du vill behålla sparade rapporter.

Teknisk stack: Python, FastAPI, SQLite, Jinja2, ReportLab.
Kontakt för projektet: malte@soldalen.nu

KURSPLAN
Se KURSPLAN.md för planerat innehåll, examinationskrav och produktion.
