-- KandyTrail database schema

DROP DATABASE IF EXISTS kandytrail;
CREATE DATABASE kandytrail CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE kandytrail;

-- categories
CREATE TABLE categories (
    category_id INT AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(50) NOT NULL UNIQUE
);

-- sub_types
CREATE TABLE sub_types (
    sub_type_id INT AUTO_INCREMENT PRIMARY KEY,
    category_id INT NOT NULL,
    name        VARCHAR(50) NOT NULL,
    UNIQUE (category_id, name),
    FOREIGN KEY (category_id) REFERENCES categories(category_id)
);

-- places
CREATE TABLE places (
    place_id           INT AUTO_INCREMENT PRIMARY KEY,
    name               VARCHAR(150) NOT NULL,
    category_id        INT NOT NULL,
    sub_type_id        INT NULL,
    short_description  VARCHAR(300),
    description        TEXT,
    latitude           DECIMAL(9,6),
    longitude          DECIMAL(9,6),
    distance_km        DECIMAL(5,1),
    opening_hours      VARCHAR(200),
    visit_duration_min INT,
    price_level        ENUM('Free','Budget','Mid-range','Premium'),
    entry_fee          VARCHAR(150),
    travel_tips        TEXT,
    contact            VARCHAR(150),
    image_file         VARCHAR(255),
    created_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories(category_id),
    FOREIGN KEY (sub_type_id) REFERENCES sub_types(sub_type_id)
);

-- admins
CREATE TABLE admins (
    admin_id      INT AUTO_INCREMENT PRIMARY KEY,
    username      VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- users
CREATE TABLE users (
    user_id       INT AUTO_INCREMENT PRIMARY KEY,
    full_name     VARCHAR(100) NOT NULL,
    email         VARCHAR(150) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- reviews
CREATE TABLE reviews (
    review_id  INT AUTO_INCREMENT PRIMARY KEY,
    user_id    INT NOT NULL,
    place_id   INT NOT NULL,
    rating     TINYINT NOT NULL CHECK (rating BETWEEN 1 AND 5),
    comment    TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, place_id),
    FOREIGN KEY (user_id)  REFERENCES users(user_id)   ON DELETE CASCADE,
    FOREIGN KEY (place_id) REFERENCES places(place_id) ON DELETE CASCADE
);

-- saved_preferences
CREATE TABLE saved_preferences (
    preference_id  INT AUTO_INCREMENT PRIMARY KEY,
    user_id        INT NOT NULL UNIQUE,
    start_label    VARCHAR(150),
    start_latitude  DECIMAL(9,6),
    start_longitude DECIMAL(9,6),
    interests      VARCHAR(255),
    number_of_places TINYINT,
    include_lunch  BOOLEAN DEFAULT TRUE,
    budget         ENUM('Free','Budget','Mid-range','Premium'),
    transport      ENUM('Car','Tuk-tuk','Bus','Walking'),
    updated_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Default data

INSERT INTO categories (name) VALUES
('Religious'), ('Nature'), ('Heritage'), ('Cultural'), ('Dining');

INSERT INTO sub_types (category_id, name) VALUES
(1, 'Temple'), (1, 'Devalaya'),
(2, 'Waterfall'), (2, 'Mountain / Hiking'), (2, 'Lake'), (2, 'Garden / Park'), (2, 'River / Bathing spot'),
(3, 'Museum'), (3, 'Fort / Ruins'), (3, 'Ancient shrine'),
(4, 'Cultural show'),
(5, 'Cafe'), (5, 'Bakery'), (5, 'Local restaurant'), (5, 'Hotel restaurant');

-- Sample places
INSERT INTO places
(name, category_id, sub_type_id, short_description, latitude, longitude, distance_km,
 opening_hours, visit_duration_min, price_level, entry_fee, travel_tips)
VALUES
('Sri Dalada Maligawa (Temple of the Tooth)', 1, 1,
 'UNESCO World Heritage temple that houses the sacred Tooth Relic of the Buddha.',
 7.293600, 80.641300, 11, 'Daily 5:30am - 8:00pm', 90, 'Budget',
 'Free for locals, ticket for foreign visitors',
 'Wear white or light clothes that cover shoulders and knees. Shoes are removed at the entrance.'),

('Sri Maha Bodhi Viharaya (Bahirawakanda)', 1, 1,
 'Hilltop temple with an 88-foot white Buddha statue and views over Kandy city.',
 7.295500, 80.629000, 11, 'Daily 6:00am - 6:00pm', 45, 'Budget',
 'Small ticket', 'Best views in the early morning or near sunset.'),

('Royal Botanic Gardens, Peradeniya', 2, 6,
 'Historic 147-acre garden with orchids, giant bamboo and the famous Java fig tree.',
 7.268300, 80.596700, 13, 'Daily 7:30am - 5:00pm', 120, 'Budget',
 'Ticket (lower price for locals)', 'Bring water and wear comfortable shoes, the garden is large.'),

('Kandy Lake', 2, 5,
 'Historic lake in the centre of Kandy with a 3.4 km walking path.',
 7.291500, 80.645000, 11, 'Open all day', 45, 'Free',
 'Free', 'Walk the path in the evening when it is cooler.'),

('Hela Bojun Hala - Gannoruwa', 5, 14,
 'Traditional Sri Lankan food centre with fresh local dishes and herbal drinks at low prices.',
 7.281000, 80.592000, 11, 'Daily 7:00am - 7:00pm', 45, 'Budget',
 'Pay for what you eat', 'Try the hoppers and herbal porridge. Busy around lunchtime.');
