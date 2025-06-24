#!/usr/bin/env python3
# translation_utils.py - Translation Management Utilities
"""
Utility script for managing translations in the Enterprise File Monitor application.

Usage:
    python translation_utils.py [command] [options]

Commands:
    stats       - Show translation statistics
    missing     - Show missing translations
    export      - Export translations to JSON files
    import      - Import translations from JSON files
    validate    - Validate translation completeness
    add         - Add new translation key
    
Examples:
    python translation_utils.py stats
    python translation_utils.py missing
    python translation_utils.py export --lang nl --file dutch_translations.json
    python translation_utils.py import --file new_translations.json
    python translation_utils.py add --key "new_feature" --en "New Feature" --nl "Nieuwe Functie"
"""

import sys
import json
import argparse
from pathlib import Path

# Import our translations module
from translations import (
    validate_translations, 
    get_missing_translations,
    export_translations_to_file,
    import_translations_from_file,
    add_translations,
    TRANSLATIONS
)

def print_stats():
    """Print translation statistics"""
    stats = validate_translations()
    
    if 'error' in stats:
        print(f"❌ Error: {stats['error']}")
        return
    
    print("📊 Translation Statistics")
    print("=" * 50)
    print(f"Total translation keys: {stats['total_keys']}")
    print()
    
    for lang_code, info in stats['languages'].items():
        flag = "🇺🇸" if lang_code == 'en' else "🇳🇱" if lang_code == 'nl' else "🏳️"
        status = "✅" if info['coverage'] == 100 else "⚠️" if info['coverage'] >= 80 else "❌"
        
        print(f"{flag} {lang_code.upper()}: {info['count']} keys ({info['coverage']}%) {status}")
    
    # Show missing translations summary
    missing = stats.get('missing_translations', {})
    if missing:
        print("\n🔍 Missing Translations Summary:")
        for lang_code, missing_keys in missing.items():
            print(f"  {lang_code}: {len(missing_keys)} missing")

def print_missing():
    """Print detailed missing translations"""
    missing = get_missing_translations()
    
    if not missing:
        print("✅ All translations are complete!")
        return
    
    print("🔍 Missing Translations")
    print("=" * 50)
    
    for lang_code, missing_keys in missing.items():
        flag = "🇳🇱" if lang_code == 'nl' else "🏳️"
        print(f"\n{flag} {lang_code.upper()} ({len(missing_keys)} missing):")
        
        for key in sorted(missing_keys):
            # Show English value for reference
            en_value = TRANSLATIONS.get('en', {}).get(key, 'N/A')
            print(f"  • {key}: \"{en_value}\"")

def export_translations(lang_code=None, filename=None):
    """Export translations to file"""
    if not filename:
        if lang_code:
            filename = f"translations_{lang_code}.json"
        else:
            filename = "all_translations.json"
    
    try:
        export_translations_to_file(filename, lang_code)
        print(f"✅ Translations exported to: {filename}")
        
        # Show what was exported
        if lang_code:
            count = len(TRANSLATIONS.get(lang_code, {}))
            print(f"   📄 Exported {count} {lang_code.upper()} translations")
        else:
            total = sum(len(trans) for trans in TRANSLATIONS.values())
            print(f"   📄 Exported {total} translations across {len(TRANSLATIONS)} languages")
            
    except Exception as e:
        print(f"❌ Export failed: {e}")

def import_translations(filename):
    """Import translations from file"""
    if not Path(filename).exists():
        print(f"❌ File not found: {filename}")
        return
    
    try:
        success = import_translations_from_file(filename)
        if success:
            print(f"✅ Translations imported from: {filename}")
        else:
            print(f"❌ Import failed for: {filename}")
    except Exception as e:
        print(f"❌ Import error: {e}")

def add_translation(key, translations_dict):
    """Add a new translation key"""
    try:
        add_translations({
            lang: {key: value} 
            for lang, value in translations_dict.items()
        })
        print(f"✅ Added translation key: '{key}'")
        for lang, value in translations_dict.items():
            print(f"   {lang}: \"{value}\"")
    except Exception as e:
        print(f"❌ Failed to add translation: {e}")

def validate():
    """Validate translations and show detailed report"""
    stats = validate_translations()
    
    if 'error' in stats:
        print(f"❌ Error: {stats['error']}")
        return
    
    print("🔍 Translation Validation Report")
    print("=" * 50)
    
    # Overall status
    all_complete = all(info['coverage'] == 100 for info in stats['languages'].values())
    if all_complete:
        print("✅ All translations are complete!")
    else:
        print("⚠️ Some translations are incomplete")
    
    print(f"\n📊 Summary:")
    print(f"   Total keys: {stats['total_keys']}")
    print(f"   Languages: {len(stats['languages'])}")
    
    # Detailed breakdown
    print(f"\n📋 Language Breakdown:")
    for lang_code, info in stats['languages'].items():
        flag = "🇺🇸" if lang_code == 'en' else "🇳🇱" if lang_code == 'nl' else "🏳️"
        status_icon = "✅" if info['coverage'] == 100 else "⚠️" if info['coverage'] >= 80 else "❌"
        
        missing_count = stats['total_keys'] - info['count']
        print(f"   {flag} {lang_code.upper()}: {info['count']}/{stats['total_keys']} keys ({info['coverage']}%) {status_icon}")
        
        if missing_count > 0:
            print(f"      Missing: {missing_count} keys")

def create_template():
    """Create a translation template file"""
    template = {
        "instructions": "Fill in the translations for each key. Remove this instructions key when done.",
        "example_format": {
            "en": "English translation",
            "nl": "Dutch translation"
        }
    }
    
    # Add all English keys as a template
    missing = get_missing_translations()
    if 'nl' in missing:
        template['missing_dutch_translations'] = {}
        for key in missing['nl']:
            en_value = TRANSLATIONS.get('en', {}).get(key, '')
            template['missing_dutch_translations'][key] = {
                "en": en_value,
                "nl": "TODO: Add Dutch translation"
            }
    
    filename = "translation_template.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(template, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Created translation template: {filename}")
    if 'nl' in missing:
        print(f"   📝 Template includes {len(missing['nl'])} missing Dutch translations")

def main():
    parser = argparse.ArgumentParser(
        description="Translation management utilities for Enterprise File Monitor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Stats command
    subparsers.add_parser('stats', help='Show translation statistics')
    
    # Missing command
    subparsers.add_parser('missing', help='Show missing translations')
    
    # Validate command
    subparsers.add_parser('validate', help='Validate translation completeness')
    
    # Template command
    subparsers.add_parser('template', help='Create translation template file')
    
    # Export command
    export_parser = subparsers.add_parser('export', help='Export translations to JSON file')
    export_parser.add_argument('--lang', help='Language code to export (default: all)')
    export_parser.add_argument('--file', help='Output filename')
    
    # Import command
    import_parser = subparsers.add_parser('import', help='Import translations from JSON file')
    import_parser.add_argument('--file', required=True, help='Input filename')
    
    # Add command
    add_parser = subparsers.add_parser('add', help='Add new translation key')
    add_parser.add_argument('--key', required=True, help='Translation key')
    add_parser.add_argument('--en', required=True, help='English translation')
    add_parser.add_argument('--nl', help='Dutch translation')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    print("🌐 Enterprise File Monitor - Translation Utils")
    print()
    
    try:
        if args.command == 'stats':
            print_stats()
        elif args.command == 'missing':
            print_missing()
        elif args.command == 'validate':
            validate()
        elif args.command == 'template':
            create_template()
        elif args.command == 'export':
            export_translations(args.lang, args.file)
        elif args.command == 'import':
            import_translations(args.file)
        elif args.command == 'add':
            translations_dict = {'en': args.en}
            if args.nl:
                translations_dict['nl'] = args.nl
            add_translation(args.key, translations_dict)
    
    except KeyboardInterrupt:
        print("\n\n⚡ Operation cancelled by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")

if __name__ == '__main__':
    main()