# 🚀 ETF Monitor Web-App - Ganz Einfach!

## Schritt 1: Lokale Vorschau (Optional - zum Testen)

```bash
cd ~/Desktop/DEV/etf-monitor
python3 web_preview.py
```

Dann öffne in deinem Browser: **http://localhost:8000**

So siehst du wie die App aussieht! ✨

---

## Schritt 2: Auf Vercel veröffentlichen (Damit andere es nutzen können)

### A) GitHub Repository erstellen

1. Gehe zu: https://github.com/new
2. Repository Name: `etf-monitor` (oder was du willst)
3. Klicke "Create repository"

### B) Code hochladen

```bash
cd ~/Desktop/DEV/etf-monitor

git init
git add .
git commit -m "ETF Monitor Web App"
git branch -M main
git remote add origin https://github.com/DEIN-USERNAME/etf-monitor.git
git push -u origin main
```

**Ersetze `DEIN-USERNAME` mit deinem GitHub-Benutzernamen!**

### C) Auf Vercel deployen

1. Gehe zu: https://vercel.com
2. Klicke "Sign Up" und melde dich mit GitHub an
3. Klicke "Add New" → "Project"
4. Wähle dein `etf-monitor` Repository
5. Klicke "Deploy"

**Das war's!** 🎉

Nach ~2 Minuten bekommst du eine URL wie:
```
https://etf-monitor-xyz.vercel.app
```

---

## Schritt 3: URL teilen!

Diese URL kannst du jetzt mit **jedem** teilen!

Sie können dann:
1. URL öffnen
2. "Check starten" klicken
3. Ergebnisse sehen

**Keine Installation nötig!** ✨

---

## Wichtig zu wissen

### Quick Scan vs. Full Scan

**Quick Scan (Standard in der Web-App):**
- Prüft 6 URLs (3 pro ETF)
- Dauert ~5-10 Sekunden
- Perfekt für schnelle Checks!

**Full Scan (Alle 18 URLs):**
- Läuft über GitHub Actions (täglich automatisch)
- Siehe `WEB_DEPLOYMENT.md` für Details

### Slack-Benachrichtigungen

Jeder Nutzer kann seinen eigenen Slack-Webhook eingeben:
1. Gehe zu: https://api.slack.com/messaging/webhooks
2. Erstelle einen Webhook
3. Gib die URL in den "Einstellungen" ein
4. Fertig!

---

## Häufige Fragen

**Q: Kostet das Geld?**
A: Nein! Vercel ist kostenlos für deine Nutzung.

**Q: Wie viele Leute können die App nutzen?**
A: Unbegrenzt! Jeder kann die URL öffnen.

**Q: Muss ich programmieren können?**
A: Nein! Nach dem Deployment brauchst du nur die URL zu teilen.

**Q: Kann ich das Design ändern?**
A: Ja! Bearbeite `web/public/css/style.css` und push zu GitHub. Vercel updated automatisch!

**Q: Was wenn etwas nicht funktioniert?**
A: Schau in die Vercel Logs (Dashboard → Deployments → Details)

---

## Nächste Schritte (Optional)

### Eigene Domain nutzen

Statt `xyz.vercel.app` kannst du `etf-monitor.meine-domain.de` nutzen:

1. Vercel Dashboard → Settings → Domains
2. Domain hinzufügen
3. DNS-Einträge setzen (Vercel zeigt dir wie)

### Automatische Full Scans

Täglich um 8 Uhr automatisch alle 18 URLs checken:

1. Siehe `WEB_DEPLOYMENT.md` → "Full Scan mit GitHub Actions"
2. Erstelle `.github/workflows/monitor.yml`
3. Push zu GitHub
4. Fertig!

---

## Das war's! 🎉

Du hast jetzt eine professionelle Web-App die:
- ✅ Schön aussieht
- ✅ Jeder nutzen kann (ohne Installation)
- ✅ Kostenlos ist
- ✅ Automatisch updated

**Viel Erfolg!** 🚀
