# BarcodeMaster Wijzigingslogboek

Alle belangrijke wijzigingen, verbeteringen en bugfixes voor BarcodeMaster worden hier bijgehouden. Elke vermelding bevat de datum, een samenvatting van de wijziging en de betreffende bestanden of modules.

---

## [2025-06-13]
- **Dynamische "_REP_" Projectcode Logica:**
  - Vervangen van hardgecodeerde "MO07544_REP" logica met dynamische detectie voor alle projectcodes die "_REP_" bevatten.
  - Wanneer een scancode "_REP_" bevat, wordt automatisch "_REP" toegevoegd aan de geëxtraheerde projectcode (bijv. "MO07544" wordt "MO07544_REP").
  - Dit zorgt ervoor dat _REP_ projecten als aparte, geldige projecten in de database worden gelogd.
  - Betreft: `gui/panels/scanner_panel.py`
- **Scanner Panel "OPEN" Event Logica Verfijnd:**
  - Een "Mappen-check actief" checkbox toegevoegd voor elke gebruiker in de "OPEN" event configuratie.
  - Indien aangevinkt (standaard): "OPEN" event wordt alleen verstuurd als de projectcode overeenkomt met een bestand/map in het geconfigureerde pad van de gebruiker.
  - Indien uitgevinkt: "OPEN" event wordt standaard verstuurd voor die gebruiker, zonder mappen-check. Het padveld wordt uitgeschakeld en de waarde op "Niet ingesteld" gezet.
  - Alle nieuwe UI-elementen en berichten zijn in het Nederlands.
  - Configuratie opgeslagen in `scanner_panel_open_event_user_logic_active` in `config.json`.
  - Betreft: `gui/panels/scanner_panel.py`
  - De UI is verfijnd: de checkbox staat nu direct voor de gebruikersnaam en de tekst "Mappen-check actief" is verwijderd voor een strakker ontwerp.
- **Scannerpaneel: Verbeterde Dynamische "_REP_" Projectcode Logica**
  - De projectcode-extractie is verbeterd om dynamisch "_REP" projectcodes te herkennen uit scancodes.
  - Ondersteunt nu zowel "_REP_" als "_REP" patronen (hoofdletterongevoelig).
  - Wanneer een scancode deze patronen bevat, wordt automatisch "_REP" toegevoegd aan de geëxtraheerde projectcode (bijv. "MO07987" wordt "MO07987_REP").
  - Toegevoegde debug-logging om projectcode-extractie te traceren en problemen op te sporen.
  - Verbeterde logica voorkomt dubbele "_REP" toevoegingen en handelt verschillende scancode-formaten af.
  - Dit zorgt ervoor dat _REP_ projecten als aparte entiteiten worden behandeld in database logging en gebruikersrouting.
  - Betreft: `gui/panels/scanner_panel.py`

---

## [Unreleased] - 2024-12-13
### Toegevoegd
- **Nieuwe Instellingen Panel**: Geïntegreerde import functionaliteit van BarcodeMatch in BarcodeMaster
  - Nieuwe settings menu knop met `settings.png` icoon
  - Automatische gebruikerstype detectie (OPUS/GANNOMAT) voor verschillende workflows
  - **Event-Based Background Service**: Automatische import getriggerd door OPEN events in database
  
- **Background Import Service**: 
  - **Database Event Monitoring**: Monitort scan_events tabel voor nieuwe OPEN events
  - **Triggered Import Logic**: Automatische import alleen bij OPEN events voor matching gebruiker
  - **Project-Specific Processing**: Zoekt specifieke project bestanden/data bij OPEN event
  - Configureerbare scan intervallen (30-3600 seconden) voor database polling
  - Comprehensive logging naar bestand en UI
  
- **OPUS Gebruiker Flow**: 
  - Triggert bij OPEN event voor OPUS gebruiker in database
  - Zoekt automatisch naar project-specifieke .hop/.hops bestanden
  - Automatische API logging van import acties
  
- **GANNOMAT Gebruiker Flow**:
  - Triggert bij OPEN event voor GANNOMAT gebruiker in database
  - Zoekt automatisch naar project-specifieke database records
  - Automatische API logging van import acties
  
- **Geïntegreerde Project Code Extractie**:
  - Hergebruik van BarcodeMaster scanner panel matching logica
  - Dynamische "_REP_" project code handling (case-insensitive)
  - Consistente project code extractie met regex patterns

- **Settings Panel Features**:
  - Checkbox configuratie voor inschakelen/uitschakelen van automatische import
  - Separate OPUS en GANNOMAT database monitoring opties
  - Database path browser voor eenvoudige configuratie
  - Real-time service status monitoring met import statistieken
  - Live activiteit log met automatische scroll
  - Configuratie test functionaliteit

### Verbeterd
- **Dynamic "_REP_" Project Code Handling**: Verbeterde case-insensitive detectie van zowel "_REP_" als "_REP" patronen in gescande codes
  - Automatische detectie van "_REP_" in scan codes
  - Dynamische toevoeging van "_REP" suffix aan geëxtraheerde project codes
  - Debug logging voor project code extractie en transformatie
  - Ondersteuning voor zowel "_REP_" als "_REP" varianten (case-insensitive)

- **Event-Driven Architecture**: 
  - Database polling voor OPEN events in plaats van continue file monitoring
  - Triggered import alleen bij relevante OPEN events
  - Project-specifieke import processing
  - Reduced resource usage door event-based triggering

### Technische Details
- **Event Monitoring**: Database polling elke 30 seconden (configureerbaar) voor nieuwe OPEN events
- **Triggered Processing**: Import alleen bij OPEN events voor matching gebruiker (OPUS/GANNOMAT)
- **Project-Specific Search**: Automatische zoektocht naar project bestanden/data bij trigger
- **Configuration Persistence**: Automatische opslag van alle instellingen in config.json
- **Error Handling**: Comprehensive error handling met logging en user feedback
- **UI Responsiveness**: Alle heavy operations draaien in background threads
- **Status Monitoring**: Real-time status updates met import statistieken

---

## [2025-06-09]
- Optimalisatie van de "Start Database API" knop in het Admin Panel zodat alle blokkerende operaties in een achtergrondthread draaien, waardoor de GUI responsief blijft. (gui/panels/admin_panel.py)
- Robuuste logica toegevoegd om db_log_api.py of db_log_api.exe te starten, afhankelijk van de omgeving (broncode of verpakte exe). (gui/panels/admin_panel.py)
- Verbeterde foutafhandeling en gebruikersfeedback voor API/database initialisatie. (gui/panels/admin_panel.py, database/db_log_api.py)
- Implementatie van robuuste, meertraps LAN IP-detectie in het Admin Panel, met weergave voor netwerkconfiguratie. (gui/panels/admin_panel.py)
- Ervoor gezorgd dat LAN IP-detectie bij het opstarten van het paneel in een achtergrondthread draait voor een responsieve GUI. (gui/panels/admin_panel.py)
- `NameError` opgelost gerelateerd aan de `socket` module in de LAN IP-detectielogica. (gui/panels/admin_panel.py)
- Ervoor gezorgd dat alle belangrijke codewijzigingen consistent zijn met de projectstructuur en naamgevingsconventies. (gehele project)

---

## [2025-06-08]
- Persistent panel instance management voor alle GUI-panelen (pack_forget/pack in plaats van destroy/recreate). (gui/app.py, gui/panels/*)
- Alle gebruikersinvoervelden worden nu persistent opgeslagen in config.json voor alle panelen. (config_utils.py, gui/panels/*)
- Strikte bestands- en naamconsistentie gehandhaafd voor alle paneel- en klassewijzigingen. (gehele project)
- Projectdirectory structuur bijgewerkt en gedocumenteerd voor duidelijkheid en onderhoudbaarheid. (README.md, project root)

---

## [Eerder]
- Initiele projectstructuur en kernmodules opgezet.
- Database, configuratie en GUI-framework ingesteld.
