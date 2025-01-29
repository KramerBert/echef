-- Controleer of de tabel bestaat en maak deze aan indien nodig
CREATE TABLE IF NOT EXISTS password_resets (
    reset_id INT AUTO_INCREMENT PRIMARY KEY,
    chef_id INT NOT NULL,
    token VARCHAR(255) NOT NULL,
    expires_at DATETIME NOT NULL,
    used BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (chef_id) REFERENCES chefs(chef_id) ON DELETE CASCADE
);

-- Voeg indexes toe voor betere performance
CREATE INDEX idx_token ON password_resets(token);
CREATE INDEX idx_expires ON password_resets(expires_at);
