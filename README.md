# Little Learner Backend (Flask)

REST API for the Little Learner platform and web admin / game studio. Flask + PostgreSQL, token auth, CORS enabled.

## Run

```
cd little-learner-backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

The API runs on http://localhost:8000.

## Database (PostgreSQL)

Install PostgreSQL 14 or newer, then set the connection in `.env`:

| Variable | Default | Meaning |
|---|---|---|
| `DB_HOST` | localhost | Database server |
| `DB_PORT` | 5432 | Database port |
| `DB_NAME` | little_learner | Database name (created automatically if it does not exist) |
| `DB_USER` | postgres | Database user |
| `DB_PASSWORD` | postgres | Database password |
| `DB_SSLMODE` | empty | Set to `require` for hosted databases |
| `DB_POOL_MAX` | 10 | Maximum connections kept open |
| `DB_TABLE_SUFFIX` | `_little-learner` | Added to the end of every table name (for example `users_little-learner`) so these tables never clash with other tables in a shared database. Leave empty for plain names |
| `DATABASE_URL` | empty | A full connection string. When set it replaces all the `DB_*` values (Northflank and most hosts give you one) |

The tables are created and seeded on first start. Other settings: `UPLOAD_FOLDER` (where uploaded images and songs are stored) and `CORS_ORIGINS` (comma separated frontend URLs, `*` allows all).

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

### Move your old SQLite data into PostgreSQL

If you ran an earlier version with SQLite, copy that data once:

```
python migrate_sqlite.py                      # reads instance/little_learner.db
python migrate_sqlite.py path\to\file.db      # or point at another file
python migrate_sqlite.py --replace            # overwrite a database that already has data
```

The script keeps every id, so games, results and users stay linked. Uploaded files stay in the uploads folder.

### Production

Run with `gunicorn -w 2 -b 0.0.0.0:$PORT run:app`, set `FLASK_DEBUG=0`, a long random `SECRET_KEY`, and `DATABASE_URL` from your host.

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
