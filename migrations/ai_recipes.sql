-- AI gerelateerde kolommen toevoegen aan dishes tabel
ALTER TABLE dishes 
ADD COLUMN is_ai_generated BOOLEAN DEFAULT FALSE,
ADD COLUMN original_prompt TEXT,
ADD COLUMN generation_date DATETIME,
ADD COLUMN ai_model VARCHAR(50),
ADD COLUMN prompt_tokens INT,
ADD COLUMN completion_tokens INT,
ADD COLUMN total_cost DECIMAL(10,4) DEFAULT 0.00;

-- Index toevoegen voor sneller zoeken van AI recepten
CREATE INDEX idx_ai_generated ON dishes(is_ai_generated);

SOURCE /c:/echef/migrations/ai_recipes.sql