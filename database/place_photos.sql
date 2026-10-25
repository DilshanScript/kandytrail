USE kandytrail;

CREATE TABLE place_photos (
    photo_id  INT AUTO_INCREMENT PRIMARY KEY,
    place_id  INT NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    added_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (place_id) REFERENCES places(place_id) ON DELETE CASCADE
);
