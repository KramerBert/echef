CREATE TABLE haccp_checklists (
    checklist_id INT PRIMARY KEY AUTO_INCREMENT,
    chef_id INT,
    naam VARCHAR(255),
    frequentie VARCHAR(50), -- dagelijks/wekelijks/maandelijks
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (chef_id) REFERENCES chefs(chef_id)
);

CREATE TABLE haccp_checkpunten (
    punt_id INT PRIMARY KEY AUTO_INCREMENT,
    checklist_id INT,
    omschrijving TEXT,
    grenswaarde VARCHAR(255),
    corrigerende_actie TEXT,
    FOREIGN KEY (checklist_id) REFERENCES haccp_checklists(checklist_id)
);

CREATE TABLE haccp_metingen (
    meting_id INT PRIMARY KEY AUTO_INCREMENT,
    punt_id INT,
    chef_id INT,
    waarde DECIMAL(5,2),
    opmerking TEXT,
    actie_ondernomen TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (punt_id) REFERENCES haccp_checkpunten(punt_id),
    FOREIGN KEY (chef_id) REFERENCES chefs(chef_id)
);
