# Little Learner Backend (Flask)

REST API for the Little Learner platform and web admin / game studio. Flask + MySQL, token auth, CORS enabled.

## Run

```
cd little-learner-backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

The API runs on http://localhost:8000.

## Database (MySQL)

Use MySQL 8 (or MariaDB 10.4 or newer, which XAMPP includes). Set the connection in `.env`:

| Variable | Default | Meaning |
|---|---|---|
| `DB_HOST` | localhost | Database server |
| `DB_PORT` | 3306 | Database port |
| `DB_NAME` or `DB_DATABASE` | little_learner | Database name (created automatically if it does not exist and the user is allowed to create it) |
| `DB_USER` or `DB_USERNAME` | root | Database user |
| `DB_PASSWORD` | empty | Database password (XAMPP's root has none) |
| `DB_SSLMODE` | empty | Set to `require` if your host needs an encrypted connection |
| `DB_POOL_MAX` | 10 | Maximum connections kept open |
| `DB_TABLE_SUFFIX` | `_little-learner` | Added to the end of every table name (for example `users_little-learner`) so these tables never clash with other tables in a shared database |
| `DATABASE_URL` | empty | A full connection string such as `mysql://user:password@host:3306/dbname`. When set it replaces all the `DB_*` connection values (Northflank gives you one) |

Both naming styles work, so Northflank's `DB_DATABASE` and `DB_USERNAME` can be pasted in as they are (`DB_CONNECTION` is ignored). If both names are set, `DB_DATABASE` and `DB_USERNAME` win. Values in `.env` may be wrapped in quotes.

The tables are created and seeded on first start. Other settings: `UPLOAD_FOLDER` (local uploads when Cloudinary is off) and `CORS_ORIGINS` (comma separated frontend URLs, `*` allows all).

### Images and songs (Cloudinary)

Uploaded images and songs are stored in Cloudinary when these are set in `.env` (find them on your Cloudinary dashboard under Settings, API Keys):

| Variable | Meaning |
|---|---|
| `CLOUDINARY_CLOUD_NAME` | Your cloud name |
| `CLOUDINARY_API_KEY` | API key |
| `CLOUDINARY_API_SECRET` | API secret (keep it private) |
| `CLOUDINARY_URL` | Optional. `cloudinary://KEY:SECRET@CLOUD_NAME` replaces the three values above |
| `CLOUDINARY_FOLDER` | Folder inside Cloudinary, default `little-learner` |

If they are empty the backend saves files in the local `uploads` folder instead. Files already uploaded locally keep working, and new uploads go to Cloudinary. Duplicate names and identical files are still detected before anything is uploaded.

### Copy data into MySQL

```
python migrate_data.py --sqlite                     # old SQLite file, default instance/little_learner.db
python migrate_data.py --sqlite path\to\file.db      # another SQLite file
python migrate_data.py --postgres "postgresql://user:password@localhost:5432/little_learner"
python migrate_data.py --sqlite --replace           # overwrite a MySQL database that already has data
```

The `--postgres` option needs the PostgreSQL driver once: `pip install "psycopg[binary]"`. The script keeps every id, so games, results and users stay linked. Uploaded files are not copied.

### Production

Run with `gunicorn -w 2 -b 0.0.0.0:$PORT run:app`, set `FLASK_DEBUG=0`, a long random `SECRET_KEY`, and `DATABASE_URL` from your host (a `mysql://` address).

Ports are set in each project's `.env` file:

| Project | Port | File |
|---|---|---|
| little-learner-platform | 3000 | `little-learner-platform/.env` |
| little-learner-webadmin | 4000 | `little-learner-webadmin/.env` |
| little-learner-backend | 8000 | `little-learner-backend/.env` |

Start each frontend with `npm run dev`. The frontends find the API through `NEXT_PUBLIC_API_URL`, and the web admin builds the publish link from `NEXT_PUBLIC_PLATFORM_URL`. Restart after changing a `.env` file.

## First admin account

On first start one super admin is created: `admin@critter.academy` / `admin123`. Change it with the `ADMIN_EMAIL` and `ADMIN_PASSWORD` environment variables before the first start. All other users, games, tickets and invoices are created through the app.

Send the token as `Authorization: Bearer <token>`.

## Endpoints

Auth: `POST /api/auth/register`, `POST /api/auth/login`, `GET|PUT /api/auth/me`

Games (public): `GET /api/games?q=&subject=&kind=&featured=1&custom=1&sort=plays|new|rating`, `GET /api/games/<id|slug>`

Game studio (creator or higher):
- `GET|POST /api/studio/games`
- `GET|PUT|DELETE /api/studio/games/<id>` (the Studio Save button uses POST then PUT)
- `POST /api/studio/games/<id>/publish` with `{"visibility": "private|link|public"}`
- `POST /api/studio/games/<id>/unpublish`, `/duplicate`
- `GET /api/studio/games/<id>/versions`, `POST /api/studio/games/<id>/restore/<versionId>`
- `GET /api/studio/games/<id>/export`
- `POST /api/studio/import` (JSON, or CSV with columns `question,answer1..4,correct`)
- `POST /api/studio/ai/generate` with `{"topic": "animals", "count": 5}`
- `POST /api/assets/upload` (multipart `file`)

Play: `POST /api/play/results`, `POST /api/play/rate`, `GET /api/play/leaderboard/<game>`, `GET /api/play/history`, `GET /api/play/me/stats`

Live: `POST /api/live/sessions`, `POST /api/live/join`, `GET /api/live/sessions/<pin>`, `POST /api/live/sessions/<pin>/start|next|end|answer`

Admin (admin or higher unless noted):
- Users: `GET|POST /api/admin/users`, `PUT|DELETE /api/admin/users/<id>`
- Games: `GET /api/admin/games`, `PATCH /api/admin/games/<id>` (featured, status, visibility)
- Stats: `GET /api/admin/dashboard`, `/api/admin/reports/summary`, `/api/admin/system`
- Collections, all with `GET|POST /api/admin/<collection>` and `GET|PUT|PATCH|DELETE /api/admin/<collection>/<id>`: `templates`, `themes`, `assets`, `moderation`, `support`, `announcements`, `rewards`, `billing`, `reports`, `i18n`, `settings`, `classes`, `assignments`, `collections`

Learner: `GET /api/me/overview`, `GET /api/me/analytics`, `GET /api/rewards`, `GET /api/me/rewards`, `POST /api/rewards/<id>/buy`, `GET /api/me/library`, `POST|DELETE /api/me/library/<gameId>`, `GET /api/announcements`, `GET /api/games/by-author/<name>`

Classes: `GET|POST /api/classes`, `POST /api/classes/join`, `GET|DELETE /api/classes/<id>`, `DELETE /api/classes/<id>/members/<userId>`, `GET|POST /api/classes/<id>/assignments`, `DELETE /api/assignments/<id>`

Health: `GET /api/health`
