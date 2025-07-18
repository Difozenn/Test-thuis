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
# PDF imports removed - now using Excel processing

from config_utils import get_config
from path_utils import get_writable_path
# PDF database manager removed - now using Excel processing
from .excel_processing_functions import (
    find_excel_file_for_project, 
    parse_excel_for_nesting, 
    parse_excel_for_accura, 
    parse_excel_for_boere,
    process_excel_for_all_types,
    generate_excel_for_accura,
    generate_excel_for_boere
)

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
            # For ALL Excel-based processing - use unified handling
            code_to_match = project_code
            self._log(f"{processing_type} voor user '{user_type}': triggering unified Excel processing voor '{code_to_match}'")
            
            # Process ALL Excel users when any Excel user scans
            # This ensures ACCURA/BOERE get processed and Excel files are generated
            thread = threading.Thread(
                target=self._process_all_excel_users_unified,
                args=(user_type, project_code, event_details, timestamp, user_specific_path)
            )
            thread.start()
        
        
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
            excel_processing_users = {}  # Track which users need Excel processing
            
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
                    
                    # Track Excel-based processing types
                    processing_type = user_to_processing_type.get(user)
                    if processing_type in ['ACCURA_PROCESSING', 'BOERE_PROCESSING', 'NESTING_PROCESSING']:
                        if user_dir not in excel_processing_users:
                            excel_processing_users[user_dir] = {}
                        excel_processing_users[user_dir][user] = processing_type
            
            # Process each unique directory once
            for user_dir, users_in_dir in path_to_users.items():
                self._log(f"[BG_TASK] Checking dir '{user_dir}' for users: {users_in_dir}")
                
                # Check if we have Excel processors for this directory
                excel_processors = excel_processing_users.get(user_dir, {})
                
                if excel_processors:
                    # Always run unified Excel processing for all Excel processors
                    # This ensures Excel files are generated for ACCURA/BOERE
                    self._log(f"[BG_TASK] Running unified Excel processing for Excel processors: {list(excel_processors.keys())}")
                    self._process_directory_with_unified_excel_handling(
                        user_dir, project_code_to_log, base_project_code, 
                        excel_processors, api_url, timestamp
                    )
                    
                # Remove ALL Excel processors from regular processing (they're handled above or in trigger_import_for_event)
                users_in_dir = [u for u in users_in_dir if u not in excel_processors]
                
                # Process remaining non-Excel users normally
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

    def _process_directory_with_unified_excel_handling(self, user_dir, project_code_to_log, base_project_code, 
                                                     excel_processors, api_url, timestamp):
        """Process a directory once for all Excel-based processors."""
        try:
            self._log(f"[UNIFIED_EXCEL] Processing directory '{user_dir}' for Excel processors: {list(excel_processors.keys())}")
            
            # Find matching Excel file
            excel_file = find_excel_file_for_project(user_dir, project_code_to_log)
            
            if not excel_file:
                self._log(f"[UNIFIED_EXCEL] No Excel file found for project {project_code_to_log} in {user_dir}")
                return {}
                
            self._log(f"[UNIFIED_EXCEL] Found Excel file: {excel_file}")
            
            # Process Excel for all processor types at once
            processor_types = [proc_type for user, proc_type in excel_processors.items()]
            all_results = process_excel_for_all_types(excel_file, processor_types)
            
            # Map results back to users
            results = {}
            for user, proc_type in excel_processors.items():
                if proc_type in all_results:
                    result = all_results[proc_type]
                    
                    if proc_type == 'NESTING_PROCESSING':
                        results[user] = {
                            'has_work': (result['nesting_count'] > 0 or result['opdeelzaag_count'] > 0),
                            'nesting_count': result['nesting_count'],
                            'opdeelzaag_count': result['opdeelzaag_count'],
                            'mo_number': result['mo_number'],
                            'so_number': result['so_number'],
                            'customer_name': result['customer_name'],
                            'color': result['color']
                        }
                    elif proc_type == 'ACCURA_PROCESSING':
                        results[user] = {
                            'has_work': result.get('item_count', result.get('aantal_items', 0)) > 0,
                            'item_count': result.get('item_count', result.get('aantal_items', 0)),
                            'aantal_items': result['aantal_items'],  # Keep for backward compatibility
                            'aantal_sides': result['aantal_sides'],
                            'mo_number': result['mo_number'],
                            'so_number': result['so_number'],
                            'customer_name': result['customer_name'],
                            'color': result['color'],
                            'items_list': result.get('items_list', [])
                        }
                        
                        # Generate Excel file for ACCURA if items found
                        item_count = result.get('item_count', result.get('aantal_items', 0))
                        if item_count > 0 and result.get('items_list'):
                            try:
                                excel_path = generate_excel_for_accura(
                                    result['items_list'],
                                    result['mo_number'],
                                    result['so_number'],
                                    result['customer_name']
                                )
                                if excel_path:
                                    self._log(f"[ACCURA] Generated Excel file: {excel_path}")
                                    results[user]['generated_excel'] = excel_path
                            except Exception as e:
                                self._log(f"[ACCURA] Error generating Excel: {e}")
                    
                    elif proc_type == 'BOERE_PROCESSING':
                        results[user] = {
                            'has_work': result['item_count'] > 0,
                            'item_count': result['item_count'],
                            'mo_number': result['mo_number'],
                            'so_number': result['so_number'],
                            'customer_name': result['customer_name'],
                            'color': result['color'],
                            'items_list': result.get('items_list', [])
                        }
                        
                        # Generate Excel file for BOERE if items found
                        if result['item_count'] > 0 and result.get('items_list'):
                            try:
                                excel_path = generate_excel_for_boere(
                                    result['items_list'],
                                    result['mo_number'],
                                    result['so_number'],
                                    result['customer_name']
                                )
                                if excel_path:
                                    self._log(f"[BOERE] Generated Excel file: {excel_path}")
                                    results[user]['generated_excel'] = excel_path
                            except Exception as e:
                                self._log(f"[BOERE] Error generating Excel: {e}")
            
            # Send OPEN events for each processor that found work
            for user, processing_type in excel_processors.items():
                if user in results and results[user]['has_work']:
                    self._log(f"[UNIFIED_EXCEL] Work found for {user} ({processing_type})")
                    
                    # Send OPEN event with a delay
                    delay = random.uniform(0.2, 1.5)
                    self._log(f"[UNIFIED_EXCEL] Waiting {delay:.2f}s before posting OPEN for {user}")
                    time.sleep(delay)
                    
                    data_open = {
                        'event': 'OPEN',
                        'details': f"Auto-detected Excel work",
                        'project': project_code_to_log,
                        'base_mo_code': base_project_code,
                        'user': user
                    }
                    
                    # Add color, MO number, SO number, customer name, and item counts if available
                    if user in results:
                        result_data = results[user]
                        if result_data.get('color'):
                            data_open['color'] = result_data['color']
                        if result_data.get('mo_number'):
                            data_open['mo_number'] = result_data['mo_number']
                        if result_data.get('so_number'):
                            data_open['so_number'] = result_data['so_number']
                        if result_data.get('customer_name'):
                            data_open['customer_name'] = result_data['customer_name']
                        
                        # Add item counts based on processing type
                        if processing_type == 'NESTING_PROCESSING':
                            # Add nesting counts
                            if result_data.get('nesting_count'):
                                data_open['nesting_count'] = result_data['nesting_count']
                            if result_data.get('opdeelzaag_count'):
                                data_open['opdeelzaag_count'] = result_data['opdeelzaag_count']
                            # Add consolidated item count
                            if result_data.get('item_count'):
                                data_open['item_count'] = result_data['item_count']
                        elif processing_type == 'ACCURA_PROCESSING':
                            # Add accura counts
                            if result_data.get('item_count'):
                                data_open['item_count'] = result_data['item_count']
                            if result_data.get('aantal_sides'):
                                data_open['aantal_sides'] = result_data['aantal_sides']
                        elif processing_type == 'BOERE_PROCESSING':
                            # Add boere counts
                            if result_data.get('item_count'):
                                data_open['item_count'] = result_data['item_count']
                    
                    if timestamp:
                        data_open['timestamp'] = timestamp
                        
                    try:
                        resp_open = requests.post(api_url, json=data_open, timeout=10)
                        if resp_open.ok:
                            self._log(f"[UNIFIED_EXCEL] Successfully posted OPEN for {project_code_to_log} for user {user}")
                            
                            # Update counts based on processing type
                            if processing_type == 'ACCURA_PROCESSING':
                                self._update_accura_counts_in_db(
                                    project_code_to_log, user,
                                    results[user]['item_count'],
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
                            
                            # Update metadata if available
                            if results[user].get('mo_number') or results[user].get('customer_name') or results[user].get('color'):
                                self._update_project_metadata(
                                    project_code_to_log,
                                    results[user].get('mo_number'),
                                    results[user].get('so_number'),
                                    results[user].get('customer_name'),
                                    results[user].get('color')
                                )
                            
                            if self.log_callback:
                                self.log_callback(f"BACKGROUND_PROJECT_OPENED:{project_code_to_log}:{user}")
                        else:
                            self._log(f"[UNIFIED_EXCEL] API Error: {resp_open.status_code} - {resp_open.text}")
                    except Exception as e:
                        self._log(f"[UNIFIED_EXCEL] Error posting OPEN: {e}")
                else:
                    self._log(f"[UNIFIED_EXCEL] No work found for {user} ({processing_type})")
                    
        except Exception as e:
            self._log(f"[UNIFIED_EXCEL] Error in unified Excel processing: {e}")
            import traceback
            self._log(traceback.format_exc())

    
    
    

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

    def _process_directory_with_unified_excel_handling(self, user_dir, project_code_to_log, base_project_code, 
                                                     excel_processors, api_url, timestamp):
        """Process a directory once for all Excel-based processors."""
        try:
            self._log(f"[UNIFIED_EXCEL] Processing directory '{user_dir}' for Excel processors: {list(excel_processors.keys())}")
            
            # Find matching Excel file
            excel_file = find_excel_file_for_project(user_dir, project_code_to_log)
            
            if not excel_file:
                self._log(f"[UNIFIED_EXCEL] No Excel file found for project {project_code_to_log} in {user_dir}")
                return {}
                
            self._log(f"[UNIFIED_EXCEL] Found Excel file: {excel_file}")
            
            # Process Excel for all processor types at once
            processor_types = [proc_type for user, proc_type in excel_processors.items()]
            all_results = process_excel_for_all_types(excel_file, processor_types)
            
            # Map results back to users
            results = {}
            for user, proc_type in excel_processors.items():
                if proc_type in all_results:
                    result = all_results[proc_type]
                    
                    if proc_type == 'NESTING_PROCESSING':
                        results[user] = {
                            'has_work': (result['nesting_count'] > 0 or result['opdeelzaag_count'] > 0),
                            'nesting_count': result['nesting_count'],
                            'opdeelzaag_count': result['opdeelzaag_count'],
                            'item_count': result['item_count'],
                            'mo_number': result['mo_number'],
                            'so_number': result['so_number'],
                            'customer_name': result['customer_name'],
                            'color': result['color']
                        }
                    elif proc_type == 'ACCURA_PROCESSING':
                        results[user] = {
                            'has_work': result.get('item_count', result.get('aantal_items', 0)) > 0,
                            'item_count': result.get('item_count', result.get('aantal_items', 0)),
                            'aantal_items': result['aantal_items'],  # Keep for backward compatibility
                            'aantal_sides': result['aantal_sides'],
                            'mo_number': result['mo_number'],
                            'so_number': result['so_number'],
                            'customer_name': result['customer_name'],
                            'color': result['color'],
                            'items_list': result.get('items_list', [])
                        }
                        
                        # Generate Excel file for ACCURA if items found
                        item_count = result.get('item_count', result.get('aantal_items', 0))
                        if item_count > 0 and result.get('items_list'):
                            try:
                                excel_path = generate_excel_for_accura(
                                    result['items_list'],
                                    result['mo_number'],
                                    result['so_number'],
                                    result['customer_name']
                                )
                                if excel_path:
                                    self._log(f"[ACCURA] Generated Excel file: {excel_path}")
                                    results[user]['generated_excel'] = excel_path
                            except Exception as e:
                                self._log(f"[ACCURA] Error generating Excel: {e}")
                    
                    elif proc_type == 'BOERE_PROCESSING':
                        results[user] = {
                            'has_work': result['item_count'] > 0,
                            'item_count': result['item_count'],
                            'mo_number': result['mo_number'],
                            'so_number': result['so_number'],
                            'customer_name': result['customer_name'],
                            'color': result['color'],
                            'items_list': result.get('items_list', [])
                        }
                        
                        # Generate Excel file for BOERE if items found
                        if result['item_count'] > 0 and result.get('items_list'):
                            try:
                                excel_path = generate_excel_for_boere(
                                    result['items_list'],
                                    result['mo_number'],
                                    result['so_number'],
                                    result['customer_name']
                                )
                                if excel_path:
                                    self._log(f"[BOERE] Generated Excel file: {excel_path}")
                                    results[user]['generated_excel'] = excel_path
                            except Exception as e:
                                self._log(f"[BOERE] Error generating Excel: {e}")
            
            # Send OPEN events for each processor that found work
            for user, processing_type in excel_processors.items():
                if user in results and results[user]['has_work']:
                    self._log(f"[UNIFIED_EXCEL] Work found for {user} ({processing_type})")
                    
                    # Send OPEN event with a delay
                    delay = random.uniform(0.2, 1.5)
                    self._log(f"[UNIFIED_EXCEL] Waiting {delay:.2f}s before posting OPEN for {user}")
                    time.sleep(delay)
                    
                    data_open = {
                        'event': 'OPEN',
                        'details': f"Auto-detected Excel work",
                        'project': project_code_to_log,
                        'base_mo_code': base_project_code,
                        'user': user
                    }
                    
                    # Add color, MO number, SO number, customer name, and item counts if available
                    if user in results:
                        result_data = results[user]
                        if result_data.get('color'):
                            data_open['color'] = result_data['color']
                        if result_data.get('mo_number'):
                            data_open['mo_number'] = result_data['mo_number']
                        if result_data.get('so_number'):
                            data_open['so_number'] = result_data['so_number']
                        if result_data.get('customer_name'):
                            data_open['customer_name'] = result_data['customer_name']
                        
                        # Add item counts based on processing type
                        if processing_type == 'NESTING_PROCESSING':
                            # Add nesting counts
                            if result_data.get('nesting_count'):
                                data_open['nesting_count'] = result_data['nesting_count']
                            if result_data.get('opdeelzaag_count'):
                                data_open['opdeelzaag_count'] = result_data['opdeelzaag_count']
                            # Add consolidated item count
                            if result_data.get('item_count'):
                                data_open['item_count'] = result_data['item_count']
                        elif processing_type == 'ACCURA_PROCESSING':
                            # Add accura counts
                            if result_data.get('item_count'):
                                data_open['item_count'] = result_data['item_count']
                            if result_data.get('aantal_sides'):
                                data_open['aantal_sides'] = result_data['aantal_sides']
                        elif processing_type == 'BOERE_PROCESSING':
                            # Add boere counts
                            if result_data.get('item_count'):
                                data_open['item_count'] = result_data['item_count']
                    
                    if timestamp:
                        data_open['timestamp'] = timestamp
                        
                    try:
                        resp_open = requests.post(api_url, json=data_open, timeout=10)
                        if resp_open.ok:
                            self._log(f"[UNIFIED_EXCEL] Successfully posted OPEN for {project_code_to_log} for user {user}")
                            
                            # Update counts based on processing type
                            if processing_type == 'ACCURA_PROCESSING':
                                self._update_accura_counts_in_db(
                                    project_code_to_log, user,
                                    results[user]['item_count'],
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
                            
                            # Update metadata if available
                            if results[user].get('mo_number') or results[user].get('customer_name') or results[user].get('color'):
                                self._update_project_metadata(
                                    project_code_to_log,
                                    results[user].get('mo_number'),
                                    results[user].get('so_number'),
                                    results[user].get('customer_name'),
                                    results[user].get('color')
                                )
                            
                            if self.log_callback:
                                self.log_callback(f"BACKGROUND_PROJECT_OPENED:{project_code_to_log}:{user}")
                            
                            # Log AUTO_IMPORT event with processing details
                            if processing_type == 'NESTING_PROCESSING':
                                import_details = f"NESTING_PROCESSING voltooid: Nesting={results[user].get('nesting_count', 0)}, Opdeelzaag={results[user].get('opdeelzaag_count', 0)}"
                            elif processing_type == 'ACCURA_PROCESSING':
                                import_details = f"ACCURA_PROCESSING voltooid: {results[user].get('item_count', 0)} items, {results[user].get('aantal_sides', 0)} sides"
                            elif processing_type == 'BOERE_PROCESSING':
                                import_details = f"BOERE_PROCESSING voltooid: {results[user].get('item_count', 0)} items"
                            else:
                                import_details = f"{processing_type} voltooid"
                            
                            self._log_import_event(user, project_code_to_log, import_details)
                            
                            # Update stats
                            with BackgroundImportService._stats_lock:
                                if processing_type == 'NESTING_PROCESSING':
                                    self.stats['nesting_imports_triggered'] += 1
                                elif processing_type == 'ACCURA_PROCESSING':
                                    self.stats['accura_imports_triggered'] += 1
                                elif processing_type == 'BOERE_PROCESSING':
                                    self.stats['boere_imports_triggered'] += 1
                                self.stats['total_imports_triggered'] += 1
                                
                        else:
                            self._log(f"[UNIFIED_EXCEL] API Error: {resp_open.status_code} - {resp_open.text}")
                    except Exception as e:
                        self._log(f"[UNIFIED_EXCEL] Error posting OPEN: {e}")
                else:
                    self._log(f"[UNIFIED_EXCEL] No work found for {user} ({processing_type})")
                    
        except Exception as e:
            self._log(f"[UNIFIED_EXCEL] Error in unified Excel processing: {e}")
            import traceback
            self._log(traceback.format_exc())

    def _process_all_excel_users_unified(self, scanning_user, project_code, event_details, timestamp, scanning_user_path):
        """Process ALL Excel users when any Excel user scans - ensures all get processed and files generated."""
        try:
            self._log(f"[UNIFIED_SCAN] Processing ALL Excel users for project '{project_code}' (triggered by {scanning_user})")
            
            config = get_config()
            api_url = config.get('api_url', '').rstrip('/')
            open_users = config.get('scanner_panel_open_event_users', [])
            user_paths = config.get('scanner_panel_open_event_user_paths', {})
            user_processing_types = config.get('scanner_user_to_processing_type_map', {})
            
            # Find all Excel processing users
            excel_processors = {}
            for user in open_users:
                proc_type = user_processing_types.get(user)
                if proc_type in ['NESTING_PROCESSING', 'ACCURA_PROCESSING', 'BOERE_PROCESSING']:
                    user_path = user_paths.get(user)
                    if user_path and os.path.isdir(user_path):
                        excel_processors[user] = proc_type
            
            if not excel_processors:
                self._log(f"[UNIFIED_SCAN] No Excel processors found")
                return
                
            self._log(f"[UNIFIED_SCAN] Found Excel processors: {list(excel_processors.keys())}")
            
            # Get the directory to process (they should all share the same directory)
            processing_dir = scanning_user_path
            
            # Use the unified Excel handling that generates files
            self._process_directory_with_unified_excel_handling(
                processing_dir, project_code, project_code, 
                excel_processors, api_url, timestamp
            )
            
            # The unified handler already:
            # 1. Parses Excel for all processors
            # 2. Generates output Excel files for ACCURA/BOERE
            # 3. Creates/updates OPEN events with proper counts
            # 4. Logs AUTO_IMPORT events
            
            self._log(f"[UNIFIED_SCAN] Completed unified Excel processing for project '{project_code}'")
            
        except Exception as e:
            self._log(f"[UNIFIED_SCAN] Error in unified Excel processing: {e}")
            import traceback
            self._log(traceback.format_exc())
    
    def _execute_excel_processing_with_stats(self, user_type, project_code, event_details, timestamp, excel_file_path, processing_type):
        """Execute Excel processing with stats tracking."""
        try:
            with BackgroundImportService._stats_lock:
                if processing_type == 'NESTING_PROCESSING':
                    self.stats['nesting_imports_triggered'] += 1
                elif processing_type == 'ACCURA_PROCESSING':
                    self.stats['accura_imports_triggered'] += 1
                elif processing_type == 'BOERE_PROCESSING':
                    self.stats['boere_imports_triggered'] += 1
                self.stats['total_imports_triggered'] += 1
            
            self._log(f"{processing_type} gestart voor user '{user_type}', project '{project_code}', Excel: {excel_file_path}")
            
            # Parse Excel based on processing type
            result = None
            
            if processing_type == 'NESTING_PROCESSING':
                result = parse_excel_for_nesting(excel_file_path)
                if result['nesting_count'] > 0 or result['opdeelzaag_count'] > 0:
                    self._log(f"NESTING_PROCESSING voltooid: Nesting={result['nesting_count']}, Opdeelzaag={result['opdeelzaag_count']}")
                    self._update_open_event_with_nesting_counts(
                        user_type, project_code, 
                        result['nesting_count'], 
                        result['opdeelzaag_count']
                    )
                    self._log_import_event(user_type, project_code, 
                        f"NESTING_PROCESSING voltooid: Nesting={result['nesting_count']}, Opdeelzaag={result['opdeelzaag_count']}")
                else:
                    self._log(f"NESTING_PROCESSING: Geen onderdelen gevonden in Excel {excel_file_path}")
                    
            elif processing_type == 'ACCURA_PROCESSING':
                result = parse_excel_for_accura(excel_file_path)
                item_count = result.get('item_count', result.get('aantal_items', 0))
                if item_count > 0:
                    self._log(f"ACCURA_PROCESSING voltooid: {item_count} items, {result['aantal_sides']} sides")
                    self._update_accura_counts_in_db(
                        project_code, user_type,
                        item_count,
                        result['aantal_sides'],
                        timestamp
                    )
                    self._log_import_event(user_type, project_code,
                        f"ACCURA_PROCESSING voltooid: {item_count} items, {result['aantal_sides']} sides")
                else:
                    self._log(f"ACCURA_PROCESSING: Geen items gevonden in Excel {excel_file_path}")
                    
            elif processing_type == 'BOERE_PROCESSING':
                result = parse_excel_for_boere(excel_file_path)
                if result['item_count'] > 0:
                    self._log(f"BOERE_PROCESSING voltooid: {result['item_count']} items")
                    self._update_boere_count_in_db(
                        project_code, user_type,
                        result['item_count'],
                        timestamp
                    )
                    self._log_import_event(user_type, project_code,
                        f"BOERE_PROCESSING voltooid: {result['item_count']} items")
                else:
                    self._log(f"BOERE_PROCESSING: Geen items gevonden in Excel {excel_file_path}")
            
            # Update with additional metadata if available
            if result and (result.get('mo_number') or result.get('customer_name') or result.get('color')):
                self._update_project_metadata(
                    project_code, 
                    result.get('mo_number'),
                    result.get('so_number'),
                    result.get('customer_name'),
                    result.get('color')
                )
                
        except Exception as e:
            self._log(f"Fout bij {processing_type} voor {user_type}: {e}")
            self.logger.error(f"{processing_type} error: {e}")
            import traceback
            traceback.print_exc()

    def _update_project_metadata(self, project_code, mo_number, so_number, customer_name, color=None):
        """Update project metadata in database."""
        try:
            config = get_config()
            api_url = config.get('api_url', '').rstrip('/')
            
            if not api_url:
                return
                
            # Update via API endpoint
            update_data = {
                'project': project_code,
                'mo_number': mo_number,
                'so_number': so_number,
                'customer_name': customer_name,
                'color': color
            }
            
            # Remove None values
            update_data = {k: v for k, v in update_data.items() if v is not None}
            
            if len(update_data) > 1:  # More than just project code
                response = requests.post(
                    api_url.replace('/log', '/project/metadata'),
                    json=update_data,
                    timeout=3
                )
                
                if response.ok:
                    self._log(f"Project metadata updated for {project_code}")
                else:
                    self._log(f"Failed to update project metadata: {response.status_code}")
                    
        except Exception as e:
            self._log(f"Error updating project metadata: {e}")

    def _extract_accura_data_from_text(self, text):
        """Extract ACCURA data from pre-parsed text."""
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

    def _extract_boere_data_from_text(self, text):
        """Extract BOERE data from pre-parsed text."""
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
        """Extract NESTING data from pre-parsed text."""
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

    def _update_accura_counts_in_db(self, project_code, user_type, aantal_items, aantal_sides, timestamp):
        """Update database with ACCURA counts using consolidated item_count approach."""
        try:
            config = get_config()
            
            # Ensure api_url is correctly retrieved
            api_url = config.get('api_url', '').rstrip('/')
            
            if not api_url:
                self._log("Geen API URL geconfigureerd voor accura counts update")
                return

            # Update accura counts via API using consolidated approach
            update_url = api_url.replace('/log', '/update_accura_counts')
            data = {
                'project': project_code,
                'user': user_type,
                'item_count': aantal_items,  # Use consolidated field
                'aantal_items': aantal_items,  # Keep for backward compatibility
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
        """Update OPEN event with extracted nesting and opdeelzaag counts using consolidated item_count approach."""
        try:
            config = get_config()
            
            # Ensure api_url is correctly retrieved
            api_url = config.get('api_url', '').rstrip('/')
            
            if not api_url:
                self._log("Geen API URL geconfigureerd voor nesting counts update")
                return

            # Calculate total item count
            item_count = nesting_count + opdeelzaag_count

            # Try new consolidated endpoint first
            update_url = api_url.replace('/log', '/update_item_count')
            data = {
                'project': project,
                'user': user_name,
                'item_count': item_count,
                'nesting_count': nesting_count,  # Keep for backward compatibility
                'opdeelzaag_count': opdeelzaag_count,  # Keep for backward compatibility
                'timestamp': datetime.now().isoformat()
            }
            
            response = requests.post(update_url, json=data, timeout=5)
            
            if response.ok:
                self._log(f"OPEN event updated with item count for: {user_name} - {project} (Total: {item_count}, Nesting: {nesting_count}, Opdeelzaag: {opdeelzaag_count})")
            else:
                # Fallback to old endpoint
                self._log(f"New endpoint failed, trying fallback: {response.status_code}")
                update_url_fallback = api_url.replace('/log', '/update_nesting_counts')
                data_fallback = {
                    'project': project,
                    'user': user_name,
                    'nesting_count': nesting_count,
                    'opdeelzaag_count': opdeelzaag_count,
                    'timestamp': datetime.now().isoformat()
                }
                response = requests.post(update_url_fallback, json=data_fallback, timeout=5)
                if response.ok:
                    self._log(f"OPEN event updated with nesting counts (fallback) for: {user_name} - {project}")
                else:
                    self._log(f"Fout bij updaten OPEN event: HTTP {response.status_code} - {response.text}")

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
        
    def _log_import_event(self, user_type, project, details, item_count=None, nesting_count=None, opdeelzaag_count=None, aantal_sides=None):
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
            
            # Add item counts if provided
            if item_count is not None:
                data['item_count'] = item_count
            if nesting_count is not None:
                data['nesting_count'] = nesting_count
            if opdeelzaag_count is not None:
                data['opdeelzaag_count'] = opdeelzaag_count
            if aantal_sides is not None:
                data['aantal_sides'] = aantal_sides
            
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