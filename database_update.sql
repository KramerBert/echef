-- Add email_verified column to chefs table
ALTER TABLE chefs ADD COLUMN email_verified BOOLEAN DEFAULT FALSE;
