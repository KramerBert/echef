UPDATE allergenen SET icon_class = CASE 
    WHEN naam LIKE '%Gluten%' THEN 'fa-bread-slice'
    WHEN naam LIKE '%Schaaldieren%' THEN 'fa-shrimp'
    WHEN naam LIKE '%Eieren%' THEN 'fa-egg'
    WHEN naam LIKE '%Vis%' THEN 'fa-fish'
    WHEN naam LIKE '%Pinda%' THEN 'fa-seedling'
    WHEN naam LIKE '%Soja%' THEN 'fa-seedling'
    WHEN naam LIKE '%Melk%' THEN 'fa-cow'
    WHEN naam LIKE '%Noten%' THEN 'fa-apple-whole'
    WHEN naam LIKE '%Selderij%' THEN 'fa-carrot'
    WHEN naam LIKE '%Mosterd%' THEN 'fa-bottle-droplet'
    WHEN naam LIKE '%Sesamzaad%' THEN 'fa-seedling'
    WHEN naam LIKE '%Sulfiet%' THEN 'fa-flask'
    WHEN naam LIKE '%Lupine%' THEN 'fa-leaf'
    WHEN naam LIKE '%Weekdieren%' THEN 'fa-water'
    ELSE 'fa-circle-exclamation'
END;
