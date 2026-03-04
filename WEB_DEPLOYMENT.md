# ETF Monitor - Web App Deployment auf Vercel

## 🚀 Schnellstart

### 1. GitHub Repository erstellen

```bash
cd ~/Desktop/DEV/etf-monitor

# Git initialisieren (falls noch nicht geschehen)
git init

# Alle Dateien hinzufügen
git add .
git commit -m "Initial commit: ETF Monitor Web App"

# GitHub Repository erstellen und pushen
# Gehe zu: https://github.com/new
# Erstelle ein neues Repository (z.B. "etf-monitor")
# Dann:
git remote add origin https://github.com/DEIN-USERNAME/etf-monitor.git
git branch -M main
git push -u origin main
```

### 2. Auf Vercel deployen

#### Option A: Über Vercel Website (Einfachste Methode)

1. Gehe zu [vercel.com](https://vercel.com) und melde dich an
2. Klicke auf "Add New" → "Project"
3. Importiere dein GitHub Repository
4. Vercel erkennt automatisch die Konfiguration
5. Klicke auf "Deploy"
6. Fertig! 🎉

#### Option B: Über Vercel CLI

```bash
# Vercel CLI installieren
npm install -g vercel

# Deployment starten
cd ~/Desktop/DEV/etf-monitor
vercel

# Folge den Anweisungen:
# - Login mit GitHub
# - Bestätige Projekt-Einstellungen
# - Deploy!
```

### 3. Umgebungsvariablen setzen (Optional)

Wenn du Slack-Benachrichtigungen für ALLE Nutzer aktivieren möchtest:

1. Gehe zu deinem Projekt auf Vercel
2. Settings → Environment Variables
3. Füge hinzu:
   - Key: `SLACK_WEBHOOK_URL`
   - Value: `https://hooks.slack.com/services/...`
4. Redeploy

**Hinweis:** Nutzer können auch ihre eigenen Slack-Webhooks im Frontend eingeben.

---

## 📱 Nach dem Deployment

### Deine Web-App URL

Nach dem Deployment bekommst du eine URL wie:
```
https://etf-monitor-xxx.vercel.app
```

Diese URL kannst du mit jedem teilen! ✨

### Was Nutzer können:

1. **URL öffnen** - Keine Installation nötig!
2. **"Check starten" klicken** - Monitoring läuft
3. **Ergebnisse sehen** - Übersichtlich im Dashboard
4. **(Optional) Slack-Webhook eingeben** - Für persönliche Benachrichtigungen

---

## ⚙️ Wichtig zu wissen

### Timeout-Limits auf Vercel

**Kostenloser Plan (Hobby):**
- Timeout: 10 Sekunden
- Unser Quick Scan prüft deshalb nur **3 URLs pro ETF** (gesamt 6 URLs)
- Das ist schnell genug für <10s

**Für Full Scan (alle 18 URLs):**
- Nutze GitHub Actions (siehe unten)
- Oder upgrade zu Vercel Pro ($20/Monat) für 60s Timeout

### Full Scan mit GitHub Actions

Für automatische tägliche Full Scans:

1. Erstelle `.github/workflows/monitor.yml`:

```yaml
name: Daily ETF Monitoring

on:
  schedule:
    - cron: '0 8 * * *'  # Täglich um 8 Uhr
  workflow_dispatch:  # Manueller Trigger

jobs:
  monitor:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run monitoring
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
        run: ./run.sh
      - name: Commit results
        run: |
          git config user.name "ETF Monitor Bot"
          git config user.email "bot@etf-monitor.app"
          git add outputs/
          git commit -m "Update monitoring results" || true
          git push
```

2. Füge Secret hinzu:
   - GitHub Repository → Settings → Secrets
   - Neues Secret: `SLACK_WEBHOOK_URL`

---

## 🎨 Frontend anpassen

### Farben ändern

Bearbeite `web/public/css/style.css`:

```css
:root {
    --primary: #3b82f6;     /* Hauptfarbe */
    --success: #10b981;     /* Erfolg (grün) */
    --warning: #f59e0b;     /* Warnung (gelb) */
    --danger: #ef4444;      /* Fehler (rot) */
}
```

### Texte ändern

Bearbeite `web/public/index.html`

### Nach Änderungen:

```bash
git add .
git commit -m "Update design"
git push
```

Vercel deployed automatisch! 🚀

---

## 💡 Tipps

### 1. Custom Domain

Möchtest du eine eigene Domain wie `etf-monitor.meine-domain.de`?

1. Vercel Dashboard → Settings → Domains
2. Füge deine Domain hinzu
3. Setze DNS-Einträge (Vercel zeigt dir wie)

### 2. Analytics

Vercel bietet kostenlose Analytics:
- Dashboard → Analytics
- Sieh wie viele Leute deine App nutzen!

### 3. Mehrere Nutzer

Die App kann von unbegrenzt vielen Leuten gleichzeitig genutzt werden!
Jeder kann:
- Monitoring starten
- Ergebnisse sehen
- Eigene Slack-Webhooks nutzen

---

## 🔒 Sicherheit

### API-Schutz (Optional)

Wenn du die App nur für bestimmte Leute freigeben möchtest:

1. Füge Passwort-Schutz hinzu
2. Nutze Vercel's Authentication
3. Oder: Teile URL nur privat (Vercel-URLs sind schwer zu erraten)

---

## 🐛 Troubleshooting

**Problem:** Deployment schlägt fehl
**Lösung:** Check Logs in Vercel Dashboard → Deployments → Details

**Problem:** API Timeout
**Lösung:** Normal bei kostenlosen Plan! Nutze GitHub Actions für Full Scans

**Problem:** Scraping funktioniert nicht
**Lösung:** Manche Websites blockieren Vercel IPs. Das ist normal.

---

## 📊 Kosten

**Vercel Hobby (Kostenlos):**
- ✅ Unbegrenzte Deployments
- ✅ 100 GB Bandwidth/Monat
- ✅ Serverless Functions: 100 GB-Stunden
- ✅ Ausreichend für deine Nutzung!

**Upgrade nur nötig wenn:**
- Du >10.000 Nutzer/Monat hast
- Du längere Timeouts brauchst (>10s)

---

## 🎉 Fertig!

Du hast jetzt eine professionelle Web-App die:
- ✅ Jeder ohne Installation nutzen kann
- ✅ Kostenlos gehostet wird
- ✅ Automatisch updated (bei Git Push)
- ✅ Modern und schön aussieht

**Teile einfach die URL mit anderen!** 🚀

---

## Fragen?

- Vercel Docs: https://vercel.com/docs
- Support: https://vercel.com/support
