ALTER TABLE users ADD COLUMN phone_number VARCHAR(32);
CREATE UNIQUE INDEX IF NOT EXISTS ix_users_phone_number ON users (phone_number);
