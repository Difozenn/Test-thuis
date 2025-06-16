"""
Background Import Service voor BarcodeMaster
Automatische monitoring en verwerking van OPUS en GANNOMAT bestanden
"""

import os
import time
import threading
import time
import os
import pandas as pd
import pyodbc
import requests
import re
from datetime import datetime
import sqlite3
import json
import logging

from BarcodeMaster.config_utils import get_config

class BackgroundImportService:
    _stats_lock = threading.Lock() # Class level lock for stats
    """Service voor automatische import getriggerd door OPEN events."""
    
    def __init__(self, log_callback=None):
        self.log_callback = log_callback
        self.logger = None # Initialized in _setup_logging
        
        # Configuration holders
        # self.master_service_globally_active = False # Removed master switch
        self.scanner_users = []
        self.scanner_user_paths = {}
        self.scanner_user_logic_active = {}
        self.scanner_user_to_processing_type_map = {} # New map

        # Statistics tracking
        self.stats = {
            'opus_imports_triggered': 0,
            'gannomat_imports_triggered': 0,
            'total_imports_triggered': 0 # Added for convenience
        }
        
        self.load_config() # Load initial configuration
        self._setup_logging() # Setup logger
        
    def _setup_logging(self):
        """Setup logging voor de service."""
        log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
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
                # self.logger.info(f"Master service globally active: {self.master_service_globally_active}") # Removed
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
            # self.master_service_globally_active = False # Removed
            self.scanner_users = []
            self.scanner_user_paths = {}
            self.scanner_user_logic_active = {}
            self.scanner_user_to_processing_type_map = {}
            
    def is_enabled(self):
        """Controleer of de automatische import functionaliteit is ingeschakeld.
        Nu de master switch is verwijderd, is de service altijd 'enabled' om user-specific logic te checken."""
        return True # Service is always ready to check user-specific logic

    # is_service_explicitly_enabled removed as it's redundant without master_service_globally_active
        
    def get_status(self):
        """Krijg huidige status van de import functionaliteit."""
        # Config is loaded on init and when settings are saved.
        # No need to reload on every status check.

        opus_monitored = (
            'OPUS' in self.scanner_users and 
            self.scanner_user_logic_active.get('OPUS', False) and 
            bool(self.scanner_user_paths.get('OPUS'))
        )
        gannomat_monitored = (
            'GANNOMAT' in self.scanner_users and 
            self.scanner_user_logic_active.get('GANNOMAT', False) and 
            bool(self.scanner_user_paths.get('GANNOMAT'))
        )

        return {
            'service_enabled': True, # Service is always considered enabled now
            'opus_monitoring': opus_monitored,
            'gannomat_monitoring': gannomat_monitored,
            'opus_imports_triggered': self.stats['opus_imports_triggered'],
            'gannomat_imports_triggered': self.stats['gannomat_imports_triggered'],
            'total_imports_triggered': self.stats['total_imports_triggered']
        }
        

        
    def trigger_import_for_event(self, user_type, project_code, event_details, timestamp):
        """Verwerk een OPEN event en trigger automatische import indien nodig."""
        self.load_config() # Ensure config is up-to-date
        # if not self.is_enabled(): # Removed master switch check
        #     self._log("Automatische import is niet ingeschakeld (master switch).")
        #     return

        self._log(f"Event ontvangen: User={user_type}, Project={project_code}. Controleren voor import...")
        
        import_triggered_for_user = False
        processing_type = self.scanner_user_to_processing_type_map.get(user_type)

        if not self.scanner_user_logic_active.get(user_type, False):
            self._log(f"{user_type} import overgeslagen: logica niet actief voor deze gebruiker in ScannerPanel config (scanner_panel_open_event_user_logic_active).")
            return

        if processing_type == 'GEEN_PROCESSING':
            self._log(f"'{user_type}' is geconfigureerd voor 'GEEN_PROCESSING'. Specifieke importlogica wordt overgeslagen.")
            # The ScannerPanel.log_scan_event will still handle the database logging for OPEN events.
            # This service's role is the automated file import, which is bypassed here.
            return

        user_specific_path = self.scanner_user_paths.get(user_type)
        if not user_specific_path or not os.path.isdir(user_specific_path):
            self._log(f"{user_type} import overgeslagen: pad niet ingesteld of ongeldig ('{user_specific_path}') in scanner_panel_open_event_user_paths.")
            return

        if processing_type == 'HOPS_PROCESSING':
            # Extract subfolder name from event_details for OPUS type processing
            match = re.search(r"Scan event: (.*)$", event_details)
            if match:
                subfolder_name = match.group(1).strip()
                specific_opus_subfolder_path = os.path.join(user_specific_path, subfolder_name)

                if os.path.isdir(specific_opus_subfolder_path):
                    self._log(f"HOPS_PROCESSING (voor {user_type}) wordt gestart (in achtergrond thread) voor specifieke map: {specific_opus_subfolder_path}")
                    thread = threading.Thread(target=self._execute_opus_import_with_stats, args=(project_code, event_details, timestamp, specific_opus_subfolder_path))
                    thread.start()
                    import_triggered_for_user = True
                else:
                    self._log(f"HOPS_PROCESSING (voor {user_type}) overgeslagen: specifieke projectmap niet gevonden: '{specific_opus_subfolder_path}'.")
                    self._log(f"  Event details: \"{event_details}\", Basis pad: \"{user_specific_path}\", Geëxtraheerde submap: \"{subfolder_name}\"")
            else:
                self._log(f"HOPS_PROCESSING (voor {user_type}) overgeslagen: kon project submap naam niet extraheren. Details: \"{event_details}\"")
                
        elif processing_type == 'MDB_PROCESSING':
            self._log(f"MDB_PROCESSING (voor {user_type}) wordt gestart (in achtergrond thread). Pad: {user_specific_path}")
            thread = threading.Thread(target=self._execute_gannomat_import_with_stats, args=(project_code, event_details, timestamp, user_specific_path))
            thread.start()
            import_triggered_for_user = True
        
        elif processing_type:
            self._log(f"Onbekend processing_type '{processing_type}' geconfigureerd voor gebruiker '{user_type}'. Geen import actie.")
        else:
            self._log(f"Geen processing_type geconfigureerd voor gebruiker '{user_type}' in scanner_user_to_processing_type_map. Geen import actie.")

        # The detailed success log and total_imports_triggered stat update will now happen within the thread
        # if import_triggered_for_user:
        #     # This part is moved to the wrapper methods for threaded execution
        #     # self.stats['total_imports_triggered'] += 1 
        #     self._log(f"Import succesvol getriggerd voor {user_type}. Totaal: {self.stats['total_imports_triggered']}")

    # start() method removed as it was tied to the global master switch.
    # The service is now always 'running' in the sense that it's ready to process events based on user-specific configs.

    def _execute_opus_import_with_stats(self, project_code, event_details, timestamp, specific_opus_subfolder_path):
        try:
            self._trigger_opus_import(project_code, event_details, timestamp, specific_opus_subfolder_path)
            with BackgroundImportService._stats_lock:
                self.stats['opus_imports_triggered'] += 1
                self.stats['total_imports_triggered'] += 1
            self._log(f"OPUS import thread voltooid. Totaal OPUS: {self.stats['opus_imports_triggered']}, Totaal: {self.stats['total_imports_triggered']}")
        except Exception as e:
            self.logger.error(f"Fout in OPUS import thread: {e}")
            self._log(f"Fout in OPUS import thread: {e}")

    def _execute_gannomat_import_with_stats(self, project_code, event_details, timestamp, gannomat_path):
        try:
            self._trigger_gannomat_import(project_code, event_details, timestamp, gannomat_path)
            with BackgroundImportService._stats_lock:
                self.stats['gannomat_imports_triggered'] += 1
                self.stats['total_imports_triggered'] += 1
            self._log(f"GANNOMAT import thread voltooid. Totaal GANNOMAT: {self.stats['gannomat_imports_triggered']}, Totaal: {self.stats['total_imports_triggered']}")
        except Exception as e:
            self.logger.error(f"Fout in GANNOMAT import thread: {e}")
            self._log(f"Fout in GANNOMAT import thread: {e}")

    # stop() method removed as it was tied to the global master switch.

    def _trigger_opus_import(self, project_event_code, details, timestamp, opus_scan_path):
        """Trigger automatische OPUS import en Excel generatie voor .hop/.hops bestanden in de gespecificeerde map."""
        self._log(f"OPUS import gestart voor project context: {project_event_code} in map: {opus_scan_path}")

        if not opus_scan_path or not os.path.isdir(opus_scan_path):
            self._log(f"OPUS directory niet gevonden of ongeldig: {opus_scan_path}")
            self.logger.warning(f"OPUS directory niet gevonden of ongeldig: {opus_scan_path}")
            # self._log_import_event('OPUS', project_event_code, f"Configuratiefout: OPUS map '{opus_scan_path}' ongeldig.")
            return # Crucial return if path is invalid

        try:
            collected_files = self._collect_opus_files_for_report(opus_scan_path)

            if collected_files:
                self._log(f"{len(collected_files)} OPUS (.hop/.hops) bestanden gevonden in '{opus_scan_path}' voor Excel rapportage.")
                self._create_opus_excel_report(collected_files, opus_scan_path)
                # self._log_import_event('OPUS', project_event_code, f"Excel rapport succesvol gegenereerd met {len(collected_files)} bestanden uit {opus_scan_path}.")
            else:
                self._log(f"Geen .hop/.hops bestanden gevonden in OPUS map '{opus_scan_path}' voor Excel rapportage.")
                # self._log_import_event('OPUS', project_event_code, f"Geen .hop/.hops bestanden gevonden in {opus_scan_path} voor Excel.")

        except Exception as e:
            self.logger.error(f"Algemene fout tijdens OPUS import/Excel generatie voor pad {opus_scan_path} (project context: {project_event_code}): {e}")
            self._log(f"Algemene fout OPUS import: {str(e)}")
            # self._log_import_event('OPUS', project_event_code, f"Fout tijdens OPUS verwerking: {str(e)}")
            
    def _find_opus_project_files(self, directory, project):
        """Zoek OPUS bestanden voor een specifiek project."""
        project_files = []
        
        try:
            for root, dirs, files in os.walk(directory):
                for file in files:
                    if file.lower().endswith(('.hop', '.hops')):
                        # Check if project code is in filename
                        if project.upper() in file.upper():
                            file_path = os.path.join(root, file)
                            project_files.append(file_path)
                            
        except Exception as e:
            self.logger.error(f"Fout bij zoeken OPUS bestanden: {e}")
            
        return project_files

    def _collect_opus_files_for_report(self, opus_scan_path):
        """
        Collects all .hop/.hops files from the given path and its subdirectories,
        returning a list of dicts with 'Item' key holding the relative path.
        """
        found_files_data = []
        try:
            for root, _, filenames in os.walk(opus_scan_path):
                for filename in filenames:
                    if filename.lower().endswith(('.hop', '.hops')):
                        full_path = os.path.join(root, filename)
                        relative_path = os.path.relpath(full_path, opus_scan_path)
                        found_files_data.append({'Item': relative_path})
            if found_files_data:
                self._log(f"{len(found_files_data)} .hop/.hops bestanden verzameld uit '{opus_scan_path}'.")
            else:
                self._log(f"Geen .hop/.hops bestanden gevonden in '{opus_scan_path}'.")
        except Exception as e:
            self._log(f"Fout bij verzamelen OPUS bestanden uit '{opus_scan_path}': {e}")
            self.logger.error(f"Error collecting OPUS files from '{opus_scan_path}': {e}")
        return found_files_data

    def _create_opus_excel_report(self, report_data, opus_scan_path):
        """
        Creates an Excel file from the OPUS file data.
        report_data is a list of dicts, each with an 'Item' key (relative path).
        opus_scan_path is the full path to the scanned OPUS directory.
        """
        try:
            # pandas should be imported at the top of the file
            pass
        except ImportError:
            self._log("Pandas is niet geïnstalleerd. Kan geen OPUS Excel rapport genereren.")
            self.logger.error("Pandas is niet geïnstalleerd. Kan geen OPUS Excel rapport genereren.")
            return

        if not report_data:
            self._log(f"Geen data om op te slaan in Excel voor OPUS map '{opus_scan_path}'.")
            return

        try:
            df = pd.DataFrame(report_data)
            
            # Ensure 'Item' and 'Status' columns, similar to BarcodeMatch
            if 'Item' not in df.columns:
                 # This case should ideally not happen if _collect_opus_files_for_report works correctly
                self._log(f"Waarschuwing: 'Item' kolom ontbreekt in OPUS data voor Excel. Exporteren wat beschikbaar is.")
                df['Item'] = "Unknown"

            if 'Status' not in df.columns:
                df['Status'] = ''
            
            # Ensure correct column order if necessary, though to_excel usually handles it.
            # df = df[['Item', 'Status']] # Uncomment if specific order is strictly needed

            folder_name = os.path.basename(os.path.normpath(opus_scan_path))
            excel_path = os.path.join(opus_scan_path, f"{folder_name}.xlsx")

            df.to_excel(excel_path, index=False)
            self._log(f"OPUS Excel rapport succesvol opgeslagen: {excel_path}")
            self.logger.info(f"OPUS Excel report successfully saved: {excel_path}")

        except Exception as e:
            self._log(f"Fout bij opslaan van OPUS Excel rapport voor map '{opus_scan_path}': {e}")
            self.logger.error(f"Error saving OPUS Excel report for directory '{opus_scan_path}': {e}")

    def _trigger_gannomat_import(self, project_event_code, details, timestamp, gannomat_scan_path):
        """Trigger automatische GANNOMAT import en Excel generatie voor .mdb/.accdb bestanden."""
        self._log(f"GANNOMAT import gestart voor project context: {project_event_code} in map: {gannomat_scan_path}")

        if not gannomat_scan_path or not os.path.isdir(gannomat_scan_path):
            self._log(f"GANNOMAT directory niet gevonden of ongeldig: {gannomat_scan_path}")
            self.logger.warning(f"GANNOMAT directory niet gevonden of ongeldig: {gannomat_scan_path}")
            # self._log_import_event('GANNOMAT', project_event_code, f"Configuratiefout: GANNOMAT map '{gannomat_scan_path}' ongeldig.")
            return

        processed_files_count = 0
        excel_reports_generated = 0
        try:
            for filename in os.listdir(gannomat_scan_path):
                if filename.lower().endswith(('.mdb', '.accdb')):
                    db_file_path = os.path.join(gannomat_scan_path, filename)
                    self._log(f"Verwerken GANNOMAT bestand: {db_file_path}")
                    
                    extracted_data = self._extract_raw_gannomat_data_from_db(db_file_path)
                    
                    if extracted_data:
                        self._create_gannomat_excel_report(extracted_data, db_file_path)
                        excel_reports_generated += 1
                        self._log(f"Excel rapport gegenereerd voor {filename}.")
                    else:
                        self._log(f"Geen data geëxtraheerd uit {filename} voor Excel rapportage.")
                    processed_files_count += 1
            
            if processed_files_count > 0:
                self._log(f"{processed_files_count} GANNOMAT bestanden verwerkt. {excel_reports_generated} Excel rapporten gegenereerd in {gannomat_scan_path}.")
                # self._log_import_event('GANNOMAT', project_event_code, f"{excel_reports_generated} Excel rapport(en) gegenereerd uit {processed_files_count} MDB/ACCDB bestand(en) in {gannomat_scan_path}.")
            else:
                self._log(f"Geen .mdb/.accdb bestanden gevonden in GANNOMAT map '{gannomat_scan_path}'.")
                # self._log_import_event('GANNOMAT', project_event_code, f"Geen .mdb/.accdb bestanden gevonden in {gannomat_scan_path}.")

        except Exception as e:
            self.logger.error(f"Algemene fout tijdens GANNOMAT import/Excel generatie voor pad {gannomat_scan_path} (project context: {project_event_code}): {e}")
            self._log(f"Algemene fout GANNOMAT import: {str(e)}")
            # self._log_import_event('GANNOMAT', project_event_code, f"Fout tijdens GANNOMAT verwerking: {str(e)}")

        
    def _extract_raw_gannomat_data_from_db(self, db_path):
        """
        Extracts all ProgramNumbers from a GANNOMAT MDB/ACCDB file,
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

    def _create_gannomat_excel_report(self, report_data, db_path):
        """
        Creates an Excel file from the GANNOMAT data, similar to BarcodeMatch.
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
            # self.logger.info(f"No data to save to Excel for {mdb_basename}.") # Potentially too verbose for file log
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
            excel_path = os.path.join(export_dir, f"{base_name}_GANNOMAT.xlsx")

            df_export.to_excel(excel_path, index=False)
            self._log(f"GANNOMAT Excel rapport succesvol opgeslagen: {excel_path}")
            self.logger.info(f"GANNOMAT Excel report successfully saved: {excel_path}")

        except Exception as e:
            self._log(f"Fout bij opslaan van GANNOMAT Excel rapport voor {mdb_basename}: {e}")
            self.logger.error(f"Error saving GANNOMAT Excel report for {mdb_basename}: {e}")

    def _find_gannomat_project_data(self, directory, project):
        """Zoek GANNOMAT data voor een specifiek project."""
        project_data = []
        
        try:
            # Look for .mdb/.accdb files
            for file in os.listdir(directory):
                if file.lower().endswith(('.mdb', '.accdb')):
                    db_path = os.path.join(directory, file)
                    
                    # Try to query database for project data
                    try:
                        import pyodbc
                        
                        # Connection string for Access database
                        conn_str = f'DRIVER={{Microsoft Access Driver (*.mdb, *.accdb)}};DBQ={db_path};'
                        
                        with pyodbc.connect(conn_str) as conn:
                            cursor = conn.cursor()
                            
                            # Try common table names and search for project
                            tables = ['Projects', 'Orders', 'Jobs', 'Data']
                            
                            for table in tables:
                                try:
                                    query = f"SELECT * FROM {table} WHERE * LIKE '%{project}%'"
                                    cursor.execute(query)
                                    rows = cursor.fetchall()
                                    
                                    if rows:
                                        project_data.extend(rows)
                                        
                                except:
                                    continue  # Table might not exist
                                    
                    except ImportError:
                        self._log("pyodbc niet beschikbaar voor GANNOMAT database toegang")
                    except Exception as e:
                        self.logger.error(f"Fout bij lezen GANNOMAT database {db_path}: {e}")
                        
        except Exception as e:
            self.logger.error(f"Fout bij zoeken GANNOMAT data: {e}")
            
        return project_data
        
    def _process_opus_files(self, files, project):
        """Verwerk gevonden OPUS bestanden."""
        self._log(f"Verwerking van {len(files)} OPUS bestanden voor project {project}")
        
        try:
            # Extract project code with _REP_ handling (consistent with scanner panel)
            project_code = self._extract_project_code(project)
            
            # Process each file
            for file_path in files:
                self._log(f"Verwerking OPUS bestand: {os.path.basename(file_path)}")
                
                # Here you would implement the actual matching logic
                # For now, just log the action
                self._log_import_event('OPUS', project_code, f"Automatische import van {os.path.basename(file_path)}")
                
        except Exception as e:
            self.logger.error(f"Fout bij verwerken OPUS bestanden: {e}")
            self._log(f"Fout bij verwerken OPUS bestanden: {str(e)}")
            
    def _process_gannomat_data(self, data, project):
        """Verwerk gevonden GANNOMAT data."""
        self._log(f"Verwerking van GANNOMAT data voor project {project}")
        
        try:
            # Extract project code with _REP_ handling (consistent with scanner panel)
            project_code = self._extract_project_code(project)
            
            # Process the data
            self._log(f"Verwerking {len(data)} GANNOMAT records")
            
            # Here you would implement the actual matching logic
            # For now, just log the action
            self._log_import_event('GANNOMAT', project_code, f"Automatische import van {len(data)} database records")
            
        except Exception as e:
            self.logger.error(f"Fout bij verwerken GANNOMAT data: {e}")
            self._log(f"Fout bij verwerken GANNOMAT data: {str(e)}")
            
    def _extract_project_code(self, code):
        """Extract project code met _REP_ handling (consistent met scanner panel)."""
        project_code = code  # Default to full code
        
        # Try to extract project code using standard pattern
        match = re.search(r'_([A-Z]{2}\d+)_', code)
        if match:
            project_code = match.group(1)
        
        # Dynamic logic for handling _REP_ project codes (case insensitive)
        code_upper = code.upper()
        if "_REP_" in code_upper or "_REP" in code_upper:
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
