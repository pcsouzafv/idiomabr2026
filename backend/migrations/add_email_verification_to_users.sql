-- Adds email verification timestamp to users table (safe to run multiple times)
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS email_verified_at TIMESTAMP;
