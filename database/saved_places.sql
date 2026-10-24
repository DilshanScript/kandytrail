USE kandytrail;

-- places a traveller saved to visit later
CREATE TABLE saved_places (
    user_id  INT NOT NULL,
    place_id INT NOT NULL,
    saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, place_id),
    FOREIGN KEY (user_id)  REFERENCES users(user_id)   ON DELETE CASCADE,
    FOREIGN KEY (place_id) REFERENCES places(place_id) ON DELETE CASCADE
);
