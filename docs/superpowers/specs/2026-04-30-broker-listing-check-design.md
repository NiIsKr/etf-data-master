# ETF Monitor v2 — Broker Listing Check (Design)

**Datum:** 2026-04-30
**Status:** Design — wartet auf Approval
**Stakeholder:** Nils (Owner), Leona (Operations, primärer User)

---

## 1. Ziel

Das bestehende ETF-Monitoring-Tool um eine Broker-Listing-Prüfung erweitern. Operations soll auf einen Klick sehen, bei welchen deutschen Brokern die naroiq-ETFs gelistet sind, mit welchen TER, unter welchem Namen — und ob ein Broker den ETF fälschlich als "komplexes Finanzinstrument" klassifiziert (Inyova-Bug-Pattern: blockiert Vertrieb durch zwingenden Knowledge-Test).

## 2. Use Case

- **Wer:** Leona (Operations)
- **Wann:** On-demand vor Vertriebs-/Sales-Aktionen, wenn ein neuer ETF live geht oder bei Verdacht auf Listing-Fehler
- **Was:** Schnelle Übersicht "wo bei welchem Broker hakt was"
- **Erfolg:** WRONG_CATEGORY-Befunde werden sofort erkannt und an den Broker gemeldet

Nicht im Scope: periodisches Tracking, Historie, Slack-Alerts, Multi-User-Access.

## 3. Architektur

```
Frontend (public/index.html + js)
  ├─ Counter-Cards (✓/⚠/❌/?)
  ├─ Section "Broker Listings" (14 Broker)
  └─ Section "Daten-Quellen"   (8 Info-Sites)
        │
        ▼
Vercel Lambda (api/monitor.py)
  ├─ Source dispatcher
  ├─ Renderer-Strategy:
  │     • SSR-Sites (8 Info + comdirect + avl) → requests + condense
  │     • SPA-Sites (~12 Broker) → Playwright headless
  ├─ LLM Extraktion (Haiku 4.5) — 5 Felder pro Quelle
  └─ Status-Logic + Aggregation
```

**Hosting Playwright:** Vercel Lambda mit `@sparticuz/chromium`. **Vorbehaltlich Spike-Test (Phase 1.0).** Falls Spike zeigt, dass Lambda-Hosting für 14 Broker nicht stabil ist, wechseln wir auf Browserless.io. Concurrency-Limit für Playwright-Jobs auf max. 4 parallel, um Memory-Druck im Lambda zu begrenzen.

## 4. Datenmodell

```python
ETFS = {
    "LU3098954871": {
        "name": "TEQ - General Artificial Intelligence R EUR UCITS ETF (Acc)",
        "short_name": "TEQ",
        "ter": 0.69,
        "category": "standard_ucits",   # NEU
    },
    "LU3075459852": { …, "category": "standard_ucits" },  # Inyova
}

SOURCES = {
    "LU3098954871": [
        {"url": "https://justetf.com/...",         "type": "info",   "renderer": "http"},
        {"url": "https://comdirect.de/...",        "type": "broker", "renderer": "http"},
        {"url": "https://www.ing.de/...",          "type": "broker", "renderer": "playwright"},
        {"url": "https://app.traderepublic.com/...","type": "broker", "renderer": "manual"},
        …
    ]
}
```

Pro Quelle: `type` (info/broker), `renderer` (http/playwright/manual). `manual` heißt: kein automatischer Check, im UI als "manuell prüfen" markiert.

## 5. LLM-Extraktion

**Briefing-Strategie:** LLM bleibt für **alle** Felder zuständig (auch wo deterministische Heuristiken theoretisch möglich wären). Erfahrung im ETF Monitor: Regex-First scheitert an Heterogenität der Quellen, LLM mit semantischem Kontext ist robuster. Risiko der Fehler-Korrelation (alle Felder kippen wenn Modell Seitentyp falsch versteht) wird durch klares Page-Type-Briefing abgefangen.

**LLM extrahiert pro Quelle:**

| Feld | Erwartung | Werte |
|---|---|---|
| `page_type` | Was ist das für eine Seite? | `detail` / `search_no_results` / `search_ambiguous` / `error_or_block` |
| `name` | ETF-Name auf der Seite | String oder None |
| `ter` | Total Expense Ratio | Float oder None |
| `category` | Klassifikations-Label | `standard_ucits` / `spezialitaeten` / `hebel` / `aif` / `strukturiert` / `unknown` |
| `listed` | Boolean (abgeleitet aus page_type) | `true` wenn `page_type == detail` mit klarem ISIN+Name-Match, sonst `false` |

**Briefing für `category`:**
> "Such nach explizitem Klassifikations-Feld auf der Seite (Anlagekategorie, Anlageklasse, Fondskategorie, Unterkategorie, Produktart, Besondere Strategie). Ignoriere generische Footer-Disclaimer und Risiko-Warnungen. Wenn kein explizites Feld auf der Detail-Seite zu sehen ist, antworte mit `unknown` — das ist kein Fehler."

**Briefing für `page_type`:**
> "Ist die Seite eine echte ETF-Detail-Page mit ISIN+Name prominent angezeigt (`detail`), eine Suchseite mit klarem 'Kein Treffer'-Marker (`search_no_results`), eine Such-/Generic-Page wo der ETF nicht eindeutig als Hauptinhalt erscheint (`search_ambiguous`), oder eine Error-/Block-Seite (`error_or_block`)?"

## 6. Status-Logic

**Pro Quelle, schlimmster Befund gewinnt:**

| Bedingung | Status | Farbe | Bedeutung |
|---|---|---|---|
| HTTP-Error / Timeout | `UNREACHABLE` | ⚫ schwarz | Site nicht erreichbar |
| `page_type == error_or_block` | `UNREACHABLE` | ⚫ schwarz | Antwort, aber blockiert (Bot-Detection, Login-Wand) |
| `page_type == search_no_results` | `NOT_LISTED` | ⚪ grau | Klare Negativ-Evidenz: Broker hat ETF nicht im Sortiment |
| `page_type == search_ambiguous` | `AMBIGUOUS` | 🔘 hellgrau | Trefferlage unklar — manuelle Prüfung empfohlen |
| `page_type == detail` UND `category` ∉ `{standard_ucits, unknown}` | `WRONG_CATEGORY` | 🔴 rot | **Blockiert Vertrieb** — sofortiger Handlungsbedarf |
| `page_type == detail` UND `name` weicht stark ab | `WRONG_NAME` | 🟠 orange | Inkonsistenz |
| `page_type == detail` UND `ter` weicht ab (>0.05% Diff) | `WRONG_TER` | 🟠 orange | Inkonsistenz |
| `page_type == detail` UND `ter == None` sonst ok | `TER_MISSING` | 🟡 gelb | Hinweis: Quelle zeigt TER nicht im DOM |
| Alles passt | `MATCH` | 🟢 grün | OK |
| `renderer == manual` | `MANUAL_CHECK` | 🔘 hellgrau | Nicht automatisch prüfbar (App-Login etc.) |

**Wichtige Regeln:**
- `category == unknown` ist explizit **kein** Fehler. Viele Info-Quellen haben gar kein Kategorie-Feld.
- `TER_MISSING` ist Warnhinweis, nicht Block. Manche Quellen zeigen TER einfach nicht (z.B. deutsche-boerse heute).
- `AMBIGUOUS` ist neuer Status für die Lücke zwischen "klar gelistet" und "klar nicht gelistet" — verhindert False Confidence in beide Richtungen.
- `WRONG_CATEGORY` wird im UI prominent hervorgehoben, weil es als einziger Status den Vertrieb blockiert.

## 7. UI

```
[ TEQ - General AI ]                                [ Inyova ]
Soll: Standard UCITS, TER 0,69%

┌────────────────────────────────────────────────────────────┐
│  ✓ 18 OK   ⚠ 2 Wrong   ❌ 1 Not Listed   ? 1 Ambiguous   │
└────────────────────────────────────────────────────────────┘

▼ Broker Listings (14)
  🔴  ING                  WRONG_CATEGORY    Spezialitäten   ─ blockiert Vertrieb
  ⚪  S Broker             NOT_LISTED        ─               
  🔘  Trade Republic       MANUAL_CHECK      App-only        
  🔘  Smartbroker+         AMBIGUOUS         Such-Page       ─ manuell verifizieren
  🟢  comdirect            MATCH             ETF
  ...

▼ Daten-Quellen (8)
  🟢  justETF              MATCH             ─
  🟡  deutsche-boerse      TER_MISSING       ─ TER nicht im DOM
  ...
```

**UI-Verhalten:**
- Sortierung pro Sektion: WRONG_CATEGORY → WRONG_TER/NAME → NOT_LISTED → AMBIGUOUS → UNREACHABLE → MANUAL_CHECK → TER_MISSING → MATCH
- Counter-Cards aggregieren über beide Sektionen
- Per-Zeile expandierbar: zeigt URL, extrahierte Werte, Soll-Werte und Modell-Erklärung im Detail

## 8. Phasen-Plan

### Phase 1.0 — Spike-Test (vor Implementation)

**Ziel:** Realitäts-Check bevor Architektur festgezogen wird. Codex-Empfehlung.

- 4 schwierige Broker durchspielen: ING, S Broker, 1822direkt, Trade Republic
- Pro Broker dokumentieren:
  - URL-Pattern für ETF-Detail (oder Search-Path)
  - Wie wird ISIN/Name auf der gerenderten Seite dargestellt?
  - Welche Selektoren/Wartezeiten für Playwright?
  - Bot-Detection oder Geo-Blocking aktiv?
  - Cold-Start-Verhalten in Vercel-Lambda (oder Test-Skript)
- **Output:** Entscheidung "Vercel-Lambda+Playwright reicht" oder "wir brauchen Browserless/separater Service"

**Dauer:** 1 Tag

### Phase 1.A — Infrastruktur (nach Spike)

- Datenmodell-Refactor: `ETFS.category`, `SOURCES` mit `type`+`renderer`-Tags
- LLM-Prompt erweitern (5 Felder mit Page-Type)
- Status-Logic implementieren (8 neue Status)
- UI-Update: Counter-Cards, zwei Sektionen, sortierte Tabelle, expandierbare Zeilen
- Playwright-Setup (Vercel direkt oder externer Service je nach Spike)
- ThreadPoolExecutor mit Concurrency-Limit für Playwright-Workers (max 4)

**Dauer:** 1-2 Tage

### Phase 1.B — Broker schrittweise einbauen

Reihenfolge nach erwarteter Erfolgswahrscheinlichkeit:

1. comdirect (schon drin) ✓
2. avl-investmentfonds (schon drin) ✓
3. 1822direkt (Hash-Routing → Playwright)
4. ING (Search → Playwright)
5. Consorsbank (Direct + Search → Playwright)
6. S Broker (Finder → Playwright)
7. maxblue (Finder → Playwright)
8. Smartbroker+ (Liste → Playwright)
9. Scalable Capital (via justETF-Liste)
10. Commerzbank (nur Sparpläne — als Spezial-Status)
11. Trade Republic (App-only → `manual`)
12-14. Restliche Excel-Broker mit URL

Pro Broker: URL-Pattern + Playwright-Selektoren + Test gegen TEQ + Inyova.

**Dauer:** 1-2 Tage (Broker-pro-Broker, je nach Stolperstellen)

### Phase 1.C — Verifikation & Übergabe an Leona

- Vollständiger Run gegen TEQ + Inyova
- Screenshot der UI für Leona
- Kurze Doku (CLAUDE.md/README) update mit neuem Workflow
- Demo-Termin

**Dauer:** 0.5 Tag

## 9. Risiken & Annahmen

- **Cold-Start Vercel Lambda mit Playwright:** 5-15s. Bei sporadischer Nutzung jedes Mal neu spürbar. Akzeptabel für Operations-Tool.
- **Trade Republic / Scalable App-Login:** Wahrscheinlich nicht ohne Auth crawlbar — explizit als `manual` markiert, kein automated truth claim.
- **Performance:** ~30-60s pro vollem Check. Akzeptabel für on-demand Operations-Tool.
- **Broker ändert URL-Struktur:** Pro Broker eine Strategy-Kapsel; einfach zu pflegen.
- **Heterogenität Broker-Seiten:** Search/Product/Marketing/Login-Gate/Error-Fallback brauchen unterschiedliche Behandlung. Codex-Hinweis. Wird durch `page_type`-Klassifikation im LLM-Prompt abgefangen.
- **Persistenz fehlt:** Aktuell on-demand only, keine Historie. Codex weist darauf hin als langfristige Lücke. Out-of-scope für Phase 1, kann bei Bedarf später nachgezogen werden.

## 10. Bewusst NICHT im Scope

- Persistenz / Time-Series / Audit-Trail
- Periodischer Cron-Run mit Slack-/Email-Alerts
- Authentifizierung / Multi-User-Zugriff
- Hybrid-Extraktion (deterministisch + LLM): bewusst entschieden gegen die Codex-Empfehlung, basierend auf empirischer Erfahrung im Projekt (Regex-Heuristiken brachen brittle bei der bisherigen Quellen-Heterogenität)
- Headless-Auth bei Trade Republic / Scalable
- Manuelle Eintragspflege für die "No"-Broker aus Excel (DKB, Flatex, etc.)

## 11. Offene Punkte für Implementation-Plan-Phase

- Konkrete Vercel-Memory-Settings für Lambda mit Playwright
- LLM-Prompt-Wording (final) für Page-Type-Erkennung
- Genaues Cancel-/Timeout-Verhalten pro Quelle
- Wie Soll-Daten (`category: "standard_ucits"`) sauber im Frontend pro ETF anzeigen
- Concurrency-Limit-Mechanismus (asyncio.Semaphore vs ThreadPoolExecutor max_workers)
