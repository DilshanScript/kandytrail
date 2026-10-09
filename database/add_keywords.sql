USE kandytrail;

ALTER TABLE places ADD COLUMN keywords VARCHAR(300) AFTER description;

UPDATE places SET keywords = 'tooth relic, buddhist, unesco, perahera, palace, worship' WHERE place_id = 1;
UPDATE places SET keywords = 'buddha statue, viewpoint, hill, city view, buddhist' WHERE place_id = 2;
UPDATE places SET keywords = 'botanical, flowers, orchids, trees, picnic, family, walking' WHERE place_id = 3;
UPDATE places SET keywords = 'walking, evening, city centre, photos, relax' WHERE place_id = 4;
UPDATE places SET keywords = 'lunch, sri lankan food, rice and curry, hoppers, cheap, vegetarian' WHERE place_id = 5;
