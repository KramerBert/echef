-- First check if column exists
SET @dbname = DATABASE();
SET @tablename = "dishes";
SET @columnname = "totaal_ingredient_prijs";
SET @preparedStatement = (SELECT IF(
  (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE
      TABLE_SCHEMA = @dbname
      AND TABLE_NAME = @tablename
      AND COLUMN_NAME = @columnname
  ) > 0,
  "SELECT 1",
  CONCAT("ALTER TABLE ", @tablename, " ADD ", @columnname, " DECIMAL(10,2) DEFAULT 0.00")
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- Update existing dishes with calculated totals
UPDATE dishes d 
SET totaal_ingredient_prijs = (
    SELECT COALESCE(SUM(di.prijs_totaal), 0)
    FROM dish_ingredients di
    WHERE di.dish_id = d.dish_id
);
