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
import PyPDF2
import pdfplumber

from config_utils import get_config
from path_utils import get_writable_path
from pdf_database_manager import PDFDatabaseManager

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
            'nesting_imports_triggered': 0,  # New stat for nesting processing
            'accura_imports_triggered': 0,  # New stat for accura processing
            'boere_imports_triggered': 0,  # New stat for boere processing
            'total_imports_triggered': 0
        }
        
        # Initialize PDF database manager
        self.pdf_db_manager = None
        
        self.load_config() # Load initial configuration
        self._setup_logging() # Setup logger
        
        # Initialize PDF database manager after logging is set up
        try:
            self.pdf_db_manager = PDFDatabaseManager(log_callback=self.log_callback)
            self._log("PDF database manager initialized successfully")
        except Exception as e:
            self._log(f"Failed to initialize PDF database manager: {e}")
            self.pdf_db_manager = None
        
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
        nesting_users = []
        accura_users = []
        boere_users = []
        
        for user in self.scanner_users:
            if (self.scanner_user_logic_active.get(user, False) and 
                bool(self.scanner_user_paths.get(user))):
                processing_type = self.scanner_user_to_processing_type_map.get(user)
                if processing_type == 'HOPS_PROCESSING':
                    hops_users.append(user)
                elif processing_type == 'MDB_PROCESSING':
                    mdb_users.append(user)
                elif processing_type == 'NESTING_PROCESSING':
                    nesting_users.append(user)
                elif processing_type == 'ACCURA_PROCESSING':
                    accura_users.append(user)
                elif processing_type == 'BOERE_PROCESSING':
                    boere_users.append(user)

        return {
            'service_enabled': True,
            'hops_processing_users': hops_users,
            'mdb_processing_users': mdb_users,
            'nesting_processing_users': nesting_users,
            'accura_processing_users': accura_users,
            'boere_processing_users': boere_users,
            'hops_imports_triggered': self.stats['hops_imports_triggered'],
            'mdb_imports_triggered': self.stats['mdb_imports_triggered'],
            'nesting_imports_triggered': self.stats['nesting_imports_triggered'],
            'accura_imports_triggered': self.stats['accura_imports_triggered'],
            'boere_imports_triggered': self.stats['boere_imports_triggered'],
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
        
        elif processing_type in ['NESTING_PROCESSING', 'ACCURA_PROCESSING', 'BOERE_PROCESSING']:
            # For ALL PDF-based processing, we need to trigger the unified PDF processing
            # This includes NESTING because we want all PDF processors to work on the same file
            code_to_match = project_code
            self._log(f"{processing_type} voor user '{user_type}': Triggering unified PDF search for '{code_to_match}'.")

            if not code_to_match:
                self._log("Could not determine a project code to match against. Aborting PDF processing.")
                return

            # Find the PDF file ONCE
            pdf_file_path = self._find_matching_pdf(user_specific_path, code_to_match)
            
            if pdf_file_path:
                self._log(f"Found matching PDF: {pdf_file_path}")
                
                # Now process this PDF for ALL PDF-based processors that might be interested
                # Get all PDF processors from config
                all_pdf_processors = {}
                for user in self.scanner_users:
                    if self.scanner_user_logic_active.get(user, False):
                        proc_type = self.scanner_user_to_processing_type_map.get(user)
                        if proc_type in ['NESTING_PROCESSING', 'ACCURA_PROCESSING', 'BOERE_PROCESSING']:
                            # Check if they share the same PDF directory
                            user_path = self.scanner_user_paths.get(user)
                            if user_path == user_specific_path:
                                all_pdf_processors[user] = proc_type
                
                self._log(f"Processing PDF for all processors in same directory: {list(all_pdf_processors.keys())}")
                
                # Process the PDF once for all processors
                thread = threading.Thread(
                    target=self._process_pdf_for_all_processors,
                    args=(pdf_file_path, project_code, event_details, timestamp, all_pdf_processors, user_type)
                )
                thread.start()
            else:
                self._log(f"{processing_type} (voor user '{user_type}') overgeslagen: geen overeenkomend PDF bestand gevonden in '{user_specific_path}' voor project '{code_to_match}'.")
        
        
        elif processing_type:
            self._log(f"Onbekend processing_type '{processing_type}' voor gebruiker '{user_type}'.")
        else:
            self._log(f"Geen processing_type geconfigureerd voor gebruiker '{user_type}'.")

    def process_scan_for_open_event_async(self, project_code_to_log, base_project_code, scanned_code, current_user_scanner, api_url, config_data, timestamp=None):
        """Processes the OPEN scan event for other users in a background thread."""
        thread = threading.Thread(
            target=self._process_scan_for_open_event_task,
            args=(
                project_code_to_log,
                base_project_code,
                scanned_code,
                current_user_scanner,
                api_url,
                config_data,
                timestamp
            )
        )
        thread.daemon = True # Ensure thread doesn't block program exit
        thread.start()
        self._log(f"Background task started for OPEN event: {project_code_to_log}")

    def _process_scan_for_open_event_task(self, project_code_to_log, base_project_code, scanned_code, current_user_scanner, api_url, config_data, timestamp=None):
        """Task run in a separate thread to handle OPEN event logic for other users."""
        try:
            self._log(f"[BG_TASK] Processing OPEN for {project_code_to_log}, scanned by {current_user_scanner}.")
            open_users = config_data.get('scanner_panel_open_event_users', [])
            user_logic_active_states = config_data.get('scanner_panel_open_event_user_logic_active', {})
            user_paths_map = config_data.get('scanner_panel_open_event_user_paths', {})
            user_to_processing_type = config_data.get('scanner_user_to_processing_type_map', {})
            
            # Group users by their directory path to avoid duplicate searches
            path_to_users = {}
            pdf_processing_users = {}  # Track which users need PDF processing
            
            for user in open_users:
                if user == current_user_scanner:
                    continue
                if not user_logic_active_states.get(user, True):
                    self._log(f"[BG_TASK] Logic inactive for user '{user}'. Skipping OPEN event processing.")
                    continue
                    
                user_dir = user_paths_map.get(user)
                if user_dir and os.path.isdir(user_dir):
                    if user_dir not in path_to_users:
                        path_to_users[user_dir] = []
                    path_to_users[user_dir].append(user)
                    
                    # Track PDF-based processing types
                    processing_type = user_to_processing_type.get(user)
                    if processing_type in ['ACCURA_PROCESSING', 'BOERE_PROCESSING', 'NESTING_PROCESSING']:
                        if user_dir not in pdf_processing_users:
                            pdf_processing_users[user_dir] = {}
                        pdf_processing_users[user_dir][user] = processing_type
            
            # Process each unique directory once
            for user_dir, users_in_dir in path_to_users.items():
                self._log(f"[BG_TASK] Checking dir '{user_dir}' for users: {users_in_dir}")
                
                # Check if we have PDF processors for this directory
                pdf_processors = pdf_processing_users.get(user_dir, {})
                
                if pdf_processors and current_user_scanner not in pdf_processors:
                    # Only use background unified PDF processing if the current scanner is NOT a PDF processor
                    # (If they are a PDF processor, they already handled it in trigger_import_for_event)
                    self._log(f"[BG_TASK] Running background unified PDF processing for non-scanner PDF processors: {list(pdf_processors.keys())}")
                    self._process_directory_with_unified_pdf_handling(
                        user_dir, project_code_to_log, base_project_code, 
                        pdf_processors, api_url, timestamp
                    )
                elif pdf_processors and current_user_scanner in pdf_processors:
                    self._log(f"[BG_TASK] Skipping background PDF processing - already handled by scanner {current_user_scanner}")
                    
                # Remove ALL PDF processors from regular processing (they're handled above or in trigger_import_for_event)
                users_in_dir = [u for u in users_in_dir if u not in pdf_processors]
                
                # Process remaining non-PDF users normally
                for user in users_in_dir:
                    user_processing_type = user_to_processing_type.get(user)
                    match_found_for_this_user = False
                    
                    if user_dir and os.path.isdir(user_dir):
                        self._log(f"[BG_TASK] Checking dir '{user_dir}' for user '{user}' (type: {user_processing_type}) for project '{project_code_to_log}'.")
                        try:
                            # Logic adapted from scanner_panel.py lines 628-643
                            if base_project_code and base_project_code.strip():
                                for item_name in os.listdir(user_dir):
                                    item_base_name, _ = os.path.splitext(item_name)
                                    is_rep_scan_for_item = bool(re.search(r'_REP_?', project_code_to_log, re.IGNORECASE))
                                    
                                    # Standard file matching logic
                                    file_matches = False
                                    if is_rep_scan_for_item:
                                        if item_base_name.upper().endswith(project_code_to_log.upper()):
                                            file_matches = True
                                    else:
                                        if item_base_name.upper().endswith(project_code_to_log.upper()) and not re.search(r'_REP_?', item_name, re.IGNORECASE):
                                            file_matches = True
                                    
                                    if file_matches:
                                        # Regular users - file match is enough
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
                        
                        # Include original timestamp if provided
                        if timestamp:
                            data_open['timestamp'] = timestamp
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
            
            self._log(f"[BG_TASK] Finished processing OPEN for {project_code_to_log}.")
            if self.log_callback:
                self.log_callback(f"BACKGROUND_PROCESSING_COMPLETE:{project_code_to_log}")

        except Exception as e_task:
            self._log(f"[BG_TASK_FATAL_ERR] Unhandled exception in _process_scan_for_open_event_task for {project_code_to_log}: {e_task}\n{traceback.format_exc()}")
            if self.log_callback:
                self.log_callback(f"BACKGROUND_FATAL_ERROR:{project_code_to_log}:Error - {e_task}")

    def _process_directory_with_unified_pdf_handling(self, user_dir, project_code_to_log, base_project_code, 
                                                     pdf_processors, api_url, timestamp):
        """Process a directory once for all PDF-based processors."""
        try:
            self._log(f"[UNIFIED_PDF] Processing directory '{user_dir}' for PDF processors: {list(pdf_processors.keys())}")
            
            # Find matching PDF files in the directory
            is_rep_project = bool(re.search(r'_REP_?', project_code_to_log, re.IGNORECASE))
            
            for item_name in os.listdir(user_dir):
                if not item_name.lower().endswith('.pdf'):
                    continue
                    
                item_base_name, _ = os.path.splitext(item_name)
                file_matches = False
                
                # Check if this PDF matches the project using endswith (same as NESTING)
                if item_base_name.upper().endswith(project_code_to_log.upper()):
                    file_matches = True
                    self._log(f"[UNIFIED_PDF] Match found: '{item_base_name}' ends with '{project_code_to_log}'")
                else:
                    self._log(f"[UNIFIED_PDF] No match: '{item_base_name}' does not end with '{project_code_to_log}'")
                
                if file_matches:
                    pdf_path = os.path.join(user_dir, item_name)
                    self._log(f"[UNIFIED_PDF] Found matching PDF: {pdf_path}")
                    
                    # Process this PDF once for all relevant processors
                    results = self._process_pdf_for_multiple_processors(pdf_path, pdf_processors)
                    
                    # Send OPEN events for each processor that found work
                    for user, processing_type in pdf_processors.items():
                        if user in results and results[user]['has_work']:
                            self._log(f"[UNIFIED_PDF] Work found for {user} ({processing_type})")
                            
                            # Send OPEN event with a delay
                            delay = random.uniform(0.2, 1.5)
                            self._log(f"[UNIFIED_PDF] Waiting {delay:.2f}s before posting OPEN for {user}")
                            time.sleep(delay)
                            
                            data_open = {
                                'event': 'OPEN',
                                'details': f"Auto-detected PDF work",
                                'project': project_code_to_log,
                                'base_mo_code': base_project_code,
                                'is_rep_variant': is_rep_project,
                                'user': user
                            }
                            
                            if timestamp:
                                data_open['timestamp'] = timestamp
                                
                            try:
                                resp_open = requests.post(api_url, json=data_open, timeout=10)
                                if resp_open.ok:
                                    self._log(f"[UNIFIED_PDF] Successfully posted OPEN for {project_code_to_log} for user {user}")
                                    
                                    # Update counts based on processing type
                                    if processing_type == 'ACCURA_PROCESSING':
                                        self._update_accura_counts_in_db(
                                            project_code_to_log, user,
                                            results[user]['aantal_items'],
                                            results[user]['aantal_sides'],
                                            timestamp
                                        )
                                    elif processing_type == 'BOERE_PROCESSING':
                                        self._update_boere_count_in_db(
                                            project_code_to_log, user,
                                            results[user]['item_count'],
                                            timestamp
                                        )
                                    elif processing_type == 'NESTING_PROCESSING':
                                        self._update_open_event_with_nesting_counts(
                                            user, project_code_to_log,
                                            results[user]['nesting_count'],
                                            results[user]['opdeelzaag_count']
                                        )
                                    
                                    if self.log_callback:
                                        self.log_callback(f"BACKGROUND_PROJECT_OPENED:{project_code_to_log}:{user}")
                                else:
                                    self._log(f"[UNIFIED_PDF] API Error: {resp_open.status_code} - {resp_open.text}")
                            except Exception as e:
                                self._log(f"[UNIFIED_PDF] Error posting OPEN: {e}")
                        else:
                            self._log(f"[UNIFIED_PDF] No work found for {user} ({processing_type})")
                    
                    # Stop after processing the first matching PDF
                    break
                    
        except Exception as e:
            self._log(f"[UNIFIED_PDF] Error in unified PDF processing: {e}")
            import traceback
            self._log(traceback.format_exc())

    def _process_pdf_for_multiple_processors(self, pdf_path, pdf_processors):
        """Process a single PDF file once and extract data for all relevant processors using database."""
        results = {}
        
        try:
            if not self.pdf_db_manager:
                self._log("[PDF_DB] PDF database manager not available, falling back to direct parsing")
                return self._process_pdf_for_multiple_processors_fallback(pdf_path, pdf_processors)
            
            # Extract project code from filename
            project_code = self._extract_project_code_from_path(pdf_path)
            
            # Check if PDF is cached and parse if needed
            if not self.pdf_db_manager.is_pdf_cached(pdf_path, project_code):
                self._log(f"[PDF_DB] Parsing and caching PDF: {pdf_path}")
                success = self.pdf_db_manager.parse_and_store_pdf(pdf_path, project_code)
                if not success:
                    self._log("[PDF_DB] Failed to parse PDF, falling back to direct parsing")
                    return self._process_pdf_for_multiple_processors_fallback(pdf_path, pdf_processors)
            else:
                self._log(f"[PDF_DB] Using cached PDF data for: {pdf_path}")
            
            # Process for each processor type using database queries
            for user, processing_type in pdf_processors.items():
                if processing_type == 'ACCURA_PROCESSING':
                    accura_data = self.pdf_db_manager.get_accura_data(project_code)
                    results[user] = {
                        'has_work': accura_data['aantal_items'] > 0,
                        'aantal_items': accura_data['aantal_items'],
                        'aantal_sides': accura_data['aantal_sides']
                    }
                    
                elif processing_type == 'BOERE_PROCESSING':
                    boere_count = self.pdf_db_manager.get_boere_data(project_code)
                    results[user] = {
                        'has_work': boere_count > 0,
                        'item_count': boere_count
                    }
                    
                elif processing_type == 'NESTING_PROCESSING':
                    nesting_data = self.pdf_db_manager.get_nesting_data(project_code)
                    results[user] = {
                        'has_work': (nesting_data['nesting_count'] > 0 or nesting_data['opdeelzaag_count'] > 0),
                        'nesting_count': nesting_data['nesting_count'],
                        'opdeelzaag_count': nesting_data['opdeelzaag_count']
                    }
                    
        except Exception as e:
            self._log(f"[PDF_DB] Error processing PDF {pdf_path}: {e}")
            self._log(traceback.format_exc())
            # Fallback to direct parsing
            return self._process_pdf_for_multiple_processors_fallback(pdf_path, pdf_processors)
            
        return results
    
    def _extract_project_code_from_path(self, pdf_path):
        """Extract project code from PDF file path."""
        try:
            filename = os.path.basename(pdf_path)
            # Extract MO code and description from filename
            # Example: "S04479_RAPPORT_Rudi Matterne_0411_MO07199_Hoekdressing - opklapbed (4-7).PDF"
            # Should return: "MO07199_Hoekdressing - opklapbed (4-7)"
            
            match = re.search(r'(MO\d+[^.]*?)\.PDF', filename, re.IGNORECASE)
            if match:
                project_code = match.group(1).strip()
                self._log(f"[PDF_DB] Extracted project code: '{project_code}' from '{filename}'")
                return project_code
            
            # Fallback: look for MO pattern anywhere
            match = re.search(r'(MO\d+.*?)(?:\.PDF|$)', filename, re.IGNORECASE)
            if match:
                project_code = match.group(1).strip()
                self._log(f"[PDF_DB] Extracted project code (fallback): '{project_code}' from '{filename}'")
                return project_code
            
            # Last resort: use filename without extension
            project_code = os.path.splitext(filename)[0]
            self._log(f"[PDF_DB] Warning: Could not extract MO code, using full filename: '{project_code}'")
            return project_code
            
        except Exception as e:
            self._log(f"Error extracting project code from {pdf_path}: {e}")
            return os.path.splitext(os.path.basename(pdf_path))[0]
    
    def _extract_so_number_from_path(self, pdf_path):
        """Extract SO (Sales Order) number from PDF file path."""
        try:
            filename = os.path.basename(pdf_path)
            # Extract SO number from filename
            # Example: "S04479_RAPPORT_Rudi Matterne_0411_MO07199_Hoekdressing - opklapbed (4-7).PDF"
            # Should return: "S04479"
            
            match = re.search(r'^(S\d+)', filename, re.IGNORECASE)
            if match:
                so_number = match.group(1).upper()
                self._log(f"[PDF_DB] Extracted SO number: '{so_number}' from '{filename}'")
                return so_number
            
            return None
            
        except Exception as e:
            self._log(f"Error extracting SO number from {pdf_path}: {e}")
            return None
    
    def _process_pdf_for_multiple_processors_fallback(self, pdf_path, pdf_processors):
        """Fallback method using direct PDF parsing (original implementation)."""
        results = {}
        
        try:
            # Process for each processor type using their individual parsing methods
            for user, processing_type in pdf_processors.items():
                if processing_type == 'ACCURA_PROCESSING':
                    # Use the dedicated ACCURA parsing method
                    accura_data = self._parse_pdf_for_accura_counts(pdf_path)
                    results[user] = {
                        'has_work': accura_data['aantal_items'] > 0,
                        'aantal_items': accura_data['aantal_items'],
                        'aantal_sides': accura_data['aantal_sides']
                    }
                    
                elif processing_type == 'BOERE_PROCESSING':
                    # Use the dedicated BOERE parsing method
                    boere_count = self._parse_pdf_for_boere_counts(pdf_path)
                    results[user] = {
                        'has_work': boere_count > 0,
                        'item_count': boere_count
                    }
                    
                elif processing_type == 'NESTING_PROCESSING':
                    # Use the dedicated NESTING parsing method
                    nesting_data = self._parse_pdf_for_counts(pdf_path)
                    results[user] = {
                        'has_work': (nesting_data['nesting_count'] > 0 or nesting_data['opdeelzaag_count'] > 0),
                        'nesting_count': nesting_data['nesting_count'],
                        'opdeelzaag_count': nesting_data['opdeelzaag_count']
                    }
                    
        except Exception as e:
            self._log(f"[UNIFIED_PDF] Error processing PDF {pdf_path}: {e}")
            
        return results

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

    def _find_matching_pdf(self, directory_path, project_code):
        """Find a PDF file that matches the project code. Returns the full path or None."""
        try:
            for item_name in os.listdir(directory_path):
                if item_name.lower().endswith('.pdf'):
                    item_base_name, _ = os.path.splitext(item_name)
                    
                    # Use endswith matching (consistent with existing logic)
                    if item_base_name.upper().endswith(project_code.upper()):
                        return os.path.join(directory_path, item_name)
            return None
        except Exception as e:
            self._log(f"Error searching for PDF: {e}")
            return None
    
    def _process_pdf_for_all_processors(self, pdf_file_path, project_code, event_details, timestamp, all_pdf_processors, triggering_user):
        """Process a single PDF file for all interested processors."""
        try:
            self._log(f"[UNIFIED_PDF] Processing {pdf_file_path} for processors: {list(all_pdf_processors.keys())}")
            
            # Send callback that we're processing for all users
            if self.log_callback:
                self.log_callback(f"BACKGROUND_PROCESSING_STARTED:{project_code}")
            
            # Process the PDF once and get results for all processors
            results = self._process_pdf_for_multiple_processors(pdf_file_path, all_pdf_processors)
            
            # Now handle results for each processor
            for user, processing_type in all_pdf_processors.items():
                if user in results and results[user]['has_work']:
                    self._log(f"[UNIFIED_PDF] Work found for {user} ({processing_type})")
                    
                    if processing_type == 'NESTING_PROCESSING':
                        # Update stats and log
                        with BackgroundImportService._stats_lock:
                            self.stats['nesting_imports_triggered'] += 1
                            self.stats['total_imports_triggered'] += 1
                        
                        # Update nesting counts in DB
                        self._update_open_event_with_nesting_counts(
                            user, project_code,
                            results[user]['nesting_count'],
                            results[user]['opdeelzaag_count']
                        )
                        
                        # Log auto import
                        self._log(f"NESTING_PROCESSING voltooid: Nesting={results[user]['nesting_count']}, Opdeelzaag={results[user]['opdeelzaag_count']}")
                        self._log_import_event(user, project_code, 
                            f"NESTING_PROCESSING voltooid: Nesting={results[user]['nesting_count']}, Opdeelzaag={results[user]['opdeelzaag_count']}")
                        
                        # Send callback for scanner panel
                        if self.log_callback:
                            self.log_callback(f"BACKGROUND_PROJECT_OPENED:{project_code}:{user}")
                        
                    elif processing_type == 'ACCURA_PROCESSING':
                        # For ACCURA, we need to send OPEN event if not already sent
                        if user != triggering_user:
                            # Send OPEN event for ACCURA
                            self._send_open_event_for_user(user, project_code, event_details, timestamp, triggering_user)
                        
                        # Update stats
                        with BackgroundImportService._stats_lock:
                            self.stats['accura_imports_triggered'] += 1
                            self.stats['total_imports_triggered'] += 1
                        
                        # Update ACCURA counts
                        self._update_accura_counts_in_db(
                            project_code, user,
                            results[user]['aantal_items'],
                            results[user]['aantal_sides'],
                            timestamp
                        )
                        
                        # Send callback for scanner panel
                        if self.log_callback:
                            self.log_callback(f"BACKGROUND_PROJECT_OPENED:{project_code}:{user}")
                        
                    elif processing_type == 'BOERE_PROCESSING':
                        # For BOERE, we need to send OPEN event if not already sent
                        if user != triggering_user:
                            # Send OPEN event for BOERE
                            self._send_open_event_for_user(user, project_code, event_details, timestamp, triggering_user)
                        
                        # Update stats
                        with BackgroundImportService._stats_lock:
                            self.stats['boere_imports_triggered'] += 1
                            self.stats['total_imports_triggered'] += 1
                        
                        # Update BOERE count
                        self._update_boere_count_in_db(
                            project_code, user,
                            results[user]['item_count'],
                            timestamp
                        )
                        
                        # Send callback for scanner panel
                        if self.log_callback:
                            self.log_callback(f"BACKGROUND_PROJECT_OPENED:{project_code}:{user}")
                else:
                    self._log(f"[UNIFIED_PDF] No work found for {user} ({processing_type})")
            
            # Send completion callback
            if self.log_callback:
                self.log_callback(f"BACKGROUND_PROCESSING_COMPLETE:{project_code}")
                    
        except Exception as e:
            self._log(f"[UNIFIED_PDF] Error processing PDF for all processors: {e}")
            import traceback
            self._log(traceback.format_exc())
    
    def _send_open_event_for_user(self, user, project_code, event_details, timestamp, triggering_user):
        """Send an OPEN event for a specific user."""
        try:
            config = get_config()
            api_url = config.get('api_url', 'http://localhost:5001/log')
            
            # Extract base project code
            base_project_code = self._get_base_code(project_code)
            is_rep_variant = bool(re.search(r'_REP_?', project_code, re.IGNORECASE))
            
            data_open = {
                'event': 'OPEN',
                'details': f"Auto-detected from {triggering_user}'s scan of {event_details}",
                'project': project_code,
                'base_mo_code': base_project_code,
                'is_rep_variant': is_rep_variant,
                'user': user
            }
            
            if timestamp:
                data_open['timestamp'] = timestamp
            
            # Add a small delay to prevent collisions
            delay = random.uniform(0.2, 0.5)
            time.sleep(delay)
            
            resp = requests.post(api_url, json=data_open, timeout=10)
            if resp.ok:
                self._log(f"Successfully posted OPEN event for {user} on project {project_code}")
            else:
                self._log(f"Failed to post OPEN event for {user}: {resp.status_code} - {resp.text}")
                
        except Exception as e:
            self._log(f"Error sending OPEN event for {user}: {e}")

    def _get_base_code(self, project_code):
        """Extracts MO codes (5 digits) or uses full project name as fallback."""
        import re
        # Look for MOxxxxx pattern (exactly 5 digits to match BarcodeMatch)
        mo_match = re.search(r'(MO\d{5})', project_code, re.IGNORECASE)
        if mo_match:
            return mo_match.group(0).upper()
        # Use full project name when no MO code found
        return project_code

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
            
            # Count items in the Excel file
            item_count = len(df)
            self._log(f"HOPS Excel rapport bevat {item_count} items")

            # Update the OPEN event with the Excel file path AND item count
            self._update_open_event_with_file_path_and_count(
                user_name,
                project_code,  # Use the actual project code from the OPEN event
                excel_path,
                item_count
            )
            
            # Note: OPEN events for other users are already created by process_scan_for_open_event_async
            # Sessions will be created when users actually start working (not here)

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
            
            # Count items in the Excel file
            item_count = len(df_export)
            self._log(f"MDB Excel rapport bevat {item_count} items")
            
            # Update the OPEN event with the Excel file path AND item count
            self._update_open_event_with_file_path_and_count(
                user_name,
                project_code,  # Use the actual project code from the OPEN event
                excel_path,
                item_count
            )
            
            # Note: OPEN events for other users are already created by process_scan_for_open_event_async
            # Sessions will be created when users actually start working (not here)

        except Exception as e:
            self._log(f"Fout bij opslaan van MDB Excel rapport voor {mdb_basename}: {e}")
            self.logger.error(f"Error saving MDB Excel report for {mdb_basename}: {e}")

    def _update_open_event_with_file_path_and_count(self, user_name, project, file_path, item_count):
        """Update the existing OPEN event with the Excel file path and item count."""
        try:
            config = get_config()
            # Ensure api_url is correctly retrieved
            api_url = config.get('api_url', '').rstrip('/')
            
            if not api_url:
                self._log("Geen API URL geconfigureerd voor event logging")
                return

            # Update file path
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

            # Update item count
            update_count_url = api_url.replace('/log', '/update_item_count')
            count_data = {
                'project': project,
                'user': user_name,
                'item_count': item_count,
                'timestamp': datetime.now().isoformat()
            }
            
            response = requests.post(update_count_url, json=count_data, timeout=5)
            
            if response.ok:
                self._log(f"OPEN event updated with item count ({item_count}) for: {user_name} - {project}")
            else:
                self._log(f"Fout bij updaten OPEN event met item count: HTTP {response.status_code} - {response.text}")

        except Exception as e:
            self.logger.error(f"Fout bij updaten OPEN event: {e}")
            self._log(f"Fout bij API update: {str(e)}")

    def _execute_nesting_import_with_stats(self, user_type, project_code, event_details, timestamp, pdf_file_path):
        """Execute NESTING_PROCESSING with PDF parsing and stats tracking for a specific PDF file."""
        try:
            with BackgroundImportService._stats_lock:
                self.stats['nesting_imports_triggered'] += 1
                self.stats['total_imports_triggered'] += 1
            
            self._log(f"NESTING_PROCESSING gestart voor user '{user_type}', project '{project_code}', PDF: {pdf_file_path}")
            
            # Parse the specific PDF file
            nesting_count = 0
            opdeelzaag_count = 0
            
            try:
                if os.path.exists(pdf_file_path) and pdf_file_path.lower().endswith('.pdf'):
                    self._log(f"PDF bestand wordt verwerkt: {pdf_file_path}")
                    
                    # Parse PDF for nesting and opdeelzaag counts
                    pdf_counts = self._parse_pdf_for_counts(pdf_file_path)
                    
                    nesting_count = pdf_counts['nesting_count']
                    opdeelzaag_count = pdf_counts['opdeelzaag_count']
                    
                    self._log(f"PDF parsing resultaat: Nesting={nesting_count}, Opdeelzaag={opdeelzaag_count}")
                    
                    if nesting_count > 0 or opdeelzaag_count > 0:
                        self._log(f"NESTING_PROCESSING voltooid: Nesting={nesting_count}, Opdeelzaag={opdeelzaag_count}")
                        
                        # Update the OPEN event with extracted counts
                        self._update_open_event_with_nesting_counts(user_type, project_code, nesting_count, opdeelzaag_count)
                        
                        # Log successful processing
                        self._log_import_event(user_type, project_code, f"NESTING_PROCESSING voltooid: Nesting={nesting_count}, Opdeelzaag={opdeelzaag_count}")
                    else:
                        self._log(f"NESTING_PROCESSING: Geen onderdelen gevonden in PDF {pdf_file_path}")
                else:
                    self._log(f"NESTING_PROCESSING: PDF bestand niet gevonden: {pdf_file_path}")
                    
            except Exception as e:
                self._log(f"Fout bij NESTING_PROCESSING voor {user_type}: {e}")
                self.logger.error(f"NESTING_PROCESSING error: {e}")
                
        except Exception as e:
            self._log(f"Kritieke fout bij NESTING_PROCESSING stats update: {e}")
            self.logger.error(f"Critical NESTING_PROCESSING error: {e}")

    def _parse_pdf_for_counts(self, pdf_path):
        """Parse PDF for part counts using proper table extraction."""
        nesting_count = 0
        opdeelzaag_count = 0
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    try:
                        # Extract tables from the page
                        tables = page.extract_tables()
                        
                        for table in tables:
                            if not table or len(table) < 2:  # Need header + data
                                continue
                                
                            # Look for tables with 'Aantal onderdelen' column
                            header = table[0] if table[0] else []
                            aantal_col = -1
                            
                            for i, cell in enumerate(header):
                                if cell and 'aantal onderdelen' in str(cell).lower():
                                    aantal_col = i
                                    break
                            
                            if aantal_col >= 0:
                                # Process data rows
                                for row in table[1:]:
                                    if len(row) > aantal_col and row[aantal_col]:
                                        try:
                                            count = int(str(row[aantal_col]).strip())
                                            
                                            # Check row context for opdeelzaag indicators
                                            row_text = ' '.join([str(cell) for cell in row if cell]).lower()
                                            
                                            if 'opdeelzaag' in row_text or 'zaag' in row_text:
                                                opdeelzaag_count += count
                                                self._log(f"Opdeelzaag found: {count} onderdelen")
                                            else:
                                                nesting_count += count
                                                self._log(f"Nesting found: {count} onderdelen")
                                        except (ValueError, TypeError):
                                            continue
                        
                        # Fallback: search page text for pattern
                        if nesting_count == 0 and opdeelzaag_count == 0:
                            text = page.extract_text()
                            if text:
                                # Look for context-based patterns
                                nesting_section = re.search(r'nesting.*?aantal\s+onderdelen[:\s]*(\d+)', text, re.IGNORECASE | re.DOTALL)
                                if nesting_section:
                                    count = int(nesting_section.group(1))
                                    nesting_count += count
                                    self._log(f"Nesting section found: {count} onderdelen")
                                
                                opdeelzaag_section = re.search(r'opdeelzaag.*?aantal\s+onderdelen[:\s]*(\d+)', text, re.IGNORECASE | re.DOTALL)
                                if opdeelzaag_section:
                                    count = int(opdeelzaag_section.group(1))
                                    opdeelzaag_count += count
                                    self._log(f"Opdeelzaag section found: {count} onderdelen")
                                
                                # Generic fallback
                                if nesting_count == 0 and opdeelzaag_count == 0:
                                    matches = re.findall(r'aantal\s+onderdelen[:\s]*(\d+)', text, re.IGNORECASE)
                                    for match in matches:
                                        count = int(match)
                                        nesting_count += count
                                        self._log(f"Fallback pattern match: {count} onderdelen")
                        
                    except Exception as e_page:
                        self._log(f"Error parsing page {page_num}: {e_page}")
                        continue
                        
        except Exception as e:
            self._log(f"PDF parsing error: {e}")
            
        return {'nesting_count': nesting_count, 'opdeelzaag_count': opdeelzaag_count}

    def _parse_pdf_for_accura_counts(self, pdf_path):
        """Parse PDF for ACCURA_PROCESSING - find L1/L2/B1/B2 tables in Nesting and Opdeelzaag sections."""
        aantal_items = 0
        aantal_sides = 0
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                # ACCURA processes both Nesting and Opdeelzaag sections
                # Look for L1/L2/B1/B2 tables on ANY page
                
                for page_num, page in enumerate(pdf.pages, 1):
                    try:
                        # Check page context for enhanced logging
                        page_text = page.extract_text() or ""
                        has_nesting = 'nesting' in page_text.lower()
                        has_opdeelzaag = 'opdeelzaag' in page_text.lower()
                        has_controle = 'controle' in page_text.lower()
                        
                        # ACCURA should process Nesting and Opdeelzaag, NOT Controle
                        is_accura_page = has_nesting or has_opdeelzaag
                        
                        tables = page.extract_tables()
                        self._log(f"ACCURA_PROCESSING page {page_num}: Found {len(tables)} tables (Nesting: {has_nesting}, Opdeelzaag: {has_opdeelzaag}, Controle: {has_controle})")
                        
                        if not is_accura_page:
                            self._log(f"ACCURA_PROCESSING: Skipping page {page_num} - not Nesting or Opdeelzaag")
                            continue
                        
                        for table_idx, table in enumerate(tables):
                            if not table or len(table) < 2:
                                continue
                            
                            # Look for table with L1, L2, B1, B2 columns
                            header = table[0] if table[0] else []
                            l1_col = l2_col = b1_col = b2_col = -1
                            
                            for i, cell in enumerate(header):
                                if not cell:
                                    continue
                                cell_upper = str(cell).upper()
                                if cell_upper == 'L1':
                                    l1_col = i
                                elif cell_upper == 'L2':
                                    l2_col = i
                                elif cell_upper == 'B1':
                                    b1_col = i
                                elif cell_upper == 'B2':
                                    b2_col = i
                            
                            # Found L1/L2/B1/B2 table - this IS ACCURA work
                            if all(col >= 0 for col in [l1_col, l2_col, b1_col, b2_col]):
                                section_type = "Nesting" if has_nesting else "Opdeelzaag" if has_opdeelzaag else "Unknown"
                                self._log(f"ACCURA_PROCESSING: Found L1/L2/B1/B2 table on page {page_num} in {section_type} section")
                                
                                # Process all data rows
                                for row_idx, row in enumerate(table[1:], 1):
                                    if not row or len(row) <= max(l1_col, l2_col, b1_col, b2_col):
                                        continue
                                    
                                    # Check if row starts with a number (valid data row)
                                    if not (row[0] and str(row[0]).strip().isdigit()):
                                        continue
                                    
                                    # Count work content in L1/L2/B1/B2 columns
                                    sides_in_row = 0
                                    has_work = False
                                    
                                    for col in [l1_col, l2_col, b1_col, b2_col]:
                                        cell_content = str(row[col]).strip() if row[col] else ''
                                        col_name = ['L1', 'L2', 'B1', 'B2'][[l1_col, l2_col, b1_col, b2_col].index(col)]
                                        
                                        # Clean multi-line content and check for meaningful work
                                        cleaned_content = ' '.join(cell_content.split()) if cell_content else ''
                                        
                                        # Check if cell has meaningful work content
                                        if (cleaned_content and 
                                            cleaned_content.upper() not in ['', 'TE BESTELLEN', 'DUMMY', 'N/A'] and
                                            not cleaned_content.isdigit() and
                                            len(cleaned_content) > 1):  # Must be more than 1 character
                                            sides_in_row += 1
                                            has_work = True
                                            self._log(f"ACCURA {section_type} {col_name} has valid content: '{cleaned_content}'")
                                    
                                    if has_work:
                                        aantal_items += 1
                                        aantal_sides += sides_in_row
                                        self._log(f"ACCURA {section_type} row {aantal_items}: {sides_in_row} sides with content")
                        
                    except Exception as e_page:
                        self._log(f"Error parsing ACCURA_PROCESSING page {page_num}: {e_page}")
                        continue
                        
        except Exception as e:
            self._log(f"ACCURA_PROCESSING PDF parsing error: {e}")
            
        self._log(f"ACCURA_PROCESSING result: {aantal_items} items, {aantal_sides} sides")
        return {'aantal_items': aantal_items, 'aantal_sides': aantal_sides}

    def _check_pdf_for_accura_work(self, pdf_path):
        """Check if PDF has actual work in L1/L2/B1/B2 columns by counting."""
        counts = self._parse_pdf_for_accura_counts(pdf_path)
        return counts['aantal_items'] > 0

    def _extract_accura_data_from_text(self, text):
        """Extract ACCURA data from pre-parsed PDF text."""
        aantal_items = 0
        aantal_sides = 0
        
        try:
            # Look for table structure - find the line with column headers
            lines = text.split('\n')
            header_line_index = -1
            
            for i, line in enumerate(lines):
                # Look for header with L1, L2, B1, B2 columns
                if 'L1' in line.upper() and 'L2' in line.upper() and 'B1' in line.upper() and 'B2' in line.upper():
                    header_line_index = i
                    self._log(f"Found ACCURA table header at line {i}: {line.strip()}")
                    break
            
            if header_line_index == -1:
                return {'aantal_items': 0, 'aantal_sides': 0}
            
            # Parse data rows after the header
            for i in range(header_line_index + 1, len(lines)):
                line = lines[i].strip()
                
                # Stop at end markers
                if line.lower().startswith('aantal onderdelen') or line.lower().startswith('totaal') or not line:
                    if line.lower().startswith('aantal onderdelen'):
                        break
                    continue
                
                # Skip lines that don't look like data rows (need at least a number at start)
                if not line or not line[0].isdigit():
                    continue
                
                # This is a data row - check if it has work in L1/L2/B1/B2 columns
                parts = line.split()
                
                if len(parts) < 5:  # Need at least: number, name, dimensions, some content
                    continue
                
                # Look for content that indicates work (anything that's not just numbers or "Te bestellen")
                has_work_in_row = False
                sides_in_row = 0
                
                # Skip the first few parts (number, name, dimensions) and look at the rest
                potential_work_parts = parts[4:] if len(parts) > 4 else []
                
                for part in potential_work_parts:
                    # Skip common non-work indicators
                    if part.upper() in ['TE', 'BESTELLEN', 'DUMMY']:
                        continue
                        
                    # If there's any alphabetic content, consider it work
                    if any(char.isalpha() for char in part) and len(part) > 1:
                        has_work_in_row = True
                        sides_in_row += 1
                        
                    # Also count if it's a meaningful number (like thickness: 1mm, 19mm)
                    elif part.endswith('mm') or (part.isdigit() and int(part) > 0 and int(part) < 100):
                        sides_in_row += 1
                
                # Count this row if it has any work content
                if has_work_in_row:
                    aantal_items += 1
                    aantal_sides += min(sides_in_row, 4)  # Max 4 sides per row (L1, L2, B1, B2)
                    
        except Exception as e:
            self._log(f"Error extracting ACCURA data: {e}")
            
        self._log(f"ACCURA extraction result: {aantal_items} items, {aantal_sides} sides")
        return {'aantal_items': aantal_items, 'aantal_sides': aantal_sides}

    def _parse_pdf_for_boere_counts(self, pdf_path):
        """Parse PDF for BOERE_PROCESSING - count items in Controle sections, excluding 'Te bestellen'."""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                item_count = 0
                
                for page_num, page in enumerate(pdf.pages, 1):
                    try:
                        # Check if page has Controle context
                        page_text = page.extract_text() or ""
                        has_controle = 'controle' in page_text.lower()
                        
                        if not has_controle:
                            continue
                        
                        # Extract tables from Controle pages
                        tables = page.extract_tables()
                        self._log(f"BOERE_PROCESSING page {page_num}: Found {len(tables)} tables in Controle context")
                        
                        for table_idx, table in enumerate(tables):
                            if not table or len(table) < 2:
                                continue
                            
                            # Look for table with "Pro.methode" column
                            header = table[0] if table[0] else []
                            pro_methode_col = -1
                            
                            for i, cell in enumerate(header):
                                if not cell:
                                    continue
                                cell_upper = str(cell).upper()
                                if 'PRO.METHODE' in cell_upper or 'METHODE' in cell_upper:
                                    pro_methode_col = i
                                    break
                            
                            if pro_methode_col >= 0:
                                self._log(f"BOERE_PROCESSING: Found Pro.methode table on page {page_num}, column {pro_methode_col}")
                                
                                # Count data rows, excluding those with "Te bestellen"
                                valid_items = 0
                                excluded_items = 0
                                
                                for row_idx, row in enumerate(table[1:], 1):
                                    if not row or len(row) <= pro_methode_col:
                                        continue
                                    
                                    # Check if this row has meaningful data (starts with number)
                                    if not (row[0] and str(row[0]).strip().isdigit()):
                                        continue
                                    
                                    # Check Pro.methode column content
                                    pro_methode_content = str(row[pro_methode_col]).strip() if row[pro_methode_col] else ''
                                    
                                    if 'TE BESTELLEN' in pro_methode_content.upper():
                                        excluded_items += 1
                                        self._log(f"BOERE_PROCESSING: Excluding item {row[0]} - Pro.methode: '{pro_methode_content}'")
                                    else:
                                        valid_items += 1
                                        self._log(f"BOERE_PROCESSING: Including item {row[0]} - Pro.methode: '{pro_methode_content}'")
                                
                                item_count += valid_items
                                self._log(f"BOERE_PROCESSING table: {valid_items} valid items, {excluded_items} excluded ('Te bestellen')")
                            else:
                                self._log(f"BOERE_PROCESSING: Table {table_idx} on page {page_num} has no Pro.methode column")
                    
                    except Exception as e_page:
                        self._log(f"Error processing BOERE page {page_num}: {e_page}")
                        continue
                
                self._log(f"BOERE_PROCESSING result: {item_count} items (excluding 'Te bestellen')")
                return item_count
                
        except Exception as e:
            self._log(f"Error parsing PDF for BOERE_PROCESSING: {e}")
            import traceback
            self._log(traceback.format_exc())
            return 0

    def _extract_boere_data_from_text(self, text):
        """Extract BOERE data from pre-parsed PDF text."""
        item_count = 0
        
        try:
            # Look for Controle section and stop at Magazijn header
            lines = text.split('\n')
            in_controle_section = False
            header_line_index = -1
            
            for i, line in enumerate(lines):
                line_upper = line.upper().strip()
                
                # Look for Controle header
                if 'CONTROLE' in line_upper and not in_controle_section:
                    in_controle_section = True
                    # Look for the table header in the next few lines
                    for j in range(i, min(i + 5, len(lines))):
                        if 'PRO.METHODE' in lines[j].upper() or 'METHODE' in lines[j].upper():
                            header_line_index = j
                            self._log(f"Found BOERE table header at line {j}: {lines[j].strip()}")
                            break
                    continue
                
                # Stop if we hit Magazijn header (as a section header, not just the word)
                if in_controle_section and line_upper.startswith('MAGAZIJN') and len(line.strip()) < 20:
                    self._log(f"Stopped at Magazijn header: {line.strip()}")
                    break
                
                # Process data rows if we're in the Controle section and found the header
                if in_controle_section and header_line_index != -1 and i > header_line_index:
                    line = line.strip()
                    
                    # Skip empty lines
                    if not line:
                        continue
                    
                    # Skip lines that don't look like data rows (need at least a number at start)
                    if not line[0].isdigit():
                        continue
                    
                    # Check if this row has "Te bestellen" in the Pro.methode column
                    if 'te bestellen' not in line.lower():
                        item_count += 1
                        
        except Exception as e:
            self._log(f"Error extracting BOERE data: {e}")
            
        self._log(f"BOERE extraction result: {item_count} items")
        return item_count

    def _extract_nesting_data_from_text(self, text):
        """Extract NESTING data from pre-parsed PDF text."""
        nesting_count = 0
        opdeelzaag_count = 0
        
        try:
            # Look for all "Aantal onderdelen: XX" patterns
            aantal_matches = re.findall(r'Aantal\s+onderdelen[:\s]*(\d+)', text, re.IGNORECASE)
            self._log(f"Found {len(aantal_matches)} 'Aantal onderdelen' matches: {aantal_matches}")
            
            # Method 1: Context-based detection using section headers
            # Look for sections containing "Nesting" followed by "Aantal onderdelen"
            nesting_section = re.search(r'Nesting.*?Aantal\s+onderdelen[:\s]*(\d+)', text, re.IGNORECASE | re.DOTALL)
            if nesting_section:
                found_count = int(nesting_section.group(1))
                nesting_count = max(nesting_count, found_count)
                self._log(f"Nesting section gevonden: {found_count} onderdelen")
            
            # Look for sections containing "Opdeelzaag" followed by "Aantal onderdelen"  
            opdeelzaag_section = re.search(r'Opdeelzaag.*?Aantal\s+onderdelen[:\s]*(\d+)', text, re.IGNORECASE | re.DOTALL)
            if opdeelzaag_section:
                found_count = int(opdeelzaag_section.group(1))
                opdeelzaag_count = max(opdeelzaag_count, found_count)
                self._log(f"✓ Opdeelzaag section gevonden: {found_count} onderdelen")
            else:
                # Debug: Check if we have Opdeelzaag but no match
                if 'opdeelzaag' in text.lower():
                    self._log(f"⚠️ Found 'Opdeelzaag' text but regex didn't match")
                    # Try broader search
                    opdeelzaag_lines = [line for line in text.split('\n') if 'opdeelzaag' in line.lower()]
                    aantal_lines = [line for line in text.split('\n') if 'aantal onderdelen' in line.lower()]
                    self._log(f"Opdeelzaag lines: {opdeelzaag_lines[:3]}")  # Show first 3
                    self._log(f"Aantal onderdelen lines: {aantal_lines}")
                    
                    # Try alternative pattern without requiring close proximity
                    if aantal_lines and opdeelzaag_lines:
                        for aantal_line in aantal_lines:
                            aantal_match = re.search(r'aantal\s+onderdelen[:\s]*(\d+)', aantal_line, re.IGNORECASE)
                            if aantal_match:
                                found_count = int(aantal_match.group(1))
                                opdeelzaag_count = max(opdeelzaag_count, found_count)
                                self._log(f"✓ Opdeelzaag (alternative): {found_count} onderdelen")
                                break
            
            # Method 2: Fallback for single section documents
            if len(aantal_matches) == 1 and not nesting_section and not opdeelzaag_section:
                found_count = int(aantal_matches[0])
                # Check document type by title/filename
                if re.search(r'Nesting', text, re.IGNORECASE):
                    nesting_count = max(nesting_count, found_count)
                    self._log(f"Nesting document (fallback): {found_count} onderdelen")
                elif re.search(r'Opdeelzaag', text, re.IGNORECASE):
                    opdeelzaag_count = max(opdeelzaag_count, found_count)
                    self._log(f"Opdeelzaag document (fallback): {found_count} onderdelen")
                else:
                    # Default to nesting if unclear
                    nesting_count = max(nesting_count, found_count)
                    self._log(f"Unclear document type, defaulting to Nesting: {found_count} onderdelen")
                    
        except Exception as e:
            self._log(f"Error extracting NESTING data: {e}")
            
        return {'nesting_count': nesting_count, 'opdeelzaag_count': opdeelzaag_count}

    def _parse_pdf_for_boere_count(self, pdf_path):
        """Parse PDF for BOERE metrics using proper table extraction."""
        item_count = 0
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    try:
                        # Extract tables from the page
                        tables = page.extract_tables()
                        
                        for table in tables:
                            if not table or len(table) < 2:  # Need header + data
                                continue
                            
                            # Look for table with "Controle" context and "Pro.methode" column
                            header = table[0] if table[0] else []
                            pro_methode_col = -1
                            has_controle_context = False
                            
                            # Check if this table is in Controle section
                            for cell in header:
                                if cell and 'controle' in str(cell).lower():
                                    has_controle_context = True
                                    break
                            
                            # Find Pro.methode column
                            for i, cell in enumerate(header):
                                if cell and 'pro.methode' in str(cell).lower().replace(' ', '').replace('.', ''):
                                    pro_methode_col = i
                                    break
                            
                            # Process if we're in controle context or found pro.methode column
                            if has_controle_context or pro_methode_col >= 0:
                                self._log(f"Found BOERE table (Controle context: {has_controle_context}, Pro.methode col: {pro_methode_col})")
                                
                                # Process data rows
                                for row_idx, row in enumerate(table[1:], 1):
                                    if not row:
                                        continue
                                    
                                    # Check if row starts with a number (valid data row)
                                    if not (row[0] and str(row[0]).strip().isdigit()):
                                        continue
                                    
                                    # Check Pro.methode column if it exists
                                    if pro_methode_col >= 0 and len(row) > pro_methode_col:
                                        pro_methode_content = str(row[pro_methode_col]).strip() if row[pro_methode_col] else ''
                                        
                                        # Count if NOT "Te bestellen"
                                        if 'te bestellen' not in pro_methode_content.lower():
                                            item_count += 1
                                            self._log(f"BOERE item {item_count}: Pro.methode = '{pro_methode_content}'")
                                    else:
                                        # If no Pro.methode column, check entire row for "Te bestellen"
                                        row_text = ' '.join([str(cell) for cell in row if cell]).lower()
                                        if 'te bestellen' not in row_text:
                                            item_count += 1
                                            self._log(f"BOERE item {item_count}: Row without 'Te bestellen'")
                        
                        # Fallback: search page text for Controle section
                        if item_count == 0:
                            text = page.extract_text()
                            if text and 'controle' in text.lower():
                                lines = text.split('\n')
                                in_controle = False
                                
                                for line in lines:
                                    if 'controle' in line.lower() and not in_controle:
                                        in_controle = True
                                        continue
                                    if in_controle and 'magazijn' in line.lower():
                                        break
                                    if in_controle and line.strip() and line.strip()[0].isdigit():
                                        if 'te bestellen' not in line.lower():
                                            item_count += 1
                        
                    except Exception as e_page:
                        self._log(f"Error parsing BOERE page {page_num}: {e_page}")
                        continue
                        
        except Exception as e:
            self._log(f"BOERE PDF parsing error: {e}")
            
        self._log(f"BOERE parsing result: {item_count} items")
        return item_count

    def _update_accura_counts_in_db(self, project_code, user_type, aantal_items, aantal_sides, timestamp):
        """Update database with ACCURA counts for the OPEN event."""
        try:
            config = get_config()
            
            # Ensure api_url is correctly retrieved
            api_url = config.get('api_url', '').rstrip('/')
            
            if not api_url:
                self._log("Geen API URL geconfigureerd voor accura counts update")
                return

            # Update accura counts via API
            update_url = api_url.replace('/log', '/update_accura_counts')
            data = {
                'project': project_code,
                'user': user_type,
                'aantal_items': aantal_items,
                'aantal_sides': aantal_sides,
                'timestamp': timestamp or datetime.now().isoformat()
            }
            
            response = requests.post(update_url, json=data, timeout=5)
            
            if response.ok:
                self._log(f"OPEN event updated with accura counts for: {user_type} - {project_code} (Items: {aantal_items}, Sides: {aantal_sides})")
                
                # Update stats
                with BackgroundImportService._stats_lock:
                    self.stats['accura_imports_triggered'] += 1
                    self.stats['total_imports_triggered'] += 1
            else:
                self._log(f"Fout bij updaten OPEN event met accura counts: HTTP {response.status_code} - {response.text}")

        except Exception as e:
            self.logger.error(f"Fout bij updaten OPEN event met accura counts: {e}")
            self._log(f"Fout bij accura counts API update: {str(e)}")

    def _update_boere_count_in_db(self, project_code, user_type, item_count, timestamp):
        """Update database with BOERE count for the OPEN event."""
        try:
            config = get_config()
            
            # Ensure api_url is correctly retrieved
            api_url = config.get('api_url', '').rstrip('/')
            
            if not api_url:
                self._log("Geen API URL geconfigureerd voor boere count update")
                return

            # Update item count via standard API (reuse existing item_count field)
            # BOERE uses the existing item_count field in the database
            data_update = {
                'event': 'UPDATE',
                'details': f"BOERE item count update: {item_count} items",
                'project': project_code,
                'user': user_type,
                'item_count': item_count,
                'timestamp': timestamp or datetime.now().isoformat()
            }
            
            # For BOERE we can update the item_count field directly on the OPEN event
            # This requires a slightly different approach - we'll update the most recent OPEN event
            update_response = self._update_open_event_item_count(project_code, user_type, item_count, timestamp)
            
            if update_response:
                self._log(f"OPEN event updated with boere count for: {user_type} - {project_code} (Items: {item_count})")
                
                # Update stats
                with BackgroundImportService._stats_lock:
                    self.stats['boere_imports_triggered'] += 1
                    self.stats['total_imports_triggered'] += 1
            else:
                self._log(f"Fout bij updaten OPEN event met boere count")

        except Exception as e:
            self.logger.error(f"Fout bij updaten OPEN event met boere count: {e}")
            self._log(f"Fout bij boere count API update: {str(e)}")

    def _update_open_event_item_count(self, project_code, user_type, item_count, timestamp):
        """Update the item_count for the most recent OPEN event."""
        try:
            config = get_config()
            api_url = config.get('api_url', '').rstrip('/')
            
            if not api_url:
                return False

            # Update item count via a direct database update
            update_url = api_url.replace('/log', '/update_item_count')
            data = {
                'project': project_code,
                'user': user_type,
                'item_count': item_count,
                'timestamp': timestamp or datetime.now().isoformat()
            }
            
            response = requests.post(update_url, json=data, timeout=5)
            return response.ok

        except Exception as e:
            self.logger.error(f"Error updating item count: {e}")
            return False

    def _update_open_event_with_nesting_counts(self, user_name, project, nesting_count, opdeelzaag_count):
        """Update OPEN event with extracted nesting and opdeelzaag counts."""
        try:
            config = get_config()
            
            # Ensure api_url is correctly retrieved
            api_url = config.get('api_url', '').rstrip('/')
            
            if not api_url:
                self._log("Geen API URL geconfigureerd voor nesting counts update")
                return

            # Update nesting counts
            update_url = api_url.replace('/log', '/update_nesting_counts')
            data = {
                'project': project,
                'user': user_name,
                'nesting_count': nesting_count,
                'opdeelzaag_count': opdeelzaag_count,
                'timestamp': datetime.now().isoformat()
            }
            
            response = requests.post(update_url, json=data, timeout=5)
            
            if response.ok:
                self._log(f"OPEN event updated with nesting counts for: {user_name} - {project} (Nesting: {nesting_count}, Opdeelzaag: {opdeelzaag_count})")
            else:
                self._log(f"Fout bij updaten OPEN event met nesting counts: HTTP {response.status_code} - {response.text}")

        except Exception as e:
            self.logger.error(f"Fout bij updaten OPEN event met nesting counts: {e}")
            self._log(f"Fout bij nesting counts API update: {str(e)}")

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