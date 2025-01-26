CREATE DATABASE IF NOT EXISTS echef;
USE echef;

CREATE TABLE gerechten (
    dish_id INT AUTO_INCREMENT PRIMARY KEY,
    naam VARCHAR(100) NOT NULL,
    beschrijving TEXT,
    categorie VARCHAR(50),
    bereidingswijze TEXT,
    verkoopprijs DECIMAL(10,2),
    chef_naam VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE ingredienten (
    ingredient_id INT AUTO_INCREMENT PRIMARY KEY,
    naam VARCHAR(100) NOT NULL,
    eenheid VARCHAR(20),
    prijs_per_eenheid DECIMAL(10,2),
    categorie VARCHAR(50)
);

CREATE TABLE gerecht_ingredient (
    gerecht_id INT,
    ingredient_id INT,
    hoeveelheid DECIMAL(10,3) NOT NULL,
    PRIMARY KEY (gerecht_id, ingredient_id),
    FOREIGN KEY (gerecht_id) REFERENCES gerechten(dish_id),
    FOREIGN KEY (ingredient_id) REFERENCES ingredienten(ingredient_id)
);
