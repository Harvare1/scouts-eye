# Andrablicken – överlämning till Codex

## Mål
Bygg en svensk webbplattform för fotbollsscouting med ett flöde från klubbens uppdrag och behörig matchvideo till scoutens rapport, administratörens granskning och klubbens tillgång till godkända rapporter. Lägg därefter till en grundlig kursplattform. Varumärkets arbetsnamn är **Andrablicken** (tidigare namnförslag Eagle Eye). Visuell stil: mörk skogsgrön, limeaccent, typografiskt enkel, professionell fotbollskaraktär. Språk: svenska.

## Källfiler och nuläge
Detta repo kommer från en fungerande **lokal pilot**, inte en produktionsklar tjänst. Läs `README.txt` och `KURSPLAN.md`.

Teknikstack:
- Python, FastAPI, Jinja2
- SQLite för lokal testning
- ReportLab för PDF
- Statiska HTML/CSS/JavaScript, bland annat en digital taktiktavla
- `app.py` – applikation, användarroller, lag, uppdrag, ansökningar, rapporter, kursdemo
- `pdf_reports.py` – rapport-PDF:er
- `templates/` – UI
- `static/` – grafik, taktik, stil och PDF-blanketter

Det finns tre demokonton (se README.txt) som **inte får följa med till publicerad miljö**. Innehållet består av exempeldata. Matchvideo är en extern länk; applikationen hostar ingen matchfilm och kan inte kringgå videoleverantörens behörigheter.

## Avsedd produkt
Tre roller:
- **Scout:** medlemsprofil, tilldelade/lediga uppdrag, matchlänkar, tidsstämplade observationer, webbrapporter, PDF-generering, status och egen portfolio, kursgenomförande.
- **Klubb:** verifierat klubbkonto, skapa uppdrag, dela behörig videolänk, se inkomna godkända rapporter, ladda ned/exportera.
- **Admin:** hantera klubbverifiering, scouttilldelning, rapportgranskning, avslag/kompletteringar, kurser och användare.

Rapporttyper:
- **Spelarrapport**: fullständig flersidig rapport, identitet/match, position och kontext, teknik, taktik, fysik, observerade mentala aspekter, styrkor, utvecklingsområden, rekommendation, konfidens/observationsunderlag, relevanta tidsstämplar och taktiska diagram.
- **Motståndarrapport**: omfattande lag- och matchanalys, laguppställning, formationer, press, speluppbyggnad, försvar, omställningar, fasta situationer, nyckelspelare, risker, styrkor, svagheter, matchplansrekommendation och taktiska diagram.

Kurser:
- Introduktion till scouting med pedagogiskt kursmaterial, lektioner, quiz och **manuellt granskad praktisk rapportuppgift**.
- Först senare högre nivåer, betalning och kursintyg. Inte kalla kursintyget officiell SvFF-/UEFA-ackreditering.

## Viktigt: uppdatera verklig status, inte bara UI
Den interaktiva chatten innehöll också en fristående klickbar mockup. Den är INTE repo-källkoden; utgå från den lokala pilotens faktiska implementation. Granska vad som finns, reproducerar och testa innan du lovar funktionalitet.

## Rekommenderad arbetsordning
1. Reproducera den lokala piloten, installera beroenden, kör tester/manuella smoke-tests. Dokumentera funktioner och säkerhetsbrister.
2. Strukturera om projektet för underhåll och skapa testsvit. Lägg till databasmigrationer och ett begripligt konfigurationssystem.
3. Härda autentisering och behörighetskontroll, separat klubbåtkomst, filuppladdningssäkerhet, CSRF, sessions, HTTPS, loggning och sekretess/GDPR. Radera seedade demoidentiteter från produktionsläget.
4. Fullborda uppdrags-, match- och rapportflödet inklusive autosave, versionshantering, granskningsstatus, PDF-export och interna bilagor.
5. Förbättra den responsiva svenska frontenddesignen utan att förlora fokus på funktion.
6. Skapa en stängd stagingmiljö genom ägarens befintliga infrastruktur och GitHub-baserad driftsättning. Inga hemligheter i kod eller chatt.
7. Implementera utbildning stegvis efter pilot med riktiga scouter och klubbar.

## Driftsättning och säkerhet
Ägaren har egen infrastruktur men specifikationerna är ännu inte fastställda. Välj inte molnleverantör, domän eller deploymentarkitektur utan att inspektera miljön. Föreslå Docker Compose/Nginx/PostgreSQL bara som ett alternativ beroende på befintlig miljö. Använd GitHub Secrets eller serverns sekretesshantering; begär aldrig att privata nycklar eller produktionslösenord klistras in i chatt eller repo.

**Ingen automatisk produktionsdriftsättning utan uttryckligt godkännande.** Inga verkliga matchfilmer får kopieras/streamas via plattformen utan licens eller rättighetshavarens tillstånd.

## Första konkreta Codex-uppdrag
"Inspektera hela koden och kör piloten lokalt. Gör en välgrundad gap-/säkerhetsanalys mot målflödet klubb → uppdrag → behörig match → scout → rapport → granskning → klubbens nedladdning. Lägg sedan upp en prioriterad implementeringsplan och genomför steg 1 med tester. Visa exakt vilka ändringar och tester du utfört. Publicera inget på nätet ännu."
