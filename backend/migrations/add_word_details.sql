-- Migration: Add detailed information fields to words table
-- Created: 2025-12-15

-- Add new columns for grammatical and semantic information
ALTER TABLE words ADD COLUMN IF NOT EXISTS word_type VARCHAR(50);
ALTER TABLE words ADD COLUMN IF NOT EXISTS definition_en TEXT;
ALTER TABLE words ADD COLUMN IF NOT EXISTS definition_pt TEXT;
ALTER TABLE words ADD COLUMN IF NOT EXISTS synonyms TEXT;
ALTER TABLE words ADD COLUMN IF NOT EXISTS antonyms TEXT;

-- Add new columns for examples and usage
ALTER TABLE words ADD COLUMN IF NOT EXISTS example_en TEXT;
ALTER TABLE words ADD COLUMN IF NOT EXISTS example_pt TEXT;
ALTER TABLE words ADD COLUMN IF NOT EXISTS example_sentences TEXT;
ALTER TABLE words ADD COLUMN IF NOT EXISTS usage_notes TEXT;
ALTER TABLE words ADD COLUMN IF NOT EXISTS collocations TEXT;

-- Add new columns for categorization/media
ALTER TABLE words ADD COLUMN IF NOT EXISTS tags VARCHAR(500);
ALTER TABLE words ADD COLUMN IF NOT EXISTS audio_url VARCHAR(500);

-- Add comments for documentation
COMMENT ON COLUMN words.word_type IS 'Grammatical type: noun, verb, adjective, adverb, etc';
COMMENT ON COLUMN words.definition_en IS 'English definition of the word';
COMMENT ON COLUMN words.definition_pt IS 'Portuguese definition of the word';
COMMENT ON COLUMN words.synonyms IS 'Comma-separated list of synonyms';
COMMENT ON COLUMN words.antonyms IS 'Comma-separated list of antonyms';
COMMENT ON COLUMN words.example_en IS 'Example sentence in English';
COMMENT ON COLUMN words.example_pt IS 'Example sentence in Portuguese';
COMMENT ON COLUMN words.example_sentences IS 'JSON array of example sentences with translations';
COMMENT ON COLUMN words.usage_notes IS 'Usage tips, context, and nuances';
COMMENT ON COLUMN words.collocations IS 'JSON array of common word collocations';
COMMENT ON COLUMN words.tags IS 'Comma-separated list of tags';
COMMENT ON COLUMN words.audio_url IS 'Audio URL for pronunciation';
