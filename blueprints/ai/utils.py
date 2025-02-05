import re

def parse_recipe(recipe_text):
    """Parse het gegenereerde recept naar een gestructureerd formaat"""
    sections = {
        'naam': '',
        'beschrijving': '',
        'ingredienten': [],
        'bereidingswijze': [],
        'bereidingstijd': '',
        'moeilijkheidsgraad': 0
    }
    
    # Extraheer naam (eerste regel)
    lines = recipe_text.split('\n')
    if lines:
        sections['naam'] = lines[0].replace('Naam van het gerecht:', '').strip()
    
    # Parse ingrediënten (regels die beginnen met - of •)
    ingredient_pattern = r'[-•]\s*([\d.,]+)\s*([\w\s()]+)\s+(.*)'
    for line in lines:
        match = re.match(ingredient_pattern, line.strip())
        if match:
            hoeveelheid, eenheid, naam = match.groups()
            sections['ingredienten'].append({
                'hoeveelheid': float(hoeveelheid.replace(',', '.')),
                'eenheid': eenheid.strip(),
                'naam': naam.strip()
            })
    
    # Extract bereidingswijze (regels die beginnen met een nummer)
    step_pattern = r'^\d+\.\s+(.+)'
    for line in lines:
        match = re.match(step_pattern, line.strip())
        if match:
            sections['bereidingswijze'].append(match.group(1))
    
    return sections
