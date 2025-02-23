import os
import re
from pathlib import Path

def scan_for_references(search_path, filename):
    """Zoek naar referenties naar een bestand in alle project bestanden"""
    references = []
    
    # Converteer filename naar verschillende notaties die gebruikt kunnen worden
    filename_variants = [
        filename,
        filename.replace('\\', '/'),
        os.path.basename(filename),
        os.path.splitext(os.path.basename(filename))[0]
    ]
    
    # Loop door alle bestanden
    for root, _, files in os.walk(search_path):
        for file in files:
            if file.endswith(('.py', '.html', '.js', '.css')):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # Zoek naar alle varianten van de bestandsnaam
                        for variant in filename_variants:
                            if variant in content:
                                references.append(file_path)
                                break
                except Exception as e:
                    print(f"Fout bij lezen van {file_path}: {e}")
    
    return references

def main():
    project_root = "c:/echef"  # Pas dit aan naar je project root
    
    # Mappen die we willen scannen
    dirs_to_scan = [
        'static',
        'templates',
        'uploads'
    ]
    
    # Bestanden/extensies die we willen negeren
    ignore_patterns = [
        '__pycache__',
        '.git',
        '.pytest_cache',
        '.venv',
        '.env',
        'node_modules'
    ]
    
    print("Start scan voor mogelijk overbodige bestanden...")
    
    for dir_name in dirs_to_scan:
        dir_path = os.path.join(project_root, dir_name)
        if not os.path.exists(dir_path):
            print(f"Map niet gevonden: {dir_path}")
            continue
            
        print(f"\nScan map: {dir_path}")
        
        # Loop door alle bestanden in de map
        for root, _, files in os.walk(dir_path):
            # Skip genegeerde mappen
            if any(ignore in root for ignore in ignore_patterns):
                continue
                
            for file in files:
                file_path = os.path.join(root, file)
                refs = scan_for_references(project_root, file)
                
                if not refs:
                    size = os.path.getsize(file_path)
                    print(f"\n🔍 Mogelijk overbodig: {file_path}")
                    print(f"   Grootte: {size/1024:.1f}KB")
                    print(f"   Geen referenties gevonden")
                else:
                    print(f"\n✅ In gebruik: {file_path}")
                    print(f"   Gevonden in {len(refs)} bestand(en):")
                    for ref in refs[:3]:  # Toon max 3 referenties
                        print(f"   - {ref}")
                    if len(refs) > 3:
                        print(f"   ... en {len(refs)-3} meer")

if __name__ == "__main__":
    main()
