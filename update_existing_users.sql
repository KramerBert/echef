
-- Add email_verified column to chefs table
ALTER TABLE chefs ADD COLUMN email_verified BOOLEAN DEFAULT FALSE;

-- Update bestaande gebruikers zodat ze geverifieerd zijn
UPDATE chefs SET email_verified = 1 WHERE email_verified IS NULL OR email_verified = 0;