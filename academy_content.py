"""Originalutkast för Andrablicken Academy.

Innehållet är skrivet för Andrablicken och får kvalitetssäkras i adminpanelen.
Seederfunktionen i app.py skapar bara poster som saknas och skriver därför inte
över senare redaktionella ändringar.
"""

INTRO_COURSE = {
    "slug": "introduktion-fotbollsscouting",
    "title": "Introduktion till fotbollsscouting",
    "summary": "Grundläggande matchobservation, spelaridentifiering och rapportskrivning för svensk senior-, akademi- och breddfotboll.",
    "level": "Grundkurs",
    "access_type": "free",
    "price_ore": 0,
    "estimated_minutes": 180,
    "study_time_label": "2–3 timmar",
    "status": "draft",
    "modules": [
        {
            "title": "Grundkurs",
            "summary": "Sex lektioner, kunskapstest och manuellt bedömd praktisk examination.",
            "lessons": [
                {
                    "slug": "scoutens-roll",
                    "title": "Scoutens roll inom fotbollen",
                    "learning_objective": "Förstå varför klubbar arbetar med scouting och hur observationer omvandlas till beslutsunderlag.",
                    "body": """En fotbollsscout samlar och analyserar information som hjälper en klubb att fatta bättre sportsliga beslut. Uppdraget kan handla om att identifiera potentiella nyförvärv, analysera en kommande motståndare eller bedöma lagets egen prestation.

Scouting är inte enbart att identifiera bra spelare. En spelare som fungerar utmärkt i ett lag behöver inte nödvändigtvis passa i ett annat. Därför måste scouten förstå klubbens behov, spelarens roll och sammanhanget bakom prestationen.

Vi ska skilja på tre delar:

• Observation: Vad såg vi faktiskt?
• Tolkning: Vad kan observationen betyda?
• Rekommendation: Vad bör klubben göra med informationen?""",
                    "example": "En central mittfältare slår många passningar bakåt. Det betyder inte automatiskt att spelaren saknar offensiv förmåga. Det kan bero på motståndarens press, medspelarnas rörelser eller lagets instruktioner.",
                    "exercise": "Skriv tre frågor du vill ställa till en sportchef innan du börjar scouta en mittfältare.",
                    "diagram_kind": "decision-chain",
                    "question": "Vilken formulering är en observation snarare än en tolkning?",
                    "choices": ["Mittfältaren saknar mod", "23:40 spelar mittfältaren tillbaka till mittback under press", "Mittfältaren passar inte vår spelidé"],
                    "correct_index": 1,
                    "explanation": "En observation beskriver vad som faktiskt sker och när. De andra alternativen är tolkningar som kräver mer underlag.",
                },
                {
                    "slug": "spelets-faser",
                    "title": "Förstå spelets olika faser",
                    "learning_objective": "Kunna identifiera spelets huvudfaser och skilja lagets organisation från enskilda aktioner.",
                    "body": """En match ska observeras utifrån flera spelfaser:

1. Anfallsspel – när laget har kontroll över bollen.
2. Försvarsspel – hur laget organiserar sig utan boll.
3. Offensiv omställning – agerandet när laget vinner bollen.
4. Defensiv omställning – agerandet direkt efter bolltapp.
5. Fasta situationer – exempelvis hörnor och frisparkar.

Scouten ska undersöka både lagets grundstruktur och hur den förändras beroende på matchsituation.

En formation är inte hela spelidén. Ett lag kan exempelvis utgå från 4-3-3, försvara sig i 4-5-1 och bygga upp spelet med tre spelare i den första linjen.""",
                    "example": "Fiktiva Sjöstad IF utgår från 4-3-3. Med boll flyttar vänsterbacken in centralt och den defensiva mittfältaren sjunker mellan mittbackarna. Utan boll faller yttrarna ned och laget försvarar i 4-5-1.",
                    "exercise": "Växla mellan med boll och utan boll på taktiktavlan. Beskriv vilken formation du ser och nämn en positionsförändring.",
                    "diagram_kind": "phase-board",
                    "question": "Vilket påstående beskriver bäst skillnaden mellan formation och spelidé?",
                    "choices": ["Formation och spelidé är samma sak", "Formationen visar utgångspositioner men organisationen kan ändras mellan spelfaser", "En formation gäller bara vid fasta situationer"],
                    "correct_index": 1,
                    "explanation": "Utgångsformationen är en startpunkt. Roller och positioner förändras ofta när laget anfaller, försvarar eller ställer om.",
                },
                {
                    "slug": "spelaridentifiering",
                    "title": "Grundläggande spelaridentifiering",
                    "learning_objective": "Kunna observera en spelare strukturerat och bedöma prestation i förhållande till roll och matchkontext.",
                    "body": """Spelarscouting handlar om att identifiera egenskaper och beteenden som är relevanta för en specifik roll.

Vi delar in observationerna i:

• Teknik: Förstatouch, passningar, bollkontroll och utförande under press.
• Taktik: Positionering, scanning, spelförståelse och beslutsfattande.
• Fysik: Observerad snabbhet, acceleration, styrka och uthållighet.
• Mentala och beteendemässiga faktorer: Kommunikation, arbetsinsats och reaktioner på matchsituationer.

En enda match räcker sällan för att bedöma en spelares långsiktiga potential.""",
                    "example": "En defensiv mittfältare behöver inte ha flest bollkontakter för att göra en bra prestation. Positioneringen kan vara avgörande för att laget ska kunna spela sig ur motståndarens press.",
                    "exercise": "Observera en valfri central mittfältare under minst 15 minuter och dokumentera fem konkreta aktioner, inklusive två utan boll.",
                    "diagram_kind": "player-lens",
                    "question": "Varför ska en spelare bedömas i förhållande till sin roll?",
                    "choices": ["Alla positioner har samma krav", "Rollens uppgifter avgör vilka beteenden som är relevanta", "Det gör att en match alltid räcker"],
                    "correct_index": 1,
                    "explanation": "En handling får mening i sitt taktiska sammanhang. En defensiv mittfältare och en ytterforward har olika prioriterade uppgifter.",
                },
                {
                    "slug": "motstandaranalys",
                    "title": "Grundläggande motståndaranalys",
                    "learning_objective": "Kunna identifiera motståndarens återkommande spelmönster och sammanfatta dem inför en match.",
                    "body": """Vid motståndaranalys ska vi inte enbart beskriva vad ett lag gör. Vi ska försöka förstå varför laget gör det och hur den beställande klubben kan använda informationen.

Analysera särskilt:

• Grundformation och positionsförändringar.
• Speluppbyggnad och anfallsvägar.
• Presshöjd och försvarsorganisation.
• Offensiva och defensiva omställningar.
• Fasta situationer.
• Nyckelspelare och återkommande sårbarheter.

Skilj på ett enskilt misstag och ett återkommande taktiskt mönster.""",
                    "example": "Fiktiva Västerdal BK spelar vid två separata tillfällen förbi hög press genom att målvakten hittar en nedfallande sexa. Samma lösning i flera sekvenser kan vara ett mönster; en ensam lyckad passning är inte tillräcklig.",
                    "exercise": "Jämför de två fiktiva matchsituationerna i illustrationen och identifiera hur laget försöker spela sig ur press.",
                    "diagram_kind": "press-solutions",
                    "question": "När bör ett beteende beskrivas som ett återkommande mönster?",
                    "choices": ["Efter en enstaka situation", "När det återkommer i flera relevanta situationer och kontexter", "När resultatet i matchen är positivt"],
                    "correct_index": 1,
                    "explanation": "Ett mönster kräver upprepade observationer. Matchresultatet avgör inte i sig om beteendet är återkommande.",
                },
                {
                    "slug": "dokumentation-rapporter",
                    "title": "Dokumentation och scoutingrapporter",
                    "learning_objective": "Kunna skriva en rapport som en tränare eller sportchef faktiskt kan använda.",
                    "body": """En scoutingrapport ska vara tydlig, saklig och fokuserad på uppdragets syfte.

Varje viktig slutsats bör kunna kopplas till observationer. Använd matchminut, spelfas och en beskrivning av händelsen.

Rapporten ska innehålla en sammanfattning, tydliga observationer, styrkor, utvecklingsområden och slutsatser.""",
                    "example": "Observation: Vid 18:40 och 32:15 flyttar motståndarens högerback upp mycket högt.\nTolkning: Det uppstår en möjlig yta bakom ytterbacken efter bolltapp.\nRekommendation: Undersök om snabba spelvändningar mot den ytan kan vara ett alternativ.\nOsäkerhet: Två situationer räcker inte för att bekräfta ett återkommande mönster.",
                    "exercise": "Skriv tre konkreta matchobservationer och koppla varje observation till en möjlig taktisk konsekvens.",
                    "diagram_kind": "evidence-chain",
                    "question": "Vilken del saknas om en rapport går direkt från observation till en säker rekommendation?",
                    "choices": ["En bedömning av tolkning och osäkerhet", "Spelarens födelsedag", "Matchens publiksiffra"],
                    "correct_index": 0,
                    "explanation": "Scouten behöver förklara hur observationen tolkas och hur säkert underlaget är innan en rekommendation ges.",
                },
                {
                    "slug": "professionalism-etik",
                    "title": "Professionalism, etik och kvalitet",
                    "learning_objective": "Förstå scoutens ansvar gentemot klubbar, spelare och andra scouter.",
                    "body": """Scouter hanterar ibland konfidentiella uppgifter. Rapporter, klubbens instruktioner och privata matchlänkar får inte delas med obehöriga.

Scouten måste också redovisa eventuella intressekonflikter. En person som representerar en klubb kan inte automatiskt ta alla uppdrag från konkurrenter.

Undvik obefogade påståenden om spelares personlighet, hälsa eller framtida karriär. Bedöm observerade fotbollsbeteenden och redovisa osäkerhet.

Vid scouting av minderåriga krävs särskilda rutiner för personuppgifter, video och åtkomst.""",
                    "example": "Tre fiktiva situationer: en privat Hudl-länk skickas av en vän, en scout erbjuds uppdrag från en direkt konkurrent till den egna klubben och en rapport gäller en minderårig spelare. I samtliga fall ska behörighet, intressekonflikt och dataskydd klarläggas innan arbetet fortsätter.",
                    "exercise": "Beskriv lämpligt agerande i de tre etiska situationerna: obehörig matchlänk, möjlig intressekonflikt och scouting av minderårig.",
                    "diagram_kind": "ethics-check",
                    "question": "Vad ska scouten göra vid en möjlig intressekonflikt?",
                    "choices": ["Dölja den för att få uppdraget", "Redovisa den och invänta beslut innan uppdraget accepteras", "Dela klubbens instruktioner med andra scouter"],
                    "correct_index": 1,
                    "explanation": "Öppen redovisning skyddar klubbarna, scouten och plattformens förtroende. Uppdraget ska inte påbörjas innan konflikten hanterats.",
                },
            ],
        }
    ],
}


INTRO_QUIZ = [
    ("Vilken ordning gör en scoutingbedömning spårbar?", ["Rekommendation – rykte – observation", "Observation – tolkning – rekommendation", "Betyg – känsla – slutsats"], 1, "Observationen är underlaget, tolkningen förklarar betydelsen och rekommendationen anger nästa steg."),
    ("Vad ska scouten klarlägga före ett spelaruppdrag?", ["Klubbens behov och den aktuella rollen", "Endast spelarens statistik", "Vilken agent spelaren har"], 0, "Bedömningen måste utgå från klubbens beslutssituation och rollkrav."),
    ("Vilken spelfas börjar direkt när laget vinner bollen?", ["Defensiv omställning", "Offensiv omställning", "Fast situation"], 1, "Offensiv omställning beskriver lagets första agerande efter bollvinst."),
    ("Varför räcker inte beteckningen 4-3-3 för en motståndsanalys?", ["Formationer används aldrig", "Organisation och roller kan förändras mellan spelfaser", "Alla 4-3-3-lag spelar likadant"], 1, "Utgångsformationen beskriver inte automatiskt press, uppspel eller positionsförändringar."),
    ("Vilken observation är mest användbar?", ["Spelaren var svag", "61:20 scannar sexan två gånger före mottagning och spelar förbi press", "Spelaren borde byta klubb"], 1, "Den anger minut och observerbart beteende utan obestyrkta personomdömen."),
    ("Hur bör fysisk förmåga beskrivas utan testdata?", ["Som observerat beteende i matchsituationer", "Som en medicinsk diagnos", "Som ett säkert maxvärde"], 0, "Matchscouting kan beskriva observerad acceleration eller uthållighet men inte ersätta tester eller medicinsk bedömning."),
    ("Vad skiljer ett taktiskt mönster från ett enskilt misstag?", ["Mönstret återkommer i flera relevanta situationer", "Misstaget leder alltid till mål", "Mönstret syns bara i statistik"], 0, "Upprepning och kontext krävs för att beskriva ett återkommande mönster."),
    ("Vad ska följa en stark rekommendation?", ["Konkreta observationer och redovisad osäkerhet", "Så många adjektiv som möjligt", "En garanti om framtida utveckling"], 0, "Rekommendationen måste vara underbyggd och avgränsad av underlagets kvalitet."),
    ("Får en privat matchlänk delas med en annan scout?", ["Ja, om matchen är intressant", "Endast om behörighet och rättighetshavare tillåter det", "Ja, om länken saknar lösenord"], 1, "Teknisk åtkomst är inte samma sak som tillåtelse att dela materialet."),
    ("Vad gäller efter godkänd grundkurs?", ["Deltagaren garanteras klubbuppdrag", "Kursen visar genomförd utbildning men ger ingen uppdragsbehörighet", "Deltagaren blir officiellt förbundslicensierad"], 1, "Academy och behörigheten för riktiga klubbuppdrag är separata processer."),
]


DRAFT_COURSES = [
    {
        "slug": "spelaridentifiering-rekrytering", "title": "Spelaridentifiering och rekrytering",
        "summary": "Fördjupning i flermatchobservation, positionsprofiler och rekryteringsrekommendationer.",
        "level": "Fördjupning", "access_type": "paid", "price_ore": 149500, "estimated_minutes": 420, "study_time_label": "5–7 timmar", "status": "draft",
        "modules": [
            "Rekryteringsprocessen", "Positionsspecifik scouting", "Observation över flera matcher",
            "Teknisk, taktisk, fysisk och beteendemässig bedömning", "Rekryteringsrapport", "Examination",
        ],
    },
    {
        "slug": "motstandaranalys-taktisk-scouting", "title": "Motståndaranalys och taktisk scouting",
        "summary": "Fördjupning i spelorganisation, press, omställningar, fasta situationer och professionella motståndarrapporter.",
        "level": "Fördjupning", "access_type": "paid", "price_ore": 149500, "estimated_minutes": 420, "study_time_label": "5–7 timmar", "status": "draft",
        "modules": [
            "Analysuppdraget", "Formationer och spelorganisation", "Försvarsspel",
            "Omställningar och fasta situationer", "Från observation till matchplan", "Examination",
        ],
    },
]
