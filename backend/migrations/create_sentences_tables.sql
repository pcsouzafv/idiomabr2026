-- Migration: Create sentences and related tables
-- Created: 2025-12-17
-- Description: Creates tables for sentence study system with AI teacher integration

-- Create sentences table
CREATE TABLE IF NOT EXISTS sentences (
    id SERIAL PRIMARY KEY,
    english TEXT NOT NULL,
    portuguese TEXT NOT NULL,
    level VARCHAR(10) DEFAULT 'A1',
    category VARCHAR(100),
    difficulty_score FLOAT DEFAULT 0.0,
    grammar_points TEXT,
    vocabulary_used TEXT,
    audio_url VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for sentences
CREATE INDEX IF NOT EXISTS ix_sentences_id ON sentences(id);
CREATE INDEX IF NOT EXISTS ix_sentences_english ON sentences USING gin(to_tsvector('english', english));
CREATE INDEX IF NOT EXISTS ix_sentences_level ON sentences(level);
CREATE INDEX IF NOT EXISTS ix_sentences_category ON sentences(category);

-- Create sentence_reviews table
CREATE TABLE IF NOT EXISTS sentence_reviews (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    sentence_id INTEGER NOT NULL REFERENCES sentences(id) ON DELETE CASCADE,
    difficulty VARCHAR(20) NOT NULL,
    direction VARCHAR(20) NOT NULL,
    reviewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for sentence_reviews
CREATE INDEX IF NOT EXISTS ix_sentence_reviews_id ON sentence_reviews(id);
CREATE INDEX IF NOT EXISTS ix_sentence_reviews_user_id ON sentence_reviews(user_id);
CREATE INDEX IF NOT EXISTS ix_sentence_reviews_sentence_id ON sentence_reviews(sentence_id);
CREATE INDEX IF NOT EXISTS ix_sentence_reviews_reviewed_at ON sentence_reviews(reviewed_at);

-- Create user_sentence_progress table
CREATE TABLE IF NOT EXISTS user_sentence_progress (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    sentence_id INTEGER NOT NULL REFERENCES sentences(id) ON DELETE CASCADE,
    easiness_factor FLOAT DEFAULT 2.5,
    interval INTEGER DEFAULT 0,
    repetitions INTEGER DEFAULT 0,
    last_reviewed TIMESTAMP,
    next_review TIMESTAMP,
    UNIQUE(user_id, sentence_id)
);

-- Create indexes for user_sentence_progress
CREATE INDEX IF NOT EXISTS ix_user_sentence_progress_id ON user_sentence_progress(id);
CREATE INDEX IF NOT EXISTS ix_user_sentence_progress_user_id ON user_sentence_progress(user_id);
CREATE INDEX IF NOT EXISTS ix_user_sentence_progress_sentence_id ON user_sentence_progress(sentence_id);
CREATE INDEX IF NOT EXISTS ix_user_sentence_progress_next_review ON user_sentence_progress(next_review);

-- Create ai_conversations table
CREATE TABLE IF NOT EXISTS ai_conversations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    sentence_id INTEGER REFERENCES sentences(id) ON DELETE SET NULL,
    user_message TEXT NOT NULL,
    ai_response TEXT NOT NULL,
    context TEXT,
    model_used VARCHAR(50),
    tokens_used INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for ai_conversations
CREATE INDEX IF NOT EXISTS ix_ai_conversations_id ON ai_conversations(id);
CREATE INDEX IF NOT EXISTS ix_ai_conversations_user_id ON ai_conversations(user_id);
CREATE INDEX IF NOT EXISTS ix_ai_conversations_created_at ON ai_conversations(created_at);

-- Add comments for documentation
COMMENT ON TABLE sentences IS 'Study sentences with translations and metadata';
COMMENT ON TABLE sentence_reviews IS 'History of sentence reviews by users';
COMMENT ON TABLE user_sentence_progress IS 'User progress on sentences using SM-2 spaced repetition algorithm';
COMMENT ON TABLE ai_conversations IS 'Conversations between users and AI teacher';

COMMENT ON COLUMN sentences.difficulty_score IS 'Difficulty score from 0.0 to 10.0';
COMMENT ON COLUMN sentences.grammar_points IS 'JSON array of grammar points covered';
COMMENT ON COLUMN sentences.vocabulary_used IS 'JSON array of key vocabulary words';
COMMENT ON COLUMN user_sentence_progress.easiness_factor IS 'SM-2 algorithm easiness factor (1.3 to 2.5)';
COMMENT ON COLUMN user_sentence_progress.interval IS 'Days until next review';
COMMENT ON COLUMN user_sentence_progress.repetitions IS 'Number of successful repetitions';
