DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'booking_status') THEN
        CREATE TYPE booking_status AS ENUM ('CONFIRMED', 'FAILED');
    END IF;
END
$$;

CREATE TABLE IF NOT EXISTS bookings (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    event_id INTEGER NOT NULL,
    tickets INTEGER NOT NULL CHECK (tickets > 0),
    total_price DOUBLE PRECISION NOT NULL CHECK (total_price >= 0),
    status booking_status NOT NULL DEFAULT 'CONFIRMED',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_bookings_user_id ON bookings (user_id);
CREATE INDEX IF NOT EXISTS ix_bookings_event_id ON bookings (event_id);
CREATE INDEX IF NOT EXISTS ix_bookings_status ON bookings (status);
