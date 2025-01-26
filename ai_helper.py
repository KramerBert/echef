from openai import OpenAI
import json

class RecipeAssistant:
    def __init__(self, api_key):
        self.client = OpenAI(api_key=api_key)

    def generate_recipe(self, prompt):
        system_prompt = """
        Je bent een professionele chef-kok die recepten maakt. 
        Genereer een gedetailleerd recept in het Nederlands met de volgende onderdelen:
        - Titel
        - Lijst met ingrediënten (met hoeveelheden)
        - Stapsgewijze bereidingsinstructies
        Output format moet JSON zijn met de structuur:
        {
            "title": "Titel van het gerecht",
            "ingredients": ["ingredient 1", "ingredient 2", ...],
            "instructions": ["stap 1", "stap 2", ...]
        }
        """

        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )

        try:
            recipe_data = json.loads(response.choices[0].message.content)
            return recipe_data
        except json.JSONDecodeError:
            return None
