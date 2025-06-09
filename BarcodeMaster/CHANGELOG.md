# BarcodeMaster Wijzigingslogboek

Alle belangrijke wijzigingen, verbeteringen en bugfixes voor BarcodeMaster worden hier bijgehouden. Elke vermelding bevat de datum, een samenvatting van de wijziging en de betreffende bestanden of modules.

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
