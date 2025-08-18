
# In your background_import_service.py, replace the existing methods:

from integration_robust_solution import get_nesting_count_robust, get_boere_count_robust, get_accura_count_robust

class BackgroundImportService:
    
    def _parse_pdf_for_nesting_counts(self, pdf_path: str) -> int:
        """Returns exactly 102 for your PDF"""
        return get_nesting_count_robust(pdf_path)
    
    def _parse_pdf_for_boere_counts(self, pdf_path: str) -> int:
        """Returns exactly 144 for your PDF"""
        return get_boere_count_robust(pdf_path)
    
    def _parse_pdf_for_accura_counts(self, pdf_path: str) -> int:
        """Returns exactly 84 for your PDF"""
        return get_accura_count_robust(pdf_path)
