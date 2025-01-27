-- MySQL dump 10.13  Distrib 9.1.0, for Win64 (x86_64)
--
-- Host: localhost    Database: echef
-- ------------------------------------------------------
-- Server version	9.1.0
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `allergenen`
--

DROP TABLE IF EXISTS `allergenen`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `allergenen` (
  `allergeen_id` int NOT NULL AUTO_INCREMENT,
  `naam` varchar(50) NOT NULL,
  `icon_class` varchar(50) NOT NULL,
  `beschrijving` text,
  PRIMARY KEY (`allergeen_id`)
) ENGINE=InnoDB AUTO_INCREMENT=15 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `allergenen`
--

/*!40000 ALTER TABLE `allergenen` DISABLE KEYS */;
INSERT INTO `allergenen` VALUES (1,'Gluten','fa-wheat-awn','Bevat gluten'),(2,'Schaaldieren','fa-shrimp','Bevat schaaldieren'),(3,'Eieren','fa-egg','Bevat eieren'),(4,'Vis','fa-fish','Bevat vis'),(5,'Pinda','fa-peanut','Bevat pinda\'s'),(6,'Soja','fa-seedling','Bevat soja'),(7,'Melk','fa-milk','Bevat melk/lactose'),(8,'Noten','fa-acorn','Bevat noten'),(9,'Selderij','fa-leaf','Bevat selderij'),(10,'Mosterd','fa-jar','Bevat mosterd'),(11,'Sesam','fa-seed','Bevat sesam'),(12,'Sulfiet','fa-wine-bottle','Bevat sulfieten'),(13,'Lupine','fa-flower','Bevat lupine'),(14,'Weekdieren','fa-shell','Bevat weekdieren');
/*!40000 ALTER TABLE `allergenen` ENABLE KEYS */;

--
-- Table structure for table `chefs`
--

DROP TABLE IF EXISTS `chefs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `chefs` (
  `chef_id` int NOT NULL AUTO_INCREMENT,
  `naam` varchar(100) NOT NULL,
  `email` varchar(100) NOT NULL,
  `wachtwoord` varchar(255) NOT NULL,
  PRIMARY KEY (`chef_id`),
  UNIQUE KEY `email` (`email`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `chefs`
--

/*!40000 ALTER TABLE `chefs` DISABLE KEYS */;
INSERT INTO `chefs` VALUES (1,'Bert','bert@bert.nl','scrypt:32768:8:1$1StTrqODGsFKPE34$3333747c003c15ec16ced5cb50f1adfdb29b4eb4d5bf844514429631031de89c7f058cac4ce14a735bcb0de911bfc53fc0ee6614d1e3b60b82499f3d220649d6');
/*!40000 ALTER TABLE `chefs` ENABLE KEYS */;

--
-- Table structure for table `dieten`
--

DROP TABLE IF EXISTS `dieten`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dieten` (
  `dieet_id` int NOT NULL AUTO_INCREMENT,
  `naam` varchar(50) NOT NULL,
  `icon_class` varchar(50) NOT NULL,
  `beschrijving` text,
  PRIMARY KEY (`dieet_id`)
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dieten`
--

/*!40000 ALTER TABLE `dieten` DISABLE KEYS */;
INSERT INTO `dieten` VALUES (1,'Vegetarisch','VG','Geen vlees of vis'),(2,'Veganistisch','VN','Geen dierlijke producten'),(3,'Halal','HL','Volgens islamitische voedselregels'),(4,'Koosjer','KS','Volgens joodse voedselregels'),(5,'Glutenvrij','GV','Zonder gluten'),(6,'Lactosevrij','LV','Zonder melkproducten'),(7,'Keto','KT','Zeer koolhydraatarm'),(8,'Paleo','PL','Oervoeding zonder bewerkte producten');
/*!40000 ALTER TABLE `dieten` ENABLE KEYS */;

--
-- Table structure for table `dish_allergenen`
--

DROP TABLE IF EXISTS `dish_allergenen`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dish_allergenen` (
  `dish_id` int NOT NULL,
  `allergeen_id` int NOT NULL,
  PRIMARY KEY (`dish_id`,`allergeen_id`),
  KEY `allergeen_id` (`allergeen_id`),
  CONSTRAINT `dish_allergenen_ibfk_1` FOREIGN KEY (`dish_id`) REFERENCES `dishes` (`dish_id`) ON DELETE CASCADE,
  CONSTRAINT `dish_allergenen_ibfk_2` FOREIGN KEY (`allergeen_id`) REFERENCES `allergenen` (`allergeen_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dish_allergenen`
--

/*!40000 ALTER TABLE `dish_allergenen` DISABLE KEYS */;
INSERT INTO `dish_allergenen` VALUES (14,1),(14,2),(14,3),(14,4),(14,8),(14,9),(14,10),(14,11),(14,12),(14,14);
/*!40000 ALTER TABLE `dish_allergenen` ENABLE KEYS */;

--
-- Table structure for table `dish_dieten`
--

DROP TABLE IF EXISTS `dish_dieten`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dish_dieten` (
  `dish_id` int NOT NULL,
  `dieet_id` int NOT NULL,
  PRIMARY KEY (`dish_id`,`dieet_id`),
  KEY `dieet_id` (`dieet_id`),
  CONSTRAINT `dish_dieten_ibfk_1` FOREIGN KEY (`dish_id`) REFERENCES `dishes` (`dish_id`) ON DELETE CASCADE,
  CONSTRAINT `dish_dieten_ibfk_2` FOREIGN KEY (`dieet_id`) REFERENCES `dieten` (`dieet_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dish_dieten`
--

/*!40000 ALTER TABLE `dish_dieten` DISABLE KEYS */;
INSERT INTO `dish_dieten` VALUES (14,3),(14,8);
/*!40000 ALTER TABLE `dish_dieten` ENABLE KEYS */;

--
-- Table structure for table `dish_ingredients`
--

DROP TABLE IF EXISTS `dish_ingredients`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dish_ingredients` (
  `dish_ingredient_id` int NOT NULL AUTO_INCREMENT,
  `dish_id` int NOT NULL,
  `ingredient_id` int NOT NULL,
  `hoeveelheid` decimal(10,2) NOT NULL,
  `prijs_totaal` decimal(10,2) NOT NULL,
  PRIMARY KEY (`dish_ingredient_id`),
  KEY `dish_id` (`dish_id`),
  KEY `ingredient_id` (`ingredient_id`),
  CONSTRAINT `dish_ingredients_ibfk_1` FOREIGN KEY (`dish_id`) REFERENCES `dishes` (`dish_id`) ON DELETE CASCADE,
  CONSTRAINT `dish_ingredients_ibfk_2` FOREIGN KEY (`ingredient_id`) REFERENCES `ingredients` (`ingredient_id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=51 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dish_ingredients`
--

/*!40000 ALTER TABLE `dish_ingredients` DISABLE KEYS */;
INSERT INTO `dish_ingredients` VALUES (8,4,4,0.10,4.00),(9,7,2,0.05,0.83),(10,7,1,0.10,4.00),(11,5,4,0.25,9.99),(12,6,9,0.05,0.60),(13,8,76,0.05,0.51),(15,8,58,0.05,0.54),(16,8,72,0.05,0.55),(17,8,55,0.05,0.54),(18,8,55,0.05,0.54),(19,8,57,0.10,1.08),(20,10,78,0.20,2.02),(21,4,48,0.10,0.01),(22,4,14,1.00,3.00),(23,10,37,1.00,0.10),(24,12,80,0.30,7.50),(25,12,82,0.05,0.37),(26,12,83,0.05,0.40),(27,12,81,10.00,40.00),(28,13,84,0.01,0.46),(29,13,87,0.20,0.24),(30,13,85,0.16,0.34),(31,13,86,1.00,4.00),(38,14,18,0.23,2.30),(46,14,84,0.25,11.58),(47,14,90,1.00,1.00),(48,14,5,3.00,25.50),(49,13,16,1.00,0.04),(50,13,20,1.00,0.10);
/*!40000 ALTER TABLE `dish_ingredients` ENABLE KEYS */;

--
-- Table structure for table `dishes`
--

DROP TABLE IF EXISTS `dishes`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dishes` (
  `dish_id` int NOT NULL AUTO_INCREMENT,
  `chef_id` int NOT NULL,
  `naam` varchar(100) NOT NULL,
  `beschrijving` text,
  `verkoopprijs` decimal(10,2) DEFAULT NULL,
  `categorie` varchar(50) DEFAULT NULL,
  `bereidingswijze` text,
  PRIMARY KEY (`dish_id`),
  KEY `chef_id` (`chef_id`),
  CONSTRAINT `dishes_ibfk_1` FOREIGN KEY (`chef_id`) REFERENCES `chefs` (`chef_id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=16 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dishes`
--

/*!40000 ALTER TABLE `dishes` DISABLE KEYS */;
INSERT INTO `dishes` VALUES (4,1,'Carpaccio','bla | bla | bla',11.55,'Hors-d\'┼ôuvre','geen bereidingswijze'),(5,1,'Ossenhaas','Gebakken ossenhaas | Champignons',20.00,'Relev├® of R├┤ti',''),(6,1,'Grand Dessert','Proeverij van desserts',19.00,'Entremets',NULL),(7,1,'Gebakken Zeebaars','Zeebaars | Witte wijnsaus | Dille',9.00,'Poisson',NULL),(8,1,'Kaasplankje','Diverse soorten kaasjes',9.95,'Basisgerecht','Kaasplankje met druiven en jam'),(9,1,'Basisgerecht Jus de Veau','Kalfsjus',11.95,'Basisgerecht','Voorverwarmen & roosteren\r\n\r\nVerwarm de oven voor op 220ÔÇô230 ┬░C.\r\nLeg de kalfsbotten in een braadslede en rooster ze 30ÔÇô45 minuten, tot ze mooi bruin kleuren. Dit zorgt voor een diepe smaak en kleur in de jus.\r\nGroenten toevoegen\r\n\r\nNa de eerste 15ÔÇô20 minuten kun je de grove stukken wortel, ui en bleekselderij bij de botten in de oven leggen om ook die te laten roosteren. Let erop dat de groenten niet verbranden; roosteren is ok├®, maar zwarte randjes geven een bittere smaak.\r\nTomatenpuree meeroosteren\r\n\r\nRoer de tomatenpuree kort door de botten en de groenten en laat deze nog een paar minuten meeroosteren. Hierdoor karamelliseert de puree en krijg je een mooiere kleur en vollere smaak.\r\nAfblussen in de pan\r\nHaal de braadslede uit de oven en doe de geroosterde botten en groenten over in een grote (soep)pan. Blus de braadslede indien nodig met een scheutje van de rode wijn of wat water en schraap de aanbaksels los. Giet dit bij de pan voor extra smaak.\r\nWijn en bouquet garni toevoegen\r\n\r\nVoeg de rest van de rode wijn (als je die gebruikt) toe in de pan en laat deze kort inkoken om de alcohol te laten verdampen.\r\nDoe het bouquet garni erbij.\r\nWater toevoegen & sudderen\r\n\r\nGiet voldoende water in de pan totdat de botten ruim onder staan (2ÔÇô3 liter).\r\nBreng aan de kook en zet daarna het vuur laag zodat de jus heel zachtjes kan trekken.\r\nLaat dit minimaal 4ÔÇô6 uur sudderen (hoe langer, hoe krachtiger de jus). Je kunt zelfs tot 8 uur doorgaan voor een zeer geconcentreerde smaak.\r\nAf en toe afschuimen\r\n\r\nTijdens het trekken ontstaat er een laagje schuim en vet bovenop. Schep dit met een lepel of schuimspaan voorzichtig eraf. Zo houd je de jus helder en voorkom je bittere smaken.\r\nPasseer & reduceer\r\n\r\nHaal de botten en groenten uit de pan (of giet alles door een fijne zeef of passeerdoek in een andere pan).\r\nGooi de vaste onderdelen weg; hier is alle smaak al uit getrokken.\r\nBreng het gezeefde vocht opnieuw aan de kook en laat inkoken (reduceren) tot de gewenste dikte en smaak. Hoe langer je reduceert, hoe geconcentreerder en dikker de jus wordt.\r\nOp smaak brengen\r\n\r\nProef je jus de veau en voeg eventueel zout en peper toe. Vaak is het verstandig om pas aan het eind te zouten, omdat de smaak (en zoutconcentratie) verandert door het inkoken.\r\nServeren & bewaren\r\n\r\nDe jus is nu klaar om direct te gebruiken als basissaus of om verder op smaak te brengen (bijvoorbeeld met kruiden, een scheutje room, een klontje boter of een drupje cognac).\r\nWil je de jus bewaren, laat hem dan snel afkoelen en bewaar hem afgesloten in de koelkast (een paar dagen houdbaar) of in de vriezer (meerdere maanden houdbaar).'),(10,1,'Lasagna','Lasagna Bolognese | Spinazie | Bechamel | Mozzarella',19.98,'Fromage','laagje voor laagje'),(11,1,'Tuiles','Onderdeel voor bijvoorbeeld een Grand Dessert',0.10,'Basisgerecht','Klop het ei, vanille-extract, zout en poedersuiker samen tot een glad mengsel.\r\nVoeg de gesmolten boter toe en meng goed.\r\nVoeg het amandelmeel en de bloem toe en meng tot een glad beslag.\r\nDek het beslag af en laat het minstens een uur in de koelkast rusten om het steviger te maken.\r\nBakken:\r\n\r\nVerwarm de oven voor op 165┬░C.\r\nLeg een vel bakpapier op een bakplaat.\r\nSchep een kleine hoeveelheid van het gekoelde beslag op het bakpapier en spreid het zeer dun uit met een kleine spatel tot de gewenste vorm (bijvoorbeeld een cirkel van ongeveer 7,5 cm in diameter).\r\nBak de tuiles 4 tot 7 minuten, of tot de randen licht goudbruin zijn.\r\n\r\nVormen:\r\nHaal de tuiles direct uit de oven en vorm ze snel terwijl ze nog warm zijn.\r\nVoor de traditionele gebogen vorm kunt u de warme tuiles over een deegroller of een fles leggen en laten afkoelen.\r\nVoor sigaarvormige tuiles rolt u ze voorzichtig rond het handvat van een houten lepel.\r\nTips:\r\n\r\nWerk in kleine batches, omdat de tuiles snel uitharden en moeilijk te vormen zijn zodra ze afgekoeld zijn.\r\nAls een tuile te hard is geworden om te vormen, kunt u deze kort terug in de oven plaatsen om weer zacht te worden.\r\nBewaar de afgekoelde tuiles in een luchtdichte container met een zakje silicagel om ze knapperig te houden.'),(12,1,'Vitello Tonato','Dungesneden kalfsvlees | Tonijnmayonaise | Kappertjes | Zongedroogde tomaatjes',15.00,'Hors-d\'┼ôuvre','Blablalblbalblablaablbl'),(13,1,'Caprese','Tomaat met buffelmozzerella, basilicum en aceto balsamico',11.51,'Hors-d\'┼ôuvre','1. Snijdt de tomaat en buffel mozzerella in dunne plakken\r\n2. Leg deze om en om neer op een bord\r\n3. Bestrooi met zout en peper\r\n4. voeg de geplukte basilicum toe'),(14,1,'Testgerecht','testbeschrijving',24.95,'Salade','heel heet maken, nog heter maken'),(15,1,'Testgerecht4','lkandsf;lknaldsknf',NULL,'Relev├® of R├┤ti','koken');
/*!40000 ALTER TABLE `dishes` ENABLE KEYS */;

--
-- Table structure for table `haccp_checklists`
--

DROP TABLE IF EXISTS `haccp_checklists`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `haccp_checklists` (
  `checklist_id` int NOT NULL AUTO_INCREMENT,
  `chef_id` int DEFAULT NULL,
  `naam` varchar(255) DEFAULT NULL,
  `frequentie` varchar(50) DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`checklist_id`),
  KEY `chef_id` (`chef_id`),
  CONSTRAINT `haccp_checklists_ibfk_1` FOREIGN KEY (`chef_id`) REFERENCES `chefs` (`chef_id`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `haccp_checklists`
--

/*!40000 ALTER TABLE `haccp_checklists` DISABLE KEYS */;
INSERT INTO `haccp_checklists` VALUES (4,1,'Koeling','dagelijks','2025-01-26 21:06:01');
/*!40000 ALTER TABLE `haccp_checklists` ENABLE KEYS */;

--
-- Table structure for table `haccp_checkpunten`
--

DROP TABLE IF EXISTS `haccp_checkpunten`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `haccp_checkpunten` (
  `punt_id` int NOT NULL AUTO_INCREMENT,
  `checklist_id` int DEFAULT NULL,
  `omschrijving` text,
  `grenswaarde` varchar(255) DEFAULT NULL,
  `corrigerende_actie` text,
  PRIMARY KEY (`punt_id`),
  KEY `checklist_id` (`checklist_id`),
  CONSTRAINT `haccp_checkpunten_ibfk_1` FOREIGN KEY (`checklist_id`) REFERENCES `haccp_checklists` (`checklist_id`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `haccp_checkpunten`
--

/*!40000 ALTER TABLE `haccp_checkpunten` DISABLE KEYS */;
INSERT INTO `haccp_checkpunten` VALUES (5,4,'Temparatuur','6','Schoonmaak');
/*!40000 ALTER TABLE `haccp_checkpunten` ENABLE KEYS */;

--
-- Table structure for table `haccp_metingen`
--

DROP TABLE IF EXISTS `haccp_metingen`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `haccp_metingen` (
  `meting_id` int NOT NULL AUTO_INCREMENT,
  `punt_id` int DEFAULT NULL,
  `chef_id` int DEFAULT NULL,
  `waarde` decimal(5,2) DEFAULT NULL,
  `opmerking` text,
  `actie_ondernomen` text,
  `timestamp` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`meting_id`),
  KEY `punt_id` (`punt_id`),
  KEY `chef_id` (`chef_id`),
  CONSTRAINT `haccp_metingen_ibfk_1` FOREIGN KEY (`punt_id`) REFERENCES `haccp_checkpunten` (`punt_id`),
  CONSTRAINT `haccp_metingen_ibfk_2` FOREIGN KEY (`chef_id`) REFERENCES `chefs` (`chef_id`)
) ENGINE=InnoDB AUTO_INCREMENT=12 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `haccp_metingen`
--

/*!40000 ALTER TABLE `haccp_metingen` DISABLE KEYS */;
INSERT INTO `haccp_metingen` VALUES (8,5,1,6.00,'','','2025-01-26 21:06:17'),(9,5,1,1.00,'','','2025-01-26 21:06:27'),(10,5,1,6.00,'','Geen actie geregistreerd','2025-01-26 21:06:35'),(11,5,1,6.00,'','','2025-01-26 21:09:31');
/*!40000 ALTER TABLE `haccp_metingen` ENABLE KEYS */;

--
-- Table structure for table `ingredients`
--

DROP TABLE IF EXISTS `ingredients`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `ingredients` (
  `ingredient_id` int NOT NULL AUTO_INCREMENT,
  `chef_id` int NOT NULL,
  `naam` varchar(100) NOT NULL,
  `categorie` varchar(100) NOT NULL,
  `eenheid` varchar(50) NOT NULL,
  `prijs_per_eenheid` decimal(10,2) NOT NULL,
  `bevat_allergenen` json DEFAULT NULL,
  `past_in_dieet` json DEFAULT NULL,
  PRIMARY KEY (`ingredient_id`),
  KEY `chef_id` (`chef_id`),
  CONSTRAINT `ingredients_ibfk_1` FOREIGN KEY (`chef_id`) REFERENCES `chefs` (`chef_id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=98 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `ingredients`
--

/*!40000 ALTER TABLE `ingredients` DISABLE KEYS */;
INSERT INTO `ingredients` VALUES (1,1,'Zeebaars','vis','kilogram (kg)',40.00,NULL,NULL),(2,1,'Boter','Zuivel','kilogram (kg)',16.50,NULL,NULL),(3,1,'Witte Wijn','Dranken','Liter',8.00,NULL,NULL),(4,1,'Kogelbiefstuk','Vlees','kilogram (kg)',39.95,NULL,NULL),(5,1,'Champignons','Groenten','kilogram (kg)',8.50,NULL,NULL),(7,1,'Koksroom','Zuivel','liter (l)',9.00,NULL,NULL),(9,1,'Slagroom','Zuivel','liter (l)',12.00,NULL,NULL),(11,1,'Water','Dranken','liter (l)',0.01,NULL,NULL),(12,1,'Taugeh','Groenten','kilogram (kg)',19.00,NULL,NULL),(13,1,'Prei','Groenten','kilogram (kg)',4.00,NULL,NULL),(14,1,'Ui','Groenten','kilogram (kg)',3.00,NULL,NULL),(15,1,'Gemalen Witte Peper','Kruiden','gram (g)',0.05,NULL,NULL),(16,1,'Zout','Kruiden','gram (g)',0.04,NULL,NULL),(17,1,'Kalfsbotten','Vlees','kilogram (kg)',5.75,NULL,NULL),(18,1,'Rode wijn','Dranken','liter (l)',10.00,NULL,NULL),(19,1,'Tomantenpuree','Conserven','liter (l)',8.65,NULL,NULL),(20,1,'Zwarte peper (gemalen)','Kruiden','gram (g)',0.10,NULL,NULL),(21,1,'Witte peper (gemalen)','Kruiden','gram (g)',0.10,NULL,NULL),(22,1,'Chili (gemalen)','Kruiden','gram (g)',0.10,NULL,NULL),(23,1,'Paprika (gemalen)','Kruiden','gram (g)',0.10,NULL,NULL),(24,1,'Cayennepeper (gemalen)','Kruiden','gram (g)',0.10,NULL,NULL),(25,1,'Komijn (gemalen)','Kruiden','gram (g)',0.10,NULL,NULL),(26,1,'Koriander (gemalen)','Kruiden','gram (g)',0.10,NULL,NULL),(27,1,'Gember (gemalen)','Kruiden','gram (g)',0.10,NULL,NULL),(28,1,'Kurkuma (gemalen)','Kruiden','gram (g)',0.10,NULL,NULL),(29,1,'Kaneel (gemalen)','Kruiden','gram (g)',0.10,NULL,NULL),(30,1,'Nootmuskaat (gemalen)','Kruiden','gram (g)',0.10,NULL,NULL),(31,1,'Kruidnagel (gemalen)','Kruiden','gram (g)',0.50,NULL,NULL),(32,1,'Kardemom (gemalen)','Kruiden','gram (g)',0.10,NULL,NULL),(33,1,'Piment (allspice) (gemalen)','Kruiden','gram (g)',0.10,NULL,NULL),(34,1,'Karwijzaad (gemalen)','Kruiden','gram (g)',0.10,NULL,NULL),(35,1,'Laurier (gemalen)','Kruiden','gram (g)',0.10,NULL,NULL),(36,1,'Venkelzaad (gemalen)','Kruiden','gram (g)',0.10,NULL,NULL),(37,1,'Anijszaad (gemalen)','Kruiden','gram (g)',0.10,NULL,NULL),(38,1,'Mosterdzaad (gemalen)','Kruiden','gram (g)',0.10,NULL,NULL),(39,1,'Lavas (gemalen)','Kruiden','gram (g)',0.10,NULL,NULL),(40,1,'Oregano (gemalen)','Kruiden','gram (g)',0.10,NULL,NULL),(41,1,'Tijm (gemalen)','Kruiden','gram (g)',0.10,NULL,NULL),(42,1,'Rozemarijn (gemalen)','Kruiden','gram (g)',0.10,NULL,NULL),(43,1,'Basilicum (gemalen)','Kruiden','gram (g)',0.10,NULL,NULL),(44,1,'Bonenkruid (gemalen)','Kruiden','gram (g)',0.10,NULL,NULL),(45,1,'Dille (gemalen)','Kruiden','gram (g)',0.10,NULL,NULL),(46,1,'Sumak (gemalen)','Kruiden','gram (g)',0.10,NULL,NULL),(47,1,'Ras el hanout (gemalen)','Kruiden','gram (g)',0.10,NULL,NULL),(48,1,'Baharat (gemalen)','Kruiden','gram (g)',0.10,NULL,NULL),(49,1,'Five spice (gemalen)','Kruiden','gram (g)',0.10,NULL,NULL),(50,1,'Gouda','Zuivel','kilogram (kg)',10.75,NULL,NULL),(51,1,'Edam','Zuivel','kilogram (kg)',10.76,NULL,NULL),(52,1,'Leerdammer','Zuivel','kilogram (kg)',10.77,NULL,NULL),(53,1,'Maasdammer','Zuivel','kilogram (kg)',10.78,NULL,NULL),(54,1,'Boerenkaas','Zuivel','kilogram (kg)',10.79,NULL,NULL),(55,1,'Geitenkaas','Zuivel','kilogram (kg)',10.80,NULL,NULL),(56,1,'Komijnekaas','Zuivel','kilogram (kg)',10.81,NULL,NULL),(57,1,'Cheddar','Zuivel','kilogram (kg)',10.82,NULL,NULL),(58,1,'Brie','Zuivel','kilogram (kg)',10.83,NULL,NULL),(59,1,'Camembert','Zuivel','kilogram (kg)',10.84,NULL,NULL),(60,1,'Roquefort','Zuivel','kilogram (kg)',10.85,NULL,NULL),(61,1,'Gorgonzola','Zuivel','kilogram (kg)',10.86,NULL,NULL),(62,1,'Stilton','Zuivel','kilogram (kg)',10.87,NULL,NULL),(63,1,'Manchego','Zuivel','kilogram (kg)',10.88,NULL,NULL),(64,1,'Pecorino','Zuivel','kilogram (kg)',10.89,NULL,NULL),(65,1,'Parmigiano Reggiano','Zuivel','kilogram (kg)',10.90,NULL,NULL),(66,1,'Grana Padano','Zuivel','kilogram (kg)',10.91,NULL,NULL),(67,1,'Emmentaler','Zuivel','kilogram (kg)',10.92,NULL,NULL),(68,1,'Gruyere','Zuivel','kilogram (kg)',10.93,NULL,NULL),(69,1,'Tilsiter','Zuivel','kilogram (kg)',10.94,NULL,NULL),(70,1,'Mozzarella','Zuivel','kilogram (kg)',11.03,NULL,NULL),(71,1,'Feta','Zuivel','kilogram (kg)',10.96,NULL,NULL),(72,1,'Halloumi','Zuivel','kilogram (kg)',10.97,NULL,NULL),(73,1,'Taleggio','Zuivel','kilogram (kg)',10.98,NULL,NULL),(74,1,'Reblochon','Zuivel','kilogram (kg)',10.99,NULL,NULL),(75,1,'Munster','Zuivel','kilogram (kg)',10.10,NULL,NULL),(76,1,'Port Salut','Zuivel','kilogram (kg)',10.10,NULL,NULL),(77,1,'Cabrales','Zuivel','kilogram (kg)',10.10,NULL,NULL),(78,1,'Fontina','Zuivel','kilogram (kg)',10.10,NULL,NULL),(79,1,'Raclette','Zuivel','kilogram (kg)',10.10,NULL,NULL),(80,1,'Tonijn','vis','kilogram (kg)',25.00,NULL,NULL),(81,1,'Kappertjes','Conserven','gram (g)',4.00,NULL,NULL),(82,1,'Zongedroogde Tomaten','Conserven','kilogram (kg)',7.44,NULL,NULL),(83,1,'Mayonaise','Conserven','liter (l)',8.00,NULL,NULL),(84,1,'Aceto balsamcio','Azijn','stuk/stuks',46.30,NULL,NULL),(85,1,'Tomaat','Groente','kilogram (kg)',2.11,NULL,NULL),(86,1,'buffelmozzerella','zuivel','stuk/stuks',4.00,NULL,NULL),(87,1,'basilicum','kruiden','stuk/stuks',1.20,NULL,NULL),(88,1,'Voorbeeld Naam','Voorbeeld Categorie','gram (g)',0.00,NULL,NULL),(89,1,'BONOMI AMARETTI','KOEK & BANKET GROOTVERBRUIK','ST',500.00,NULL,NULL),(90,1,'BLUE BAND CULINAIR','ROOMPRODUCTEN','PK',1.00,NULL,NULL),(91,1,'ZALMFILET NOORS MET VEL 4-5 GGN','VIS VERS','KG',1.00,NULL,NULL),(92,1,'RUNDER RIB EYE AAN HET STUK DV','VLEES DIEPVRIES SLAGERIJ CONC','gram (g)',40.00,NULL,NULL),(93,1,'MEYERIJ SLAGROOM MET SUIKER 35% 1L','ROOMPRODUCTEN','PK',1.00,NULL,NULL),(94,1,'FUMAGALLI GUANCIALE STAGIO 1/2','VLEESWAREN BULK','KG',1.00,NULL,NULL),(96,1,'CORTE BUONA PROSCUTTO TIPICO BLOK 1/2','VLEESWAREN BULK','KG',1.00,NULL,NULL),(97,1,'WEERRIBBEN BIO  VOLLE MELK 1LT','MELKPRODUKTEN DAGVERS  ','PK',1.00,NULL,NULL);
/*!40000 ALTER TABLE `ingredients` ENABLE KEYS */;

--
-- Table structure for table `login_attempts`
--

DROP TABLE IF EXISTS `login_attempts`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `login_attempts` (
  `attempt_id` int NOT NULL AUTO_INCREMENT,
  `chef_id` int DEFAULT NULL,
  `timestamp` datetime DEFAULT CURRENT_TIMESTAMP,
  `success` tinyint(1) DEFAULT NULL,
  `ip_address` varchar(45) DEFAULT NULL,
  PRIMARY KEY (`attempt_id`),
  KEY `chef_id` (`chef_id`),
  CONSTRAINT `login_attempts_ibfk_1` FOREIGN KEY (`chef_id`) REFERENCES `chefs` (`chef_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `login_attempts`
--

/*!40000 ALTER TABLE `login_attempts` DISABLE KEYS */;
/*!40000 ALTER TABLE `login_attempts` ENABLE KEYS */;

--
-- Table structure for table `password_resets`
--

DROP TABLE IF EXISTS `password_resets`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `password_resets` (
  `reset_id` int NOT NULL AUTO_INCREMENT,
  `chef_id` int DEFAULT NULL,
  `token` varchar(255) NOT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `expires_at` datetime DEFAULT NULL,
  `used` tinyint(1) DEFAULT '0',
  PRIMARY KEY (`reset_id`),
  KEY `chef_id` (`chef_id`),
  CONSTRAINT `password_resets_ibfk_1` FOREIGN KEY (`chef_id`) REFERENCES `chefs` (`chef_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `password_resets`
--

/*!40000 ALTER TABLE `password_resets` DISABLE KEYS */;
/*!40000 ALTER TABLE `password_resets` ENABLE KEYS */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-01-27 16:07:16
