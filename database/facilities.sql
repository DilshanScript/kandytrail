USE kandytrail;

ALTER TABLE places
    ADD COLUMN facilities SET('Parking','Toilets','Restaurant','Drinking water','Wheelchair access','Shops','Guide service') NULL AFTER contact,
    ADD COLUMN transport VARCHAR(300) NULL AFTER facilities;
