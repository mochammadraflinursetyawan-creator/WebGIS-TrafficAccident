-- =====================================================================
-- DATABASE SCHEMA: REAL-TIME ACCIDENT MAPPING WEBGIS
-- Database: PostgreSQL + PostGIS (EPSG:4326)
-- =====================================================================

-- 1. Enable PostGIS Extension
CREATE EXTENSION IF NOT EXISTS postgis;

-- 2. Enumerated Types (Optional, can also be handled as VARCHAR with CHECK constraints)
DO $$ BEGIN
    CREATE TYPE user_role AS ENUM ('user', 'moderator', 'admin');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE accident_status AS ENUM (
        'DETECTED', 
        'REPORTED', 
        'UNDER REVIEW', 
        'VERIFIED', 
        'REJECTED', 
        'DUPLICATE', 
        'RESOLVED'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- 3. Users Table
CREATE TABLE IF NOT EXISTS users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    role VARCHAR(20) DEFAULT 'user' CHECK (role IN ('user', 'moderator', 'admin')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. Sources Table (Audit trail for raw social media / external data)
CREATE TABLE IF NOT EXISTS sources (
    source_id SERIAL PRIMARY KEY,
    source_type VARCHAR(50) NOT NULL, -- e.g. 'twitter', 'manual_crowdsource', 'cctv'
    external_id VARCHAR(100),         -- Tweet ID or external reference ID
    source_url TEXT,                  -- URL to tweet / post
    raw_text TEXT,                    -- Raw unprocessed tweet text
    retrieved_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 5. Accidents Table (Core Spatial Table)
CREATE TABLE IF NOT EXISTS accidents (
    accident_id SERIAL PRIMARY KEY,
    event_date DATE NOT NULL,
    event_time TIME NOT NULL,
    accident_type VARCHAR(100) NOT NULL, -- e.g. 'Motorcycle', 'Car', 'Truck', 'Pedestrian', 'Multiple Vehicle'
    description TEXT,
    location_text VARCHAR(255) NOT NULL, -- e.g. 'Jalan Kaliurang KM 12'
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    geom GEOMETRY(Point, 4326),
    source_type VARCHAR(50) DEFAULT 'manual', -- 'social_media', 'manual', 'official'
    source_id INT REFERENCES sources(source_id) ON DELETE SET NULL,
    confidence NUMERIC(3, 2) DEFAULT 1.00, -- 0.00 to 1.00
    status VARCHAR(50) DEFAULT 'REPORTED' CHECK (status IN (
        'DETECTED', 'REPORTED', 'UNDER REVIEW', 'VERIFIED', 'REJECTED', 'DUPLICATE', 'RESOLVED'
    )),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create Spatial Index on geometry column
CREATE INDEX IF NOT EXISTS idx_accidents_geom ON accidents USING GIST (geom);
-- Create Temporal Index
CREATE INDEX IF NOT EXISTS idx_accidents_date ON accidents (event_date);
CREATE INDEX IF NOT EXISTS idx_accidents_status ON accidents (status);

-- 6. Tweet images attached to accident reports
CREATE TABLE IF NOT EXISTS accident_media (
    media_id SERIAL PRIMARY KEY,
    accident_id INT NOT NULL REFERENCES accidents(accident_id) ON DELETE CASCADE,
    media_url TEXT NOT NULL,
    source_url TEXT NOT NULL,
    alt_text TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_accident_media_accident ON accident_media (accident_id);

-- 7. Comments Table (Crowdsourced discussion & additional evidence)
CREATE TABLE IF NOT EXISTS comments (
    comment_id SERIAL PRIMARY KEY,
    accident_id INT NOT NULL REFERENCES accidents(accident_id) ON DELETE CASCADE,
    user_id INT REFERENCES users(user_id) ON DELETE SET NULL,
    username VARCHAR(100) DEFAULT 'Warga',
    comment_text TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'active'
);
CREATE INDEX IF NOT EXISTS idx_comments_accident ON comments (accident_id);

-- 8. Reports Table (Incoming manual citizen submissions)
CREATE TABLE IF NOT EXISTS reports (
    report_id SERIAL PRIMARY KEY,
    accident_id INT REFERENCES accidents(accident_id) ON DELETE SET NULL,
    reporter_id INT REFERENCES users(user_id) ON DELETE SET NULL,
    description TEXT NOT NULL,
    location_text VARCHAR(255),
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    photo_url TEXT,
    submitted_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    review_status VARCHAR(50) DEFAULT 'PENDING'
);

-- 9. Reviews Table (Moderator audit trail)
CREATE TABLE IF NOT EXISTS reviews (
    review_id SERIAL PRIMARY KEY,
    accident_id INT NOT NULL REFERENCES accidents(accident_id) ON DELETE CASCADE,
    reviewer_id INT REFERENCES users(user_id) ON DELETE SET NULL,
    decision VARCHAR(50) NOT NULL CHECK (decision IN ('VERIFIED', 'REJECTED', 'DUPLICATE', 'REQUEST_CLARIFICATION')),
    notes TEXT,
    reviewed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
