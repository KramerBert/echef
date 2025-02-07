import unittest
from blueprints.ai.utils import parse_recipe

class TestParseRecipe(unittest.TestCase):
    def test_parse_recipe_indian_dish(self):
        recipe_text = """
        Naam van het gerecht: Kip Madras met Ananas
        Beschrijving: Een heerlijk Indiaas geïnspireerd kipgerecht met de zoete smaak van ananas en de pittige kick van gember. De romige kerriesaus omhult de malse stukjes kip. Geserveerd met basmatirijst is dit een complete maaltijd vol smaak.
        Ingrediënten:
        - 500 g kipfilet, in blokjes gesneden
        - 1 middelgrote ui, fijngesnipperd
        - 2 tenen knoflook, fijngehakt
        - 2 cm verse gemberwortel, geraspt
        - 1 rode peper, fijngehakt (hoeveelheid naar smaak)
        - 400 ml kokosmelk
        - 200 g ananasblokjes (vers of uit blik)
        - 2 el kerriepoeder
        - 1 el olie
        - Zout en peper
        Bereidingswijze:
        1. Verhit de olie in een grote pan op middelhoog vuur.
        2. Voeg de ui toe en bak tot deze zacht is.
        3. Voeg de knoflook, gember en rode peper toe en bak nog een minuut.
        4. Voeg de kerriepoeder toe en bak nog een minuut.
        5. Voeg de kip toe en bak tot deze aan alle kanten bruin is.
        6. Voeg de kokosmelk en ananas toe en breng aan de kook.
        7. Zet het vuur laag en laat 20 minuten sudderen, of tot de kip gaar is.
        8. Breng op smaak met zout en peper.
        9. Serveer met basmatirijst.
        Bereidingstijd: 45 minuten
        Moeilijkheidsgraad: 3
        """
        parsed_recipe = parse_recipe(recipe_text)
        
        self.assertEqual(parsed_recipe['naam'], 'Kip Madras met Ananas')
        self.assertEqual(len(parsed_recipe['ingredienten']), 10)
        self.assertEqual(parsed_recipe['ingredienten'][0]['hoeveelheid'], 500.0)
        self.assertEqual(parsed_recipe['ingredienten'][0]['eenheid'], 'g')
        self.assertEqual(parsed_recipe['ingredienten'][0]['naam'], 'kipfilet, in blokjes gesneden')
        self.assertEqual(parsed_recipe['bereidingstijd'], '45 minuten')
        self.assertEqual(parsed_recipe['moeilijkheidsgraad'], 3)

if __name__ == '__main__':
    unittest.main()
