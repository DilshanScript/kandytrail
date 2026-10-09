USE kandytrail;
SET SQL_SAFE_UPDATES = 0;

-- ways to visit a place and how long each takes
CREATE TABLE visit_options (
    option_id    INT AUTO_INCREMENT PRIMARY KEY,
    place_id     INT NOT NULL,
    label        VARCHAR(80) NOT NULL,
    duration_min INT NOT NULL,
    is_default   BOOLEAN NOT NULL DEFAULT FALSE,
    FOREIGN KEY (place_id) REFERENCES places(place_id) ON DELETE CASCADE
);

-- opening times the planner can check, NULL means open all day
ALTER TABLE places
    ADD COLUMN open_time   TIME NULL AFTER opening_hours,
    ADD COLUMN close_time  TIME NULL AFTER open_time,
    ADD COLUMN closed_days SET('Mon','Tue','Wed','Thu','Fri','Sat','Sun') NULL AFTER close_time;

-- saved Google results so the same trip is not looked up twice
CREATE TABLE route_cache (
    from_key     VARCHAR(40) NOT NULL,
    to_place_id  INT NOT NULL,
    hour_of_day  TINYINT NOT NULL,
    distance_km  DECIMAL(6,1) NOT NULL,
    duration_min INT NOT NULL,
    saved_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (from_key, to_place_id, hour_of_day),
    FOREIGN KEY (to_place_id) REFERENCES places(place_id) ON DELETE CASCADE
);

-- current visit time becomes each place's default option
INSERT INTO visit_options (place_id, label, duration_min, is_default)
SELECT place_id, 'Standard visit', visit_duration_min, TRUE
FROM places WHERE visit_duration_min IS NOT NULL;

-- example: two ways to visit the Temple of the Tooth
UPDATE visit_options v JOIN places p ON p.place_id = v.place_id
SET v.label = 'Full visit', v.duration_min = 90
WHERE p.name LIKE '%Temple of the Tooth%';

INSERT INTO visit_options (place_id, label, duration_min, is_default)
SELECT place_id, 'Quick worship', 40, FALSE
FROM places WHERE name LIKE '%Temple of the Tooth%';

UPDATE places SET open_time = '05:30', close_time = '20:00'
WHERE name LIKE '%Temple of the Tooth%';

SET SQL_SAFE_UPDATES = 1;
