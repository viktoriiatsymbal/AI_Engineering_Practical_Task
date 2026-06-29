ALTER TABLE reservations
    ADD COLUMN IF NOT EXISTS admin_request_status VARCHAR(30)
    NOT NULL DEFAULT 'not_sent';

ALTER TABLE reservations
    ADD COLUMN IF NOT EXISTS admin_request_error TEXT;

CREATE TABLE IF NOT EXISTS admin_reviews (
    id SERIAL PRIMARY KEY,
    reservation_id INTEGER NOT NULL UNIQUE
        REFERENCES reservations(id),
    thread_id VARCHAR(255) NOT NULL UNIQUE,
    state VARCHAR(30) NOT NULL DEFAULT 'pending_admin',
    proposed_action VARCHAR(50),
    admin_comment TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    decided_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS ix_admin_reviews_thread_id
    ON admin_reviews(thread_id);

CREATE INDEX IF NOT EXISTS ix_admin_reviews_state
    ON admin_reviews(state);
