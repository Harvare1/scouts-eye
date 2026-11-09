# Så fortsätter du Andrablicken i Codex

1. Packa upp detta ZIP-arkiv på datorn.
2. Öppna ChatGPTs datorapp och välj **Codex**, alternativt Codex-tillägget i VS Code.
3. Öppna projektmappen `Andrablicken_Portal` i Codex.
4. Klistra in denna första uppgift:

> Läs `AGENTS.md`, `PROJECT_CONTEXT.md`, `README.txt` och `KURSPLAN.md`. Inspektera, starta och testa nuvarande FastAPI-pilot. Gör först en konkret gap- och säkerhetsanalys för nästa iteration av Andrablicken. Implementera därefter det viktigaste saknade steget för det kompletta uppdragsflödet, med tester. Behåll svensk UI och nuvarande varumärke. Ingen produktionsdriftsättning och inga känsliga credentials i koden.

5. Skapa gärna ett **privat** GitHub-repository och checka in projektet efter att du granskat att inga hemligheter, databaser, uppladdade filer eller andra känsliga uppgifter följer med.
6. Uppge separat vilken infrastruktur du har och hur du vill köra staging. Lägg hemligheter i serverns eller CI-systemets sekretesshantering, inte i chatten.

**Att tänka på:** Den klickbara appen i ChatGPT var en fristående UI-demo; koden i detta arkiv är den lokala FastAPI-piloten.
