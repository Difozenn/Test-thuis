# Changelog

Alle belangrijke wijzigingen aan dit project worden in dit bestand bijgehouden.

Het formaat is gebaseerd op [Keep a Changelog](https://keepachangelog.com/nl/1.0.0/) (Nederlandse versie als beschikbaar, anders Engelse link behouden).

## [Nog Niet Uitgebracht] - 2025-06-18

### Added
- **Databasepaneel: Handmatige Events via Rechtermuisknopmenu**
  - Een rechtermuisknopmenu toegevoegd aan de logboekweergave in het databasepaneel.
  - Gebruikers kunnen nu handmatig 'OPEN' en 'AFGEMELD' events loggen voor een geselecteerd project.
  - Dit biedt meer controle voor het handmatig beheren van projectstatussen.
  - Betreft: `gui/panels/database_panel.py`

### Changed
- **Databasepaneel: Logboekfiltering Aangepast**
  - De logboekweergave in het databasepaneel filtert nu 'AFGEMELD' events om alleen die van de huidige dag te tonen.
  - 'OPEN' events (en andere statussen) blijven zichtbaar ongeacht hun datum, waarbij per project de meest relevante status wordt getoond (voorkeur voor 'OPEN').
  - Dit zorgt voor een schonere weergave van recente afgemelde projecten, terwijl openstaande projecten altijd inzichtelijk blijven.
  - Betreft: `gui/panels/database_panel.py`


### Added
- **32-bit .exe met icoon**
  - Een 32-bit uitvoerbaar bestand (`.exe`) is gecreëerd met PyInstaller.
  - Alle vereiste dependencies uit `requirements.txt` zijn inbegrepen.
  - Het applicatie-icoon (`ico.png`) is toegevoegd aan het uitvoerbare bestand.
  - De build is uitgevoerd met de `BarcodeMatch.spec` configuratie om een `x86` architectuur te garanderen.

## [Nog Niet Uitgebracht] - 2025-06-17

### Added
- **32-bit Applicatieversie**
  - Een 32-bit versie van de applicatie is nu beschikbaar. De build-configuratie is bijgewerkt om `x86` als doelarchitectuur te specificeren, wat compatibiliteit met oudere systemen garandeert.

## [Nog Niet Uitgebracht] - 2025-06-13

### Changed
- **Scannerpaneel: Verbeterde "_REP_" Projectcode Logica**
  - De projectcode-extractie uit Excel-bestandsnamen is verbeterd om dynamisch "_REP" projectcodes te herkennen.
  - Ondersteunt nu zowel "_REP_" als "_REP" patronen (hoofdletterongevoelig).
  - Wanneer een bestandsnaam deze patronen bevat, wordt automatisch "_REP" toegevoegd aan de geëxtraheerde projectcode (bijv. "MO07544" wordt "MO07544_REP").
  - Dit zorgt voor consistente behandeling van _REP_ projecten in database logging en e-mailnotificaties.
  - Betreft: `gui/panels/scanner_panel.py`

### Added
- **Verbeterde Opstartprocedure met Achtergrond Threading**
  - Applicatie-initialisatie verplaatst naar achtergrondthread voor snellere startup.
  - Lazy loading van panelen - panelen worden alleen gemaakt wanneer nodig.
  - Verbeterd splash screen met voortgangsindicatie tijdens laden.
  - Kritieke panelen (Scanner, Database) worden vooraf geladen in achtergrond.
  - Nieuwe `startup_utils.py` module voor herbruikbare startup management.
  - Betreft: `gui/app.py`, `gui/splashscreen.py`, `startup_utils.py`

## [Nog Niet Uitgebracht] - 2025-06-10

### Changed
- **Importpaneel: Item-formaat voor Gannomat-scans**
    - Het itemformaat voor Gannomat-scans is gewijzigd naar `{bestandsnaam}:{programmanummer}` (bijv. `0520_MO07922_TV-wand_(1-5):OW_04BC1`).
    - De resultatenweergave toont nu alleen de samengestelde itemnaam voor een duidelijkere interface.
- **Scannerpaneel: Uitlijning Statuskolom**
    - De kolom 'Status' in de treeview voor scangegevens is nu rechts uitgelijnd voor betere leesbaarheid.

### Added
- **Scannerpaneel: Formaat Wijzigbare Panelen**
    - De 'Scangegevens' (resultatenlijst) en 'Logboek' (logviewer) bevinden zich nu in een paneel waarvan het formaat kan worden aangepast, zodat de gebruiker de toegewezen ruimte verticaal kan aanpassen.

### Gewijzigd
- `scanner_panel.py`: De `build_tab` methode is gerefactord om een `ttk.PanedWindow` te gebruiken voor de hoofdinhoudsgebieden.

### Opgelost
- **Scannerpaneel: Voltooiingsacties (Database/E-mail) mislukten**
  - Een bug verholpen waarbij de database- en e-mailfuncties niet werden uitgevoerd nadat alle items waren gescand. De logica is gecorrigeerd zodat voltooiingsacties nu correct worden uitgevoerd, onafhankelijk van de archiveringsinstelling.
- **Scannerpaneel: Laden van Status**
    - Een probleem verholpen waarbij itemstatussen (bijv. 'OK') uit `_updated.xlsx` bestanden niet correct werden gelezen en toegepast op de treeview bij het opstarten. De treeview geeft nu de opgeslagen statussen correct weer bij het laden van een bestand.
- **Importpaneel: Crash bij Scannen Tussen Schijven**
    - Een crash verholpen in het Importpaneel die optrad wanneer de geselecteerde scanmap (bijv. op schijf `Y:`) en de basismap (bijv. op schijf `C:`) zich op verschillende schijven bevonden. De applicatie handelt deze situatie nu correct af zonder fouten.

### Gewijzigd
- In het Instellingen-paneel is de kop "Instellingen" verwijderd en zijn de beschrijvingen van de instellingen veranderd in tooltips voor een schonere interface.

### Toegevoegd
- Instellingen paneel toegevoegd met een bijbehorende menuknop.
- **Scannerpaneel: Automatische Archivering**
  - Een nieuwe instelling toegevoegd in het Instellingen-paneel om Excel-bestanden (`.xlsx` en `_updated.xlsx`) automatisch te archiveren.
  - Wanneer deze optie is ingeschakeld en alle items in een lijst als 'OK' zijn gemarkeerd, worden de bestanden verplaatst naar een nieuwe 'Archief'-map in dezelfde directory.
- **Scannerpaneel: Persistente Statusupdates**
    - Wanneer de status van een item verandert (gescand, gemarkeerd als OK/Niet OK), wordt de volledige lijst opgeslagen in een `_updated.xlsx` bestand (bijv. `originele_naam_updated.xlsx`).
    - Bij het laden van een Excel-bestand (via Bladeren of bij opstarten vanuit `last_excel_file`), controleert het systeem nu automatisch op een `_updated.xlsx` versie en laadt deze indien aanwezig. Anders wordt het originele bestand geladen.
    - De origineel geselecteerde bestandsnaam wordt bewaard ter referentie, zodat `_updated` bestanden altijd zijn afgeleid van de basisnaam.
- **Scannerpaneel: Database-integratie**
    - Wanneer alle items in een scanlijst als 'OK' zijn gemarkeerd en databaselogging is ingeschakeld in `DatabasePanel`, wordt een 'GESLOTEN' gebeurtenis voor het project gelogd.
    - De projectnaam wordt afgeleid van de geladen Excel-bestandsnaam (bijv. `MijnProject.xlsx` wordt `MijnProject`).
- **Scannerpaneel: E-mailnotificaties**
    - Wanneer alle items in een scanlijst als 'OK' zijn gemarkeerd en e-mailnotificaties zijn ingeschakeld en ingesteld op 'per_scan' modus in `EmailPanel`, wordt een e-mail verzonden.
    - De e-mail bevat de projectnaam (afgeleid van Excel-bestandsnaam) en voegt het corresponderende `_updated.xlsx` bestand als bijlage toe.
- **E-mailpaneel: Volledige E-mailfunctionaliteit**
    - Robuuste e-mailverzending via SMTP geïmplementeerd, inclusief ondersteuning voor TLS.
    - `send_project_complete_email(project_name, excel_path)` methode toegevoegd voor gebruik door andere panelen.
    - De knop "Verzend testmail" is nu functioneel en verstuurt een testmail met de geconfigureerde instellingen.
    - Configuratie voor afzender, ontvanger, SMTP-server/poort, gebruiker/wachtwoord, inschakeloptie en verzendmodus (per_scan/dagelijks) wordt beheerd en opgeslagen.
- **Importpaneel: Gestandaardiseerde Excel-uitvoer**
    - De Excel-uitvoerkolom gestandaardiseerd naar "Item" voor zowel Opus- als Gannomat-modi in `import_panel.py`.

### Gewijzigd
- `scanner_panel.py`: `_load_excel_data` aangepast om `_updated.xlsx` bestanden prioriteit te geven.
- `scanner_panel.py`: `_check_barcode`, `_mark_item_ok`, `_mark_item_not_ok` aangepast om opslaan naar `_updated.xlsx` te activeren.
- `scanner_panel.py`: `_all_items_ok_check` aangepast om methoden voor databaselogging en e-mailnotificatie aan te roepen.
- `email_panel.py`: Herzien om volledige SMTP e-mailverzendmogelijkheden op te nemen.
