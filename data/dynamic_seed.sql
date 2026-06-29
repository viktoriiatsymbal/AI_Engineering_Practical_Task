INSERT INTO parking_spaces (zone, is_available, hourly_price) VALUES
    ('A', true, 2.50),
    ('B', true, 3.00),
    ('C', false, 2.00),
    ('VIP', true, 6.00);

INSERT INTO working_hours (day_of_week, open_time, close_time) VALUES
    ('Monday', '07:00', '23:00'),
    ('Tuesday', '07:00', '23:00'),
    ('Wednesday', '07:00', '23:00'),
    ('Thursday', '07:00', '23:00'),
    ('Friday', '07:00', '23:00'),
    ('Saturday', '08:00', '22:00'),
    ('Sunday', '08:00', '20:00');
