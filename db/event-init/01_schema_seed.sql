DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'event_status') THEN
        CREATE TYPE event_status AS ENUM ('ACTIVE', 'CANCELLED', 'SOLD_OUT');
    END IF;
END
$$;

CREATE TABLE IF NOT EXISTS events (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    venue VARCHAR(255) NOT NULL,
    event_date TIMESTAMP WITH TIME ZONE NOT NULL,
    price DOUBLE PRECISION NOT NULL CHECK (price >= 0),
    available_seats INTEGER NOT NULL CHECK (available_seats >= 0),
    status event_status NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_events_name ON events (name);
CREATE INDEX IF NOT EXISTS ix_events_event_date ON events (event_date);
CREATE INDEX IF NOT EXISTS ix_events_status ON events (status);

INSERT INTO events (id, name, venue, event_date, price, available_seats, status)
VALUES
    (
        1,
        'Cloud Native Summit',
        'Main Auditorium',
        '2026-06-15T18:00:00Z',
        1499.00,
        100,
        'ACTIVE'
    ),
    (
        2,
        'Distributed Systems Workshop',
        'Tech Park Hall B',
        '2026-07-05T10:00:00Z',
        999.00,
        60,
        'ACTIVE'
    ),
    (
        3,
        'LivePass Music Night',
        'Open Air Arena',
        '2026-08-20T19:30:00Z',
        799.00,
        250,
        'ACTIVE'
    ),
    (
        4,
        'Database Scaling Bootcamp',
        'Innovation Center',
        '2026-09-12T09:30:00Z',
        1299.00,
        40,
        'ACTIVE'
    ),
    (
        5,
        'Legacy Event Cancelled',
        'City Convention Center',
        '2026-10-01T17:00:00Z',
        499.00,
        80,
        'CANCELLED'
    )
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    venue = EXCLUDED.venue,
    event_date = EXCLUDED.event_date,
    price = EXCLUDED.price,
    available_seats = EXCLUDED.available_seats,
    status = EXCLUDED.status;

SELECT setval('events_id_seq', (SELECT MAX(id) FROM events));
