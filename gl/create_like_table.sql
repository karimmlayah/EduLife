-- SQL script to create the Like table manually
-- Run this in your SQLite database if migration doesn't work

CREATE TABLE IF NOT EXISTS "UserApp_like" (
    "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    "created_at" datetime NOT NULL,
    "post_id" bigint NOT NULL REFERENCES "UserApp_post" ("id") DEFERRABLE INITIALLY DEFERRED,
    "user_id" integer NOT NULL REFERENCES "UserApp_customuser" ("id") DEFERRABLE INITIALLY DEFERRED
);

CREATE INDEX IF NOT EXISTS "UserApp_like_post_id_idx" ON "UserApp_like" ("post_id");
CREATE INDEX IF NOT EXISTS "UserApp_like_user_id_idx" ON "UserApp_like" ("user_id");

CREATE UNIQUE INDEX IF NOT EXISTS "UserApp_like_post_id_user_id_unique" ON "UserApp_like" ("post_id", "user_id");

-- Mark migration as applied
INSERT OR IGNORE INTO "django_migrations" ("app", "name", "applied") VALUES ('UserApp', '0011_like', datetime('now'));

