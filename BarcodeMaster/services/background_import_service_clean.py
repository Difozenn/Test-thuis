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
            # Keep existing HOPS logic (not shown here for brevity)
            pass
            
        elif processing_type == 'MDB_PROCESSING':
            # Keep existing MDB logic (not shown here for brevity)
            pass
            
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

    def _log(self, message):
        """Log een bericht naar de logger en callback."""
        if self.logger:
            self.logger.info(message)
        if self.log_callback:
            self.log_callback(message)

    def _log_import_event(self, user_type, project_code, details):
        """Log een import event."""
        self._log(f"Import event: User={user_type}, Project={project_code}, Details={details}")

    def _update_open_event_with_nesting_counts(self, user_type, project_code, nesting_count, opdeelzaag_count):
        """Update OPEN event with nesting counts."""
        # Implementation would go here
        pass

    def _update_accura_counts_in_db(self, project_code, user_type, aantal_items, aantal_sides, timestamp):
        """Update ACCURA counts in database."""
        # Implementation would go here
        pass

    def _update_boere_count_in_db(self, project_code, user_type, item_count, timestamp):
        """Update BOERE count in database."""
        # Implementation would go here
        pass