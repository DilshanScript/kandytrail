USE kandytrail;

-- a place can belong to more than one category and type
CREATE TABLE place_categories (
    place_id    INT NOT NULL,
    category_id INT NOT NULL,
    PRIMARY KEY (place_id, category_id),
    FOREIGN KEY (place_id)    REFERENCES places(place_id) ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES categories(category_id)
);

CREATE TABLE place_sub_types (
    place_id    INT NOT NULL,
    sub_type_id INT NOT NULL,
    PRIMARY KEY (place_id, sub_type_id),
    FOREIGN KEY (place_id)    REFERENCES places(place_id) ON DELETE CASCADE,
    FOREIGN KEY (sub_type_id) REFERENCES sub_types(sub_type_id)
);

-- copy the current category and type of each place
INSERT INTO place_categories (place_id, category_id)
SELECT place_id, category_id FROM places;

INSERT INTO place_sub_types (place_id, sub_type_id)
SELECT place_id, sub_type_id FROM places WHERE sub_type_id IS NOT NULL;
