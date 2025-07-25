# MINTJENS Database Portaal

Een professionele, enterprise-grade single entry point voor MINTJENS database management systemen.

## Overzicht

Het MINTJENS Database Portaal biedt gecentraliseerde toegang tot:
- **HOUTANALYSE**: AI-gestuurde houtdetectie en kwaliteitsanalyse
- **CNC DATALOG**: Real-time machine monitoring en productiedata
- **PROJECT DATALOG**: Geïntegreerd project- en resource management

## Kenmerken

- **Enterprise Design**: Professionele MINTJENS branding met bedrijfskleuren
- **Real-time Status Monitoring**: Live systeem status updates
- **Responsive Interface**: Geoptimaliseerd voor desktop, tablet en mobiel
- **Loading Screen**: Professionele laadervaring met systeemchecks
- **Keyboard Shortcuts**: Snelle navigatie met toetsenbord (1-3 voor apps, 'i' voor info)
- **Schaalbaar**: Eenvoudig uitbreidbaar met nieuwe modules

## Installatie

1. Clone of download de repository
2. Pas `config.json` aan met de juiste database URLs
3. Deploy naar een webserver (Apache, Nginx, etc.)
4. Configureer HTTPS voor productiegebruik

## Configuratie

### Database URLs Aanpassen

Bewerk `config.json`:

```json
{
  "databases": [
    {
      "id": "houtanalyse",
      "name": "HOUTANALYSE",
      "url": "/houtanalyse",  // Pas deze URL aan
      "version": "v2.1.0",
      "enabled": true
    }
  ]
}
```

### Bedrijfsinstellingen

```json
{
  "settings": {
    "companyName": "MINTJENS",
    "theme": {
      "primaryDark": "#002555",
      "primaryLight": "#028ee4",
      "backgroundMain": "#f4f7f6",
      "backgroundContainer": "#ffffff"
    }
  }
}
```

## Features

### Status Monitoring
- Automatische controle elke 30 seconden
- Visuele indicators voor systeemstatus
- Waarschuwingen bij offline systemen

### Keyboard Shortcuts
- `1`: Navigeer naar HOUTANALYSE
- `2`: Navigeer naar CNC DATALOG
- `3`: Navigeer naar PROJECT DATALOG
- `i`: Open informatie modal
- `ESC`: Sluit modal

### Deep Linking
Directe toegang via URL parameters:
```
https://portal.mintjens.nl/?app=houtanalyse
```

## Structuur

```
PORTAAL/
├── index.html          # Hoofdpagina met enterprise layout
├── styles.css          # MINTJENS styling en animaties
├── script.js           # Geavanceerde functionaliteit
├── config.json         # Systeem configuratie
├── favicon.svg         # MINTJENS favicon
└── README.md          # Deze documentatie
```

## API Integratie

Voor status monitoring, implementeer deze endpoints:

```javascript
// Status check endpoint voor elk systeem
GET /api/status/houtanalyse
GET /api/status/cnc-datalog
GET /api/status/project-datalog

// Response format
{
  "status": "online",
  "version": "v2.1.0",
  "lastCheck": "2024-01-01T12:00:00Z"
}
```

## Deployment Checklist

- [ ] HTTPS configuratie
- [ ] Content Security Policy headers
- [ ] Database URLs bijgewerkt
- [ ] Analytics geïmplementeerd
- [ ] Backup strategie
- [ ] Monitoring alerts

## Browser Ondersteuning

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Beveiliging

- Content Security Policy geïmplementeerd
- Geen gevoelige data in frontend
- Authenticatie via individuele systemen
- HTTPS verplicht voor productie
- Regular security audits

## Support

Voor technische ondersteuning, neem contact op met de MINTJENS IT-afdeling.

---
© 2024 MINTJENS. Alle rechten voorbehouden.