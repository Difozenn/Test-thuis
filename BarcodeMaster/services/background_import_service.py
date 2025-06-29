"""
Background Import Service voor BarcodeMaster
Automatische monitoring en verwerking van OPUS en GANNOMAT bestanden
"""

import os
import sqlite3
import json
import logging
import requests
import re
from datetime import datetime
import traceback
import threading
import time
import random
import pandas as pd
import pyodbc

from config_utils import get_config
from path_utils import get_writable_path

class BackgroundImportService:
    _stats_lock = threading.Lock() # Class level lock for stats
    """Service voor automatische import getriggerd door OPEN events."""
    
    def __init__(self, log_callback=None):
        self.log_callback = log_callback
        self.logger = None # Initialized in _setup_logging
        
        # Configuration holders
        self.scanner_users = []
        self.scanner_user_paths = {}
        self.scanner_user_logic_active = {}
        self.scanner_user_to_processing_type_map = {} # New map

        # Statistics tracking
        self.stats = {
            'hops_imports_triggered': 0,  # Changed from opus_imports_triggered to reflect processing type
            'mdb_imports_triggered': 0,   # Changed from gannomat_imports_triggered to reflect processing type
            'total_imports_triggered': 0
        }
        
        self.load_config() # Load initial configuration
        self._setup_logging() # Setup logger
        
    def _setup_logging(self):
        """Setup logging voor de service."""
        # Use writable path for logs
        log_dir = get_writable_path('logs')
        
        os.makedirs(log_dir, exist_ok=True)
        
        log_file = os.path.join(log_dir, 'background_import_service.log')
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        
        self.logger = logging.getLogger(__name__)
        
    def load_config(self):
        """Laad configuratie van config file."""
        try:
            config = get_config()
            
            # Load ScannerPanel specific configurations for user monitoring
            self.scanner_users = config.get('scanner_panel_open_event_users', ['GANNOMAT', 'OPUS']) # Default if not set
            self.scanner_user_paths = config.get('scanner_panel_open_event_user_paths', {})
            self.scanner_user_logic_active = config.get('scanner_panel_open_event_user_logic_active', {})
            self.scanner_user_to_processing_type_map = config.get('scanner_user_to_processing_type_map', {}) # Load the new map
            
            if self.logger: # Logger might not be set up on first call from __init__
                self.logger.info("Configuratie succesvol geladen.")
                self.logger.debug(f"Scanner users: {self.scanner_users}")
                self.logger.debug(f"Scanner user paths: {self.scanner_user_paths}")
                self.logger.debug(f"Scanner user logic active: {self.scanner_user_logic_active}")
                self.logger.debug(f"Scanner user to processing type map: {self.scanner_user_to_processing_type_map}")
                
        except Exception as e:
            if self.logger:
                self.logger.error(f"Fout bij laden configuratie: {e}")
            else:
                print(f"ERROR during initial config load: {e}")
            # Reset to safe defaults
            self.scanner_users = []
            self.scanner_user_paths = {}
            self.scanner_user_logic_active = {}
            self.scanner_user_to_processing_type_map = {}
            
    def is_enabled(self):
        """Controleer of de automatische import functionaliteit is ingeschakeld."""
        return True # Service is always ready to check user-specific logic

    def get_status(self):
        """Krijg huidige status van de import functionaliteit."""
        hops_users = []
        mdb_users = []
        
        for user in self.scanner_users:
            if (self.scanner_user_logic_active.get(user, False) and 
                bool(self.scanner_user_paths.get(user))):
                processing_type = self.scanner_user_to_processing_type_map.get(user)
                if processing_type == 'HOPS_PROCESSING':
                    hops_users.append(user)
                elif processing_type == 'MDB_PROCESSING':
                    mdb_users.append(user)

        return {
            'service_enabled': True,
            'hops_processing_users': hops_users,
            'mdb_processing_users': mdb_users,
            'hops_imports_triggered': self.stats['hops_imports_triggered'],
            'mdb_imports_triggered': self.stats['mdb_imports_triggered'],
            'total_imports_triggered': self.stats['total_imports_triggered']
        }
        
    def trigger_import_for_event(self, user_type, project_code, event_details, timestamp):
        """Verwerk een OPEN event en trigger automatische import indien nodig."""
        self.load_config() # Ensure config is up-to-date

        self._log(f"Event ontvangen: User={user_type}, Project={project_code}. Controleren voor import...")
        
        processing_type = self.scanner_user_to_processing_type_map.get(user_type)

        if not self.scanner_user_logic_active.get(user_type, False):
            self._log(f"{user_type} import overgeslagen: logica niet actief voor deze gebruiker.")
            return

        if processing_type == 'GEEN_PROCESSING':
            self._log(f"'{user_type}' is geconfigureerd voor 'GEEN_PROCESSING'. Import overgeslagen.")
            return

        user_specific_path = self.scanner_user_paths.get(user_type)
        if not user_specific_path or not os.path.isdir(user_specific_path):
            self._log(f"{user_type} import overgeslagen: pad niet ingesteld of ongeldig ('{user_specific_path}').")
            return

        if processing_type == 'HOPS_PROCESSING':
            # The project_code passed in is now the one to use for matching,
            # whether it's a base code or a full REP project name.
            code_to_match = project_code
            self._log(f"HOPS_PROCESSING voor user '{user_type}': Using '{code_to_match}' for directory matching.")

            if not code_to_match:
                self._log("Could not determine a project code to match against. Aborting HOPS_PROCESSING.")
                return

            match_found = False
            try:
                is_rep_project_code = bool(re.search(r'_REP_?', code_to_match, re.IGNORECASE))
                for item_name in os.listdir(user_specific_path):
                    item_path = os.path.join(user_specific_path, item_name)
                    if os.path.isdir(item_path):
                        match_condition_met = False
                        if is_rep_project_code:
                            self._log(f"  [DEBUG HOPS] Comparing dir: '{item_name}' (Upper: '{item_name.upper()}') with code_to_match: '{code_to_match}' (Upper: '{code_to_match.upper()}')")
                            ends_with_result = item_name.upper().endswith(code_to_match.upper())
                            self._log(f"  [DEBUG HOPS] Does '{item_name.upper()}' end with '{code_to_match.upper()}'? Result: {ends_with_result}")
                            if ends_with_result:
                                match_condition_met = True
                                self._log(f"HOPS_PROCESSING (REP match) (voor user '{user_type}') wordt gestart voor gevonden map: {item_path}")
                        else: # Not a REP variant, use endswith for robustness with prefixes
                            self._log(f"  [DEBUG HOPS] Comparing dir: '{item_name}' (Upper: '{item_name.upper()}') with code_to_match: '{code_to_match}' (Upper: '{code_to_match.upper()}')")
                            ends_with_result = item_name.upper().endswith(code_to_match.upper())
                            self._log(f"  [DEBUG HOPS] Does '{item_name.upper()}' end with '{code_to_match.upper()}'? Result: {ends_with_result}")
                            if ends_with_result:
                                match_condition_met = True
                                self._log(f"HOPS_PROCESSING (EndsWith match) (voor user '{user_type}') wordt gestart voor gevonden map: {item_path}")
                        
                        if match_condition_met:
                            # Pass the actual user_type (e.g., "KL GANNOMAT") to preserve it in logging
                            thread = threading.Thread(target=self._execute_hops_import_with_stats, args=(user_type, project_code, event_details, timestamp, item_path))
                            thread.start()
                            match_found = True
                            break  # Stop after finding the first match
            except Exception as e:
                self._log(f"Fout bij het zoeken naar HOPS map: {e}")

            if not match_found:
                self._log(f"HOPS_PROCESSING (voor user '{user_type}') overgeslagen: geen overeenkomende projectmap gevonden in '{user_specific_path}' voor project '{code_to_match}'.")
                
        elif processing_type == 'MDB_PROCESSING':
            self._log(f"MDB_PROCESSING voor user '{user_type}' wordt gestart (in achtergrond thread). Pad: {user_specific_path}")
            # Pass the actual user_type (e.g., "KL GANNOMAT") to preserve it in logging
            thread = threading.Thread(target=self._execute_mdb_import_with_stats, args=(user_type, project_code, event_details, timestamp, user_specific_path))
            thread.start()
        
        elif processing_type:
            self._log(f"Onbekend processing_type '{processing_type}' voor gebruiker '{user_type}'.")
        else:
            self._log(f"Geen processing_type geconfigureerd voor gebruiker '{user_type}'.")

    def process_scan_for_open_event_async(self, project_code_to_log, base_project_code, scanned_code, current_user_scanner, api_url, config_data):
        """Processes the OPEN scan event for other users in a background thread."""
        thread = threading.Thread(
            target=self._process_scan_for_open_event_task,
            args=(
                project_code_to_log,
                base_project_code,
                scanned_code,
                current_user_scanner,
                api_url,
                config_data
            )
        )
        thread.daemon = True # Ensure thread doesn't block program exit
        thread.start()
        self._log(f"Background task started for OPEN event: {project_code_to_log}")

    def _process_scan_for_open_event_task(self, project_code_to_log, base_project_code, scanned_code, current_user_scanner, api_url, config_data):
        """Task run in a separate thread to handle OPEN event logic for other users."""
        try:
            self._log(f"[BG_TASK] Processing OPEN for {project_code_to_log}, scanned by {current_user_scanner}.")
            open_users = config_data.get('scanner_panel_open_event_users', [])
            user_logic_active_states = config_data.get('scanner_panel_open_event_user_logic_active', {})
            user_paths_map = config_data.get('scanner_panel_open_event_user_paths', {})

            for user in open_users:
                if user == current_user_scanner:
                    continue # Skip the user who initiated the scan

                if user_logic_active_states.get(user, True): # Default to True if not specified
                    user_dir = user_paths_map.get(user)
                    match_found_for_this_user = False
                    
                    if user_dir and os.path.isdir(user_dir):
                        self._log(f"[BG_TASK] Checking dir '{user_dir}' for user '{user}' for project '{project_code_to_log}'.")
                        try:
                            # Logic adapted from scanner_panel.py lines 628-643
                            if base_project_code and base_project_code.strip():
                                for item_name in os.listdir(user_dir):
                                    item_base_name, _ = os.path.splitext(item_name)
                                    is_rep_scan_for_item = bool(re.search(r'_REP_?', project_code_to_log, re.IGNORECASE))
                                    
                                    if is_rep_scan_for_item:
                                        if item_base_name.upper().endswith(project_code_to_log.upper()):
                                            match_found_for_this_user = True
                                            break
                                    else:
                                        if item_base_name.upper().endswith(project_code_to_log.upper()) and not re.search(r'_REP_?', item_name, re.IGNORECASE):
                                            match_found_for_this_user = True
                                            break
                        except OSError as e_os:
                            self._log(f"[BG_TASK_ERR] Error accessing dir {user_dir} for {user}: {e_os}")
                            if self.log_callback:
                                self.log_callback(f"BACKGROUND_IO_ERROR:{project_code_to_log}:{user}:Error accessing dir {user_dir}: {e_os}")
                            continue # Skip to next user
                    if match_found_for_this_user:
                        self._log(f"[BG_TASK] Match found for '{project_code_to_log}' in '{user_dir}' for user '{user}'. Posting OPEN.")

                        # Introduce a random delay to prevent database write collisions.
                        delay = random.uniform(0.2, 1.5)
                        self._log(f"[BG_TASK] Waiting for {delay:.2f}s before posting OPEN for {user}.")
                        time.sleep(delay)

                        data_open = {
                            'event': 'OPEN',
                            'details': f"Auto-detected from {current_user_scanner}'s scan of {scanned_code}",
                            'project': project_code_to_log,
                            'base_mo_code': base_project_code,
                            'is_rep_variant': bool(re.search(r'_REP_?', project_code_to_log, re.IGNORECASE)),
                            'user': user  # This preserves the actual user name (e.g., "KL GANNOMAT")
                        }
                        try:
                            resp_open = requests.post(api_url, json=data_open, timeout=10)
                            if resp_open.ok:
                                self._log(f"[BG_TASK] Successfully posted OPEN for {project_code_to_log} for user {user}.")
                                if self.log_callback:
                                    self.log_callback(f"BACKGROUND_PROJECT_OPENED:{project_code_to_log}:{user}")
                            else:
                                error_msg = resp_open.text
                                self._log(f"[BG_TASK_ERR] API Error opening project {project_code_to_log} for {user}: {resp_open.status_code} - {error_msg}")
                                if self.log_callback:
                                    self.log_callback(f"BACKGROUND_PROJECT_OPEN_FAILED:{project_code_to_log}:{user}:{resp_open.status_code} - {error_msg}")
                        except requests.exceptions.RequestException as e_req:
                            self._log(f"[BG_TASK_ERR] Network Error opening project {project_code_to_log} for {user}: {e_req}")
                            if self.log_callback:
                                self.log_callback(f"BACKGROUND_PROJECT_OPEN_FAILED:{project_code_to_log}:{user}:Network Error - {e_req}")
                        except Exception as e_gen_api:
                            self._log(f"[BG_TASK_ERR] Generic API Error for {project_code_to_log}, user {user}: {e_gen_api}\n{traceback.format_exc()}")
                            if self.log_callback:
                                self.log_callback(f"BACKGROUND_PROJECT_OPEN_FAILED:{project_code_to_log}:{user}:Generic API Error - {e_gen_api}")
                    else:
                        self._log(f"[BG_TASK] No match for '{project_code_to_log}' in '{user_dir}' for user '{user}'.")
                else:
                    self._log(f"[BG_TASK] Logic inactive for user '{user}'. Skipping OPEN event processing.")
            
            self._log(f"[BG_TASK] Finished processing OPEN for {project_code_to_log}.")
            if self.log_callback:
                self.log_callback(f"BACKGROUND_PROCESSING_COMPLETE:{project_code_to_log}")

        except Exception as e_task:
            self._log(f"[BG_TASK_FATAL_ERR] Unhandled exception in _process_scan_for_open_event_task for {project_code_to_log}: {e_task}\n{traceback.format_exc()}")
            if self.log_callback:
                self.log_callback(f"BACKGROUND_FATAL_ERROR:{project_code_to_log}:Error - {e_task}")

    def _execute_hops_import_with_stats(self, user_name, project_code, event_details, timestamp, specific_hops_subfolder_path):
        """Execute HOPS processing and update statistics."""
        try:
            self._trigger_hops_import(user_name, project_code, event_details, timestamp, specific_hops_subfolder_path)
            with BackgroundImportService._stats_lock:
                self.stats['hops_imports_triggered'] += 1
                self.stats['total_imports_triggered'] += 1
            self._log(f"HOPS import thread voltooid voor user '{user_name}'. Totaal HOPS: {self.stats['hops_imports_triggered']}, Totaal: {self.stats['total_imports_triggered']}")
        except Exception as e:
            self.logger.error(f"Fout in HOPS import thread voor user '{user_name}': {e}")
            self._log(f"Fout in HOPS import thread voor user '{user_name}': {e}")

    def _execute_mdb_import_with_stats(self, user_name, project_code, event_details, timestamp, mdb_path):
        """Execute MDB processing and update statistics."""
        try:
            self._trigger_mdb_import(user_name, project_code, event_details, timestamp, mdb_path)
            with BackgroundImportService._stats_lock:
                self.stats['mdb_imports_triggered'] += 1
                self.stats['total_imports_triggered'] += 1
            self._log(f"MDB import thread voltooid voor user '{user_name}'. Totaal MDB: {self.stats['mdb_imports_triggered']}, Totaal: {self.stats['total_imports_triggered']}")
        except Exception as e:
            self.logger.error(f"Fout in MDB import thread voor user '{user_name}': {e}")
            self._log(f"Fout in MDB import thread voor user '{user_name}': {e}")

    def _get_base_code(self, project_code):
        """Extracts the base project code (e.g., MO12345 or 123456) from a full project code string."""
        import re
        # Prioritize MOxxxxx pattern
        mo_match = re.search(r'(MO\d{4,6})', project_code)
        if mo_match:
            return mo_match.group(0)
        # Fallback for ACCURA style 5-6 digit codes
        accura_match = re.search(r'(\d{5,6})', project_code)
        if accura_match:
            return accura_match.group(0)
        return ""

    def _trigger_hops_import(self, user_name, project_event_code, details, timestamp, hops_scan_path):
        """Trigger automatische HOPS import en Excel generatie voor .hop/.hops bestanden in de gespecificeerde map."""
        self._log(f"HOPS import gestart voor user '{user_name}', project context: {project_event_code} in map: {hops_scan_path}")

        if not hops_scan_path or not os.path.isdir(hops_scan_path):
            self._log(f"HOPS directory niet gevonden of ongeldig: {hops_scan_path}")
            self.logger.warning(f"HOPS directory niet gevonden of ongeldig: {hops_scan_path}")
            return # Crucial return if path is invalid

        try:
            collected_files = self._collect_hops_files_for_report(hops_scan_path)

            if collected_files:
                self._log(f"{len(collected_files)} HOPS (.hop/.hops) bestanden gevonden in '{hops_scan_path}' voor Excel rapportage.")
                self._create_hops_excel_report(user_name, collected_files, hops_scan_path, project_event_code)
            else:
                self._log(f"Geen .hop/.hops bestanden gevonden in HOPS map '{hops_scan_path}' voor Excel rapportage.")

        except Exception as e:
            self.logger.error(f"Algemene fout tijdens HOPS import/Excel generatie voor pad {hops_scan_path} (project context: {project_event_code}): {e}")
            self._log(f"Algemene fout HOPS import: {str(e)}")

    def _collect_hops_files_for_report(self, hops_scan_path):
        """
        Collects all .hop/.hops files from the given path and its subdirectories,
        returning a list of dicts with 'Item' key holding the relative path.
        """
        found_files_data = []
        try:
            for root, _, filenames in os.walk(hops_scan_path):
                for filename in filenames:
                    if filename.lower().endswith(('.hop', '.hops')):
                        full_path = os.path.join(root, filename)
                        # Store the full absolute path instead of relative path
                        found_files_data.append({'Item': full_path})
            if found_files_data:
                self._log(f"{len(found_files_data)} .hop/.hops bestanden verzameld uit '{hops_scan_path}'.")
            else:
                self._log(f"Geen .hop/.hops bestanden gevonden in '{hops_scan_path}'.")
        except Exception as e:
            self._log(f"Fout bij verzamelen HOPS bestanden uit '{hops_scan_path}': {e}")
            self.logger.error(f"Error collecting HOPS files from '{hops_scan_path}': {e}")
        return found_files_data

    def _create_hops_excel_report(self, user_name, collected_files, hops_scan_path, project_code):
        """Genereert een Excel-rapport van de verzamelde HOPS-bestanden."""
        if not collected_files:
            self._log("Geen HOPS-bestanden verzameld om rapport te genereren.")
            return

        try:
            # Maak een DataFrame van de bestandsnamen
            df_data = [{'Item': os.path.basename(f['Item'])} for f in collected_files]
            df = pd.DataFrame(df_data)
            df['Status'] = ''  # Voeg een lege statuskolom toe

            # Bepaal het pad en de naam voor het Excel-bestand
            project_name_for_file = os.path.basename(os.path.normpath(hops_scan_path))
            excel_path = os.path.join(hops_scan_path, f"{project_name_for_file}.xlsx")

            # Schrijf naar Excel
            df.to_excel(excel_path, index=False)
            self._log(f"HOPS Excel rapport succesvol opgeslagen: {excel_path}")

            # Update the OPEN event with the Excel file path
            self._update_open_event_with_file_path(
                user_name,
                project_code,  # Use the actual project code from the OPEN event
                excel_path
            )

        except ImportError:
            self._log("Pandas is niet geïnstalleerd. Kan geen Excel rapport genereren.")
            self.logger.error("Pandas is niet geïnstalleerd. Kan geen Excel rapport genereren.")
        except Exception as e:
            self._log(f"Fout bij het maken van HOPS Excel-rapport voor {hops_scan_path}: {e}")
            self.logger.error(f"Fout bij het maken van HOPS Excel-rapport voor {hops_scan_path}: {e}")

    def _trigger_mdb_import(self, user_name, project_event_code, details, timestamp, mdb_scan_path):
        """Trigger automatische MDB import en Excel generatie voor .mdb/.accdb bestanden die overeenkomen met de projectcode."""
        self._log(f"MDB import gestart voor user '{user_name}', project context: {project_event_code} in map: {mdb_scan_path}")

        if not mdb_scan_path or not os.path.isdir(mdb_scan_path):
            self._log(f"MDB directory niet gevonden of ongeldig: {mdb_scan_path}")
            self.logger.warning(f"MDB directory niet gevonden of ongeldig: {mdb_scan_path}")
            return

        processed_files_count = 0
        excel_reports_generated = 0
        match_found = False
        try:
            is_rep_project_code = bool(re.search(r'_REP_?', project_event_code, re.IGNORECASE))
            for filename in os.listdir(mdb_scan_path):
                file_basename, file_ext = os.path.splitext(filename)
                if file_ext.lower() in ('.mdb', '.accdb'):
                    match_condition_met = False
                    db_file_path = "" # Define here to be accessible after condition

                    if is_rep_project_code:
                        self._log(f"  [DEBUG MDB] Comparing file_basename: '{file_basename}' (Upper: '{file_basename.upper()}') with project_event_code: '{project_event_code}' (Upper: '{project_event_code.upper()}')")
                        ends_with_result = file_basename.upper().endswith(project_event_code.upper())
                        self._log(f"  [DEBUG MDB] Does '{file_basename.upper()}' end with '{project_event_code.upper()}'? Result: {ends_with_result}")
                        if ends_with_result:
                            match_condition_met = True
                            db_file_path = os.path.join(mdb_scan_path, filename)
                            self._log(f"Overeenkomend MDB bestand (REP match) gevonden: {db_file_path}. Verwerken...")
                    else: # Not a REP variant, use endswith for robustness with prefixes
                        self._log(f"  [DEBUG MDB] Comparing file_basename: '{file_basename}' (Upper: '{file_basename.upper()}') with project_event_code: '{project_event_code}' (Upper: '{project_event_code.upper()}')")
                        ends_with_result = file_basename.upper().endswith(project_event_code.upper())
                        self._log(f"  [DEBUG MDB] Does '{file_basename.upper()}' end with '{project_event_code.upper()}'? Result: {ends_with_result}")
                        if ends_with_result:
                            match_condition_met = True
                            db_file_path = os.path.join(mdb_scan_path, filename)
                            self._log(f"Overeenkomend MDB bestand (EndsWith match) gevonden: {db_file_path}. Verwerken...")
                    
                    if match_condition_met:
                        match_found = True
                        extracted_data = self._extract_raw_mdb_data_from_db(db_file_path)
                        
                        if extracted_data:
                            self._create_mdb_excel_report(user_name, extracted_data, db_file_path, project_event_code)
                            excel_reports_generated += 1
                            self._log(f"Excel rapport gegenereerd voor {filename}.")
                        else:
                            self._log(f"Geen data geëxtraheerd uit {filename} voor Excel rapportage.")
                        processed_files_count += 1
                        break # Process only the first matched file
            
            if match_found and processed_files_count > 0:
                self._log(f"{processed_files_count} MDB bestand(en) verwerkt. {excel_reports_generated} Excel rapporten gegenereerd voor project '{project_event_code}'.")
            elif not match_found:
                self._log(f"Geen overeenkomend .mdb/.accdb bestand gevonden in '{mdb_scan_path}' voor project '{project_event_code}'.")

        except Exception as e:
            self.logger.error(f"Algemene fout tijdens MDB import voor pad {mdb_scan_path} (project: {project_event_code}): {e}")
            self._log(f"Algemene fout MDB import (project: {project_event_code}): {str(e)}")
        
    def _extract_raw_mdb_data_from_db(self, db_path):
        """
        Extracts all ProgramNumbers from a MDB/ACCDB file,
        formatted for Excel generation, similar to BarcodeMatch.
        Returns a list of dicts: [{'MDB File': 'name.mdb', 'Item': 'name:PN123'}, ...]
        """
        results = []
        mdb_basename = os.path.basename(db_path)
        mdb_filename_without_extension = os.path.splitext(mdb_basename)[0]
        
        try:
            # pyodbc should be imported at the top of the file
            pass 
        except ImportError:
            self._log("pyodbc is niet geïnstalleerd. Kan MDB-bestanden niet verwerken voor Excel.")
            self.logger.warning("pyodbc is niet geïnstalleerd. Kan MDB-bestanden niet verwerken voor Excel.")
            return results

        try:
            conn_str = (
                r'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};'
                f'DBQ={db_path};'
            )
            with pyodbc.connect(conn_str, autocommit=True) as conn:
                cursor = conn.cursor()
                tables_info = cursor.tables(tableType='TABLE')
                db_tables = [tbl_info.table_name for tbl_info in tables_info]
                
                program_table = None
                fallback_table = None

                for table_name in db_tables:
                    columns = [column.column_name for column in cursor.columns(table=table_name)]
                    if table_name.lower() == 'program' and 'ProgramNumber' in columns:
                        program_table = table_name
                        break
                    elif not fallback_table and 'ProgramNumber' in columns:
                        fallback_table = table_name
                
                target_table = program_table if program_table else fallback_table

                if target_table:
                    self._log(f"Querying 'ProgramNumber' from table '{target_table}' in {mdb_basename}")
                    cursor.execute(f'SELECT ProgramNumber FROM [{target_table}]')
                    for row in cursor.fetchall():
                        program_number_str = str(row.ProgramNumber) if row.ProgramNumber is not None else "PN_NULL"
                        item_name = f"{mdb_filename_without_extension}:{program_number_str}"
                        results.append({'MDB File': mdb_basename, 'Item': item_name})
                else:
                    self._log(f"Geen geschikte tabel (zoals 'Program' met 'ProgramNumber') gevonden in {mdb_basename}.")
                    self.logger.info(f"No suitable table (e.g., 'Program' with 'ProgramNumber') found in {mdb_basename}.")
                    
        except pyodbc.Error as ex:
            sqlstate = ex.args[0]
            self._log(f"PyODBC fout bij verwerken van {mdb_basename}: {sqlstate} - {str(ex)}")
            self.logger.error(f"PyODBC error processing {mdb_basename}: {sqlstate} - {str(ex)}")
        except Exception as e:
            self._log(f"Algemene fout bij verwerken van {mdb_basename}: {str(e)}")
            self.logger.error(f"General error processing {mdb_basename}: {str(e)}")
            
        return results

    def _create_mdb_excel_report(self, user_name, report_data, db_path, project_code):
        """
        Creates an Excel file from the MDB data, similar to BarcodeMatch.
        report_data is a list of dicts, each with 'Item' and 'MDB File' keys.
        db_path is the full path to the source MDB/ACCDB file.
        """
        mdb_basename = os.path.basename(db_path)
        try:
            # pandas should be imported at the top of the file
            pass
        except ImportError:
            self._log("Pandas is niet geïnstalleerd. Kan geen Excel rapport genereren.")
            self.logger.error("Pandas is niet geïnstalleerd. Kan geen Excel rapport genereren.")
            return

        if not report_data:
            self._log(f"Geen data om op te slaan in Excel voor {mdb_basename}.")
            return

        try:
            df = pd.DataFrame(report_data)
            
            if 'Item' in df.columns:
                df_export = df[['Item']].copy()
                df_export['Status'] = ''
            else:
                self._log(f"Kolom 'Item' niet gevonden in data voor Excel export voor {mdb_basename}. Exporteren ruwe data.")
                self.logger.warning(f"Column 'Item' not found in data for Excel export for {mdb_basename}. Exporting raw data.")
                df_export = df.copy()
                if 'Status' not in df_export.columns:
                    df_export['Status'] = ''

            export_dir = os.path.dirname(db_path)
            base_name = os.path.splitext(mdb_basename)[0]
            excel_path = os.path.join(export_dir, f"{base_name}.xlsx")

            df_export.to_excel(excel_path, index=False)
            self._log(f"MDB Excel rapport succesvol opgeslagen: {excel_path}")
            self.logger.info(f"MDB Excel report successfully saved: {excel_path}")
            
            # Update the OPEN event with the Excel file path
            self._update_open_event_with_file_path(
                user_name,
                project_code,  # Use the actual project code from the OPEN event
                excel_path
            )

        except Exception as e:
            self._log(f"Fout bij opslaan van MDB Excel rapport voor {mdb_basename}: {e}")
            self.logger.error(f"Error saving MDB Excel report for {mdb_basename}: {e}")

    def _update_open_event_with_file_path(self, user_name, project, file_path):
        """Update the existing OPEN event with the Excel file path instead of creating a new event."""
        try:
            config = get_config()
            # Ensure api_url is correctly retrieved
            api_url = config.get('api_url', '').rstrip('/')
            
            if not api_url:
                self._log("Geen API URL geconfigureerd voor event logging")
                return

            # Use the update endpoint
            update_url = api_url.replace('/log', '/update_file_path')
            
            data = {
                'project': project,
                'user': user_name,
                'file_path': file_path,
                'timestamp': datetime.now().isoformat()
            }

            response = requests.post(update_url, json=data, timeout=5)

            if response.ok:
                self._log(f"OPEN event updated with Excel path for: {user_name} - {project} at {file_path}")
            else:
                self._log(f"Fout bij updaten OPEN event met Excel path: HTTP {response.status_code} - {response.text}")

        except Exception as e:
            self.logger.error(f"Fout bij updaten OPEN event met Excel path: {e}")
            self._log(f"Fout bij API update (Excel path): {str(e)}")

    def _extract_project_code(self, code):
        """Extract project code met _REP_ handling (consistent met scanner panel)."""
        project_code = code  # Default to full code
        
        # Try to extract project code using standard pattern
        match = re.search(r'_([A-Z]{2}\d+)_', code)
        if match:
            project_code = match.group(1)
        
        # Dynamic logic for handling _REP_ project codes (case insensitive)
        code_upper = code.upper()
        if re.search(r'_REP_?', code, re.IGNORECASE):
            if not project_code.upper().endswith("_REP"):
                project_code = f"{project_code}_REP"
                
        return project_code
        
    def _log_import_event(self, user_type, project, details):
        """Log automatische import event naar API."""
        try:
            config = get_config()
            api_url = config.get('api_url', '').rstrip('/')
            
            if not api_url:
                self._log("Geen API URL geconfigureerd voor event logging")
                return
                
            data = {
                'event': 'AUTO_IMPORT',
                'details': details,
                'project': project,
                'user': user_type,
                'timestamp': datetime.now().isoformat()
            }
            
            response = requests.post(api_url, json=data, timeout=5)
            
            if response.ok:
                self._log(f"Import event gelogd naar API: {user_type} - {project}")
            else:
                self._log(f"Fout bij loggen import event: HTTP {response.status_code}")
                
        except Exception as e:
            self.logger.error(f"Fout bij loggen import event: {e}")
            self._log(f"Fout bij API logging: {str(e)}")

    def _log(self, message):
        """Log bericht naar file en callback."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {message}"
        
        self.logger.info(message)
        
        if self.log_callback:
            try:
                self.log_callback(message)
            except Exception as e:
                self.logger.error(f"Fout bij callback logging: {e}")