# This file contains the modified functions for Excel processing in background_import_service.py
# Replace the corresponding functions in the original file

# Add this import at the top of background_import_service.py:
# from .excel_processing_functions import (
#     find_excel_file_for_project, 
#     parse_excel_for_nesting, 
#     parse_excel_for_accura, 
#     parse_excel_for_boere,
#     process_excel_for_all_types
# )

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
        # Keep existing HOPS logic...
        # [Previous HOPS code remains the same]
        pass
        
    elif processing_type == 'MDB_PROCESSING':
        # Keep existing MDB logic...
        # [Previous MDB code remains the same]
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
        
        # Process results for each user
        for user, result in results.items():
            if result['has_work']:
                processing_type = excel_processors[user]
                self._log(f"[UNIFIED_EXCEL] Work found for {user} ({processing_type})")
                
                # Send OPEN event and update counts
                data_open = {
                    'event': 'OPEN',
                    'details': f"Excel processing for {processing_type}",
                    'project': project_code_to_log,
                    'base_mo_code': base_project_code,
                    'user': user,
                    'timestamp': timestamp
                }
                
                try:
                    resp = requests.post(api_url, json=data_open, timeout=3)
                    if resp.ok:
                        self._log(f"[UNIFIED_EXCEL] Successfully posted OPEN for {project_code_to_log} for user {user}")
                        
                        # Update counts based on processing type
                        if processing_type == 'ACCURA_PROCESSING':
                            self._update_accura_counts_in_db(
                                project_code_to_log, user,
                                result['aantal_items'],
                                result['aantal_sides'],
                                timestamp
                            )
                        elif processing_type == 'BOERE_PROCESSING':
                            self._update_boere_count_in_db(
                                project_code_to_log, user,
                                result['item_count'],
                                timestamp
                            )
                        elif processing_type == 'NESTING_PROCESSING':
                            self._update_open_event_with_nesting_counts(
                                user, project_code_to_log,
                                result['nesting_count'],
                                result['opdeelzaag_count']
                            )
                        
                        # Update metadata if available
                        if result.get('mo_number') or result.get('customer_name'):
                            self._update_project_metadata(
                                project_code_to_log,
                                result.get('mo_number'),
                                result.get('so_number'),
                                result.get('customer_name')
                            )
                            
                except Exception as e:
                    self._log(f"[UNIFIED_EXCEL] Error posting OPEN event: {e}")
                    
        return results
        
    except Exception as e:
        self._log(f"[UNIFIED_EXCEL] Error processing directory: {e}")
        import traceback
        traceback.print_exc()
        return {}


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