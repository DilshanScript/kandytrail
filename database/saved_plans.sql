USE kandytrail;

CREATE TABLE saved_plans (
    plan_id         INT AUTO_INCREMENT PRIMARY KEY,
    user_id         INT NOT NULL,
    name            VARCHAR(100) NOT NULL,
    start_label     VARCHAR(150) NOT NULL,
    start_latitude  DECIMAL(9,6) NOT NULL,
    start_longitude DECIMAL(9,6) NOT NULL,
    start_time      TIME NOT NULL,
    end_time        TIME NOT NULL,
    vehicle         VARCHAR(20) NOT NULL,
    finish          ENUM('start','kandy','last') NOT NULL DEFAULT 'kandy',
    rating          TINYINT NULL CHECK (rating BETWEEN 1 AND 5),
    notes           TEXT,
    is_public       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE TABLE saved_plan_stops (
    plan_id   INT NOT NULL,
    position  TINYINT NOT NULL,
    place_id  INT NOT NULL,
    option_id INT NULL,
    meal      ENUM('breakfast','lunch') NULL,
    PRIMARY KEY (plan_id, position),
    FOREIGN KEY (plan_id)   REFERENCES saved_plans(plan_id)    ON DELETE CASCADE,
    FOREIGN KEY (place_id)  REFERENCES places(place_id)        ON DELETE CASCADE,
    FOREIGN KEY (option_id) REFERENCES visit_options(option_id) ON DELETE SET NULL
);
