import re
from bs4 import BeautifulSoup
import json

def parse_recipe(recipe_text):
    """Parse het gegenereerde recept naar een gestructureerd formaat"""
    # Verwijder HTML tags
    soup = BeautifulSoup(recipe_text, 'html.parser')
    recipe_text = soup.get_text()

    sections = {
        'naam': '',
        'beschrijving': '',
        'ingredienten': [],
        'bereidingswijze': [],
    }
    
    # Split the recipe text into sections based on headings
    parts = re.split(r'(Naam van het gerecht:|Ingrediënten:|Bereidingswijze:|Beschrijving:)', recipe_text, flags=re.IGNORECASE)
    
    # Assign values to sections based on the split parts
    for i in range(1, len(parts), 2):
        heading = parts[i].strip().lower()
        content = parts[i+1].strip()
        
        if heading == 'naam van het gerecht:':
            sections['naam'] = content
        elif heading == 'beschrijving:':
            sections['beschrijving'] = content
        elif heading == 'ingrediënten:':
            ingredient_pattern = r'[-•]\s*(.*)'
            for line in content.split('\n'):
                match = re.match(ingredient_pattern, line.strip())
                if match:
                    naam = match.group(1).strip()
                    sections['ingredienten'].append({
                        'naam': naam,
                        'hoeveelheid': None,
                        'eenheid': None
                    })
        elif heading == 'bereidingswijze:':
            step_pattern = r'^\d+\.\s+(.+)'
            for line in content.split('\n'):
                match = re.match(step_pattern, line.strip())
                if match:
                    sections['bereidingswijze'].append(match.group(1))
                else:
                    sections['bereidingswijze'].append(line.strip())
    
    return sections
