# KandyTrail

KandyTrail is a web app that helps tourists find places to visit within 25 km of Kandy, Sri Lanka, and plan a one-day trip. Tourists can browse and filter attractions, read details such as opening hours, fees and travel tips, see each place on a map, and build a timed one-day route. An admin can add, edit and delete places.

ITE2953 Programming Group Project, Wickramasingha UPGCD (E2410645).

GitHub: https://github.com/DilshanScript/kandytrail

## Features

- List of 10+ tourist attractions within 25 km, with search
- Filter by category (Religious, Nature, Heritage, Cultural, Dining) and sub-type
- Place details: description, opening hours, visit time, entry fee, travel tips, distance and photos
- Google Maps location and directions for every place
- One-day trip planner: automatic wizard or pick your own places, with times and a route map
- Admin panel: login, add, edit and delete places, manage reviews
- Traveller accounts, saved places, saved trips, reviews and weather forecast

## Technologies

| Layer | Tools |
|---|---|
| Frontend | HTML5, CSS3, JavaScript, Jinja2 templates |
| Backend | Python 3, Flask |
| Database | MySQL 8, PyMySQL |
| External services | Google Maps JavaScript API, Google Routes API, Open-Meteo weather |
| Tools | VS Code, MySQL Workbench, Git and GitHub, StarUML |

## Folder structure

```
kandytrail/
  app.py              main routes (home, places, details, planner)
  admin.py            admin blueprint
  accounts.py         traveller sign up, sign in and account
  trips.py            saved trips
  traveller.py        saved places and reviews
  planner.py          one-day plan logic
  routing.py          travel times from Google Routes
  db.py               MySQL connection
  create_admin.py     creates an admin account
  database/           SQL scripts
  templates/          HTML pages
  static/             CSS, JavaScript and images
```

## Requirements

- Python 3.11 or newer
- MySQL Server 8 and MySQL Workbench
- A Google Maps API key with the Maps JavaScript API and Routes API turned on (maps and travel times do not load without it)

## Installation

1. Get the code.

   ```
   git clone https://github.com/DilshanScript/kandytrail.git
   cd kandytrail
   ```

2. Create and activate a virtual environment.

   Windows:
   ```
   python -m venv venv
   venv\Scripts\activate
   ```
   macOS or Linux:
   ```
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install the packages.

   ```
   pip install -r requirements.txt
   ```

4. Create the settings file. Copy `.env.example` to a new file named `.env` and fill in your own values.

   ```
   copy .env.example .env
   ```
   (on macOS or Linux use `cp .env.example .env`)

   | Setting | Meaning |
   |---|---|
   | DB_HOST, DB_PORT | MySQL server, usually localhost and 3306 |
   | DB_USER, DB_PASSWORD | your MySQL user and password |
   | DB_NAME | kandytrail |
   | SECRET_KEY | any long random text |
   | GOOGLE_MAPS_KEY | your Google Maps API key |

   The `.env` file holds passwords and keys, so it is not included in this submission or on GitHub.

5. Set up the database. Choose one option.

   **Option A, full database with all places (recommended).** In MySQL Workbench open `database/kandytrail_full.sql` and run it (File > Run SQL Script). This creates the `kandytrail` database with every table and all attractions.

   **Option B, empty structure from the scripts.** Run these files in MySQL Workbench in this order:

   1. `database/kandytrail_schema.sql` (creates the database, main tables and sample places)
   2. `database/planner_tables.sql`
   3. `database/place_photos.sql`
   4. `database/saved_places.sql`
   5. `database/saved_plans.sql`
   6. `database/facilities.sql`

   Then run `python database/fix_hours.py` from the project folder. `multi_category.sql` is an older upgrade script and is not needed for a new database.

6. Create an admin account.

   ```
   python create_admin.py
   ```
   Enter a username (3+ characters) and a password (8+ characters).

7. Start the app.

   ```
   python app.py
   ```
   or
   ```
   flask --app app run
   ```
   Open http://127.0.0.1:5000 in a browser. The admin panel is at http://127.0.0.1:5000/admin.

## Demo admin login

| | |
|---|---|
| Admin page | http://127.0.0.1:5000/admin |
| Username | lecturer |
| Password | KandyTrail2026 |

This account is included in `database/kandytrail_full.sql` and is only for marking. You can also create your own admin with `python create_admin.py`.

## Testing

Run the planner and routing checks with:

```
python test_planner.py
python test_routing.py
```

The full list of test cases and results is in Chapter 5 of the project report.

## Notes

- Opening hours and fees can change, so travellers are asked to check before visiting.
- Booking and payment are outside the scope of this project.
