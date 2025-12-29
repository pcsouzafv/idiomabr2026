-- Migration: Create videos and video_progress tables
-- Created: 2025-12-17
-- Description: Creates tables for video learning system

-- Create enum types for videos
DO $$ BEGIN
    CREATE TYPE video_level AS ENUM ('A1', 'A2', 'B1', 'B2', 'C1', 'C2', 'ALL');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE video_category AS ENUM ('grammar', 'vocabulary', 'pronunciation', 'listening', 'conversation', 'tips', 'culture', 'other');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Create videos table
CREATE TABLE IF NOT EXISTS videos (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    youtube_id VARCHAR(50) NOT NULL UNIQUE,
    youtube_url VARCHAR(255) NOT NULL,
    thumbnail_url VARCHAR(500),
    level video_level DEFAULT 'A1',
    category video_category DEFAULT 'other',
    tags VARCHAR(500),
    duration INTEGER,
    views_count INTEGER DEFAULT 0,
    order_index INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    is_featured BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE,
    published_at TIMESTAMP WITH TIME ZONE
);

-- Create indexes for videos
CREATE INDEX IF NOT EXISTS ix_videos_id ON videos(id);
CREATE INDEX IF NOT EXISTS ix_videos_title ON videos(title);
CREATE INDEX IF NOT EXISTS ix_videos_youtube_id ON videos(youtube_id);
CREATE INDEX IF NOT EXISTS ix_videos_level ON videos(level);
CREATE INDEX IF NOT EXISTS ix_videos_category ON videos(category);
CREATE INDEX IF NOT EXISTS ix_videos_is_active ON videos(is_active);
CREATE INDEX IF NOT EXISTS ix_videos_is_featured ON videos(is_featured);

-- Create video_progress table
CREATE TABLE IF NOT EXISTS video_progress (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    video_id INTEGER NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    watched_duration INTEGER DEFAULT 0,
    is_completed BOOLEAN DEFAULT FALSE,
    completion_percentage INTEGER DEFAULT 0,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_watched_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(user_id, video_id)
);

-- Create indexes for video_progress
CREATE INDEX IF NOT EXISTS ix_video_progress_id ON video_progress(id);
CREATE INDEX IF NOT EXISTS ix_video_progress_user_id ON video_progress(user_id);
CREATE INDEX IF NOT EXISTS ix_video_progress_video_id ON video_progress(video_id);
CREATE INDEX IF NOT EXISTS ix_video_progress_is_completed ON video_progress(is_completed);

-- Add comments for documentation
COMMENT ON TABLE videos IS 'YouTube videos for English learning';
COMMENT ON TABLE video_progress IS 'User progress tracking for videos';

COMMENT ON COLUMN videos.youtube_id IS 'Unique YouTube video ID';
COMMENT ON COLUMN videos.duration IS 'Video duration in seconds';
COMMENT ON COLUMN videos.views_count IS 'Internal view counter';
COMMENT ON COLUMN videos.order_index IS 'Display order (lower = first)';

COMMENT ON COLUMN video_progress.watched_duration IS 'Time watched in seconds';
COMMENT ON COLUMN video_progress.completion_percentage IS 'Percentage watched (0-100)';
