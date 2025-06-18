# Hops File Logger

## Overzicht
De Hops File Logger is een Windows-programma dat automatisch bestanden bijhoudt, logt en rapporten genereert. Het programma draait als een tray-applicatie (icoon in de systeemtray) en biedt een eenvoudige manier om handmatig items toe te voegen via een venster.

## Functionaliteit
- **Automatisch loggen:** Houdt wijzigingen en nieuwe bestanden bij volgens de ingestelde categorieën.
- **Tray-icoon:** Draait op de achtergrond; via het tray-menu kun je snel acties uitvoeren.
- **Handmatig toevoegen:** Voeg eenvoudig handmatig items toe via het menuoptie 'Handmatig toevoegen'.
- **Rapportage:** Genereert automatisch Excel-rapporten per week en maand, inclusief grafieken.

## Gebruik
1. Start het programma (`tray_logger.exe`).
2. Er verschijnt een icoon in de systeemtray (rechtsonder bij de klok).
3. Klik met de rechtermuisknop op het tray-icoon voor het menu:
   - **Handmatig toevoegen:** Open een venster om handmatig een item in te voeren.
   - **Exit:** Sluit het programma.
4. De logger werkt automatisch op de achtergrond en maakt rapporten aan.

## Installatie
1. Download of bouw het programma als één .exe-bestand (zie onder).
2. Plaats `categories.json` en `.seen_entries.json` in dezelfde map als de .exe.
3. Start `tray_logger.exe`.

### Zelf bouwen (optioneel)
Gebruik PyInstaller om het programma te bundelen:
```sh
python -m PyInstaller --onefile --windowed --add-data "categories.json;." --add-data ".seen_entries.json;." tray_logger.py
```
Het resultaat staat in de map `dist`.

## Rapporten
- Wekelijkse en maandelijkse rapporten worden automatisch opgeslagen in de submappen:
  - `Week Raporten`
  - `Maand`
- De rapporten zijn Excel-bestanden met grafieken per categorie en per dag/uur.

## Vereisten
- Windows 10/11
- Python 3.8+ (alleen nodig als je zelf wilt bouwen)
- Vereiste Python-pakketten: `openpyxl`, `pystray`, `pillow`

## Problemen?
- Controleer of alle benodigde bestanden in dezelfde map staan als de .exe.
- Kijk voor foutmeldingen in de console of logbestanden.
- Neem contact op met de ontwikkelaar bij aanhoudende problemen.
