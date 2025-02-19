-- Verwijder alle bestaande koppelingen en data
DROP TABLE IF EXISTS dish_dieten;
DROP TABLE IF EXISTS dish_allergenen;
DROP TABLE IF EXISTS dieten;
DROP TABLE IF EXISTS allergenen;

-- Maak de tabellen opnieuw aan
CREATE TABLE dieten (
    dieet_id INT AUTO_INCREMENT PRIMARY KEY,
    naam VARCHAR(100) NOT NULL,
    icon_class VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE allergenen (
    allergeen_id INT AUTO_INCREMENT PRIMARY KEY,
    naam VARCHAR(100) NOT NULL,
    icon_class VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE dish_dieten (
    dish_id INT,
    dieet_id INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (dish_id, dieet_id),
    FOREIGN KEY (dish_id) REFERENCES dishes(dish_id) ON DELETE CASCADE,
    FOREIGN KEY (dieet_id) REFERENCES dieten(dieet_id) ON DELETE CASCADE
);

CREATE TABLE dish_allergenen (
    dish_id INT,
    allergeen_id INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (dish_id, allergeen_id),
    FOREIGN KEY (dish_id) REFERENCES dishes(dish_id) ON DELETE CASCADE,
    FOREIGN KEY (allergeen_id) REFERENCES allergenen(allergeen_id) ON DELETE CASCADE
);

-- Voeg basis diëten weer toe
INSERT INTO dieten (naam, icon_class) VALUES
    ('Vegetarisch', '🥕'),
    ('Veganistisch', '🌱'),
    ('Glutenvrij', '🌾'),
    ('Lactosevrij', '🥛'),
    ('Halal', '🌙'),
    ('Kosher', '✡️'),
    ('Keto', '🥑'),
    ('Paleo', '🍖'),
    ('Low FODMAP', '🌿'),
    ('Diabetisch', '🍯'),
    ('Zoutarm', '🧂'),
    ('Eiwitrijk', '🥩'),
    ('Caloriearm', '⚖️'),
    ('Histaminearm', '🌿'),
    ('Fructosearm', '🍎'),
    ('Zonder toegevoegde suikers', '🚫');

-- Voeg basis allergenen weer toe
INSERT INTO allergenen (naam, icon_class) VALUES
    ('Gluten', '🌾'),
    ('Ei', '🥚'),
    ('Vis', '🐟'),
    ('Pinda', '🥜'),
    ('Noten', '🌰'),
    ('Soja', '🫘'),
    ('Melk', '🥛'),
    ('Schaaldieren', '🦐'),
    ('Weekdieren', '🦪'),
    ('Selderij', '🥬'),
    ('Mosterd', '🌭'),
    ('Sesamzaad', '✨'),
    ('Sulfiet', '🧂'),
    ('Lupine', '🌿');
