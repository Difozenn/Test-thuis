"""
Background Import Service voor BarcodeMaster
Automatische monitoring en verwerking van OPUS en GANNOMAT bestanden
Now using Excel processing instead of PDF processing
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
from .excel_processing_functions import (
    find_excel_file_for_project, 
    parse_excel_for_nesting, 
    parse_excel_for_accura, 
    parse_excel_for_boere,
    process_excel_for_all_types
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
            # For ALL Excel-based processing
            code_to_match = project_code
            self._log(f"{processing_type} voor user '{user_type}': zoeken naar Excel bestand voor '{code_to_match}'")
            
            # Find matching Excel file
            excel_file = find_excel_file_for_project(user_specific_path, code_to_match)
            
            if excel_file:
                self._log(f"Excel bestand gevonden: {excel_file}")
                
                # Process in background thread
                thread = threading.Thread(
                    target=self._execute_excel_processing_with_stats,
                    args=(user_type, project_code, event_details, timestamp, excel_file, processing_type)
                )
                thread.start()
            else:
                self._log(f"{processing_type} overgeslagen: geen Excel bestand gevonden voor '{code_to_match}' in '{user_specific_path}'")
        
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
            
            if not open_users:
                self._log("[BG_TASK] No users configured for OPEN event processing.")
                return
                
            # Get directory paths for each user
            user_paths = config_data.get('scanner_panel_open_event_user_paths', {})
            
            # Get logic enabled flags for each user
            user_logic_active = config_data.get('scanner_panel_open_event_user_logic_active', {})
            
            # Get processing type map
            user_to_processing_type_map = config_data.get('scanner_user_to_processing_type_map', {})
            
            # Collect all users that need Excel processing
            excel_processors = {}
            
            for user in open_users:
                # Skip if user is the current scanner user
                if user == current_user_scanner:
                    self._log(f"[BG_TASK] Skipping {user} (current scanner user)")
                    continue
                
                # Skip if logic is not enabled for this user
                if not user_logic_active.get(user, False):
                    self._log(f"[BG_TASK] Skipping {user} (logic not active)")
                    continue
                
                # Get user's processing type
                processing_type = user_to_processing_type_map.get(user)
                
                # Skip if no processing type configured
                if not processing_type:
                    self._log(f"[BG_TASK] Skipping {user} (no processing type configured)")
                    continue
                
                # Skip if configured for no processing
                if processing_type == 'GEEN_PROCESSING':
                    self._log(f"[BG_TASK] Skipping {user} (configured for GEEN_PROCESSING)")
                    continue
                
                # Skip if no directory path configured
                user_dir = user_paths.get(user)
                if not user_dir or not os.path.isdir(user_dir):
                    self._log(f"[BG_TASK] Skipping {user} (no valid directory path: '{user_dir}')")
                    continue
                
                # Add to Excel processors if it's an Excel-based processing type
                if processing_type in ['NESTING_PROCESSING', 'ACCURA_PROCESSING', 'BOERE_PROCESSING']:
                    excel_processors[user] = processing_type
                    self._log(f"[BG_TASK] Added {user} to Excel processors ({processing_type})")
                
                # Handle HOPS and MDB processing separately (existing logic)
                elif processing_type == 'HOPS_PROCESSING':
                    # Handle HOPS processing
                    pass
                elif processing_type == 'MDB_PROCESSING':
                    # Handle MDB processing
                    pass
            
            # Process Excel-based users in one batch
            if excel_processors:
                self._log(f"[BG_TASK] Processing Excel for users: {list(excel_processors.keys())}")
                
                # Use unified Excel processing
                results = self._process_directory_with_unified_excel_handling(
                    user_paths[next(iter(excel_processors.keys()))],  # Use first user's directory
                    project_code_to_log,
                    base_project_code,
                    excel_processors,
                    api_url,
                    timestamp
                )
                
                self._log(f"[BG_TASK] Excel processing complete for {len(excel_processors)} users")
                
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
                            'customer_name': result['customer_name']
                        }
                    elif proc_type == 'ACCURA_PROCESSING':
                        results[user] = {
                            'has_work': result['aantal_items'] > 0,
                            'aantal_items': result['aantal_items'],
                            'aantal_sides': result['aantal_sides'],
                            'mo_number': result['mo_number'],
                            'so_number': result['so_number'],
                            'customer_name': result['customer_name']
                        }
                    elif proc_type == 'BOERE_PROCESSING':
                        results[user] = {
                            'has_work': result['item_count'] > 0,
                            'item_count': result['item_count'],
                            'mo_number': result['mo_number'],
                            'so_number': result['so_number'],
                            'customer_name': result['customer_name']
                        }
            
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
                                
                        else:
                            self._log(f"[UNIFIED_EXCEL] Failed to post OPEN for {user}: {resp_open.status_code}")
                            
                    except Exception as e:
                        self._log(f"[UNIFIED_EXCEL] Error posting OPEN for {user}: {e}")
                else:
                    self._log(f"[UNIFIED_EXCEL] No work found for {user} ({processing_type})")
                    
            return results
            
        except Exception as e:
            self._log(f"[UNIFIED_EXCEL] Error processing directory for all processors: {e}")
            return {}

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
                if result['aantal_items'] > 0:
                    self._log(f"ACCURA_PROCESSING voltooid: {result['aantal_items']} items, {result['aantal_sides']} sides")
                    self._update_accura_counts_in_db(
                        project_code, user_type,
                        result['aantal_items'],
                        result['aantal_sides'],
                        timestamp
                    )
                    self._log_import_event(user_type, project_code,
                        f"ACCURA_PROCESSING voltooid: {result['aantal_items']} items, {result['aantal_sides']} sides")
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
            if result and (result.get('mo_number') or result.get('customer_name')):
                self._update_project_metadata(
                    project_code, 
                    result.get('mo_number'),
                    result.get('so_number'),
                    result.get('customer_name')
                )
                
        except Exception as e:
            self._log(f"Fout bij {processing_type} voor {user_type}: {e}")
            self.logger.error(f"{processing_type} error: {e}")
            import traceback
            traceback.print_exc()

    def _update_project_metadata(self, project_code, mo_number, so_number, customer_name):
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
                'customer_name': customer_name
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

            # Update item count via a direct database update
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

    def _execute_hops_import_with_stats(self, user_type, project_code, event_details, timestamp, directory_path):
        """Execute HOPS processing with stats tracking."""
        try:
            with BackgroundImportService._stats_lock:
                self.stats['hops_imports_triggered'] += 1
                self.stats['total_imports_triggered'] += 1
            
            self._log(f"HOPS_PROCESSING gestart voor user '{user_type}', project '{project_code}', directory: {directory_path}")
            
            # HOPS processing implementation would go here
            # For now, just log the event
            self._log_import_event(user_type, project_code, 
                f"HOPS_PROCESSING voltooid voor directory: {directory_path}")
                
        except Exception as e:
            self._log(f"Fout bij HOPS_PROCESSING voor {user_type}: {e}")
            self.logger.error(f"HOPS_PROCESSING error: {e}")

    def _execute_mdb_import_with_stats(self, user_type, project_code, event_details, timestamp, directory_path):
        """Execute MDB processing with stats tracking."""
        try:
            with BackgroundImportService._stats_lock:
                self.stats['mdb_imports_triggered'] += 1
                self.stats['total_imports_triggered'] += 1
            
            self._log(f"MDB_PROCESSING gestart voor user '{user_type}', project '{project_code}', directory: {directory_path}")
            
            # MDB processing implementation would go here
            # For now, just log the event
            self._log_import_event(user_type, project_code, 
                f"MDB_PROCESSING voltooid voor directory: {directory_path}")
                
        except Exception as e:
            self._log(f"Fout bij MDB_PROCESSING voor {user_type}: {e}")
            self.logger.error(f"MDB_PROCESSING error: {e}")

    def _log(self, message):
        """Log een bericht naar de logger en callback."""
        if self.logger:
            self.logger.info(message)
        if self.log_callback:
            self.log_callback(message)