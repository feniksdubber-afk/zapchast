import Database from "better-sqlite3";
import path from "node:path";
import fs from "node:fs";
import { logger } from "./logger.js";

const DB_PATH =
  process.env["DB_PATH"] ??
  (process.env["NODE_ENV"] === "production"
    ? "/data/kinobot.db"
    : path.join(process.cwd(), "data", "kinobot.db"));

let _db: Database.Database | null = null;

export function getDb(): Database.Database {
  if (_db) return _db;

  if (!fs.existsSync(DB_PATH)) {
    logger.warn(
      { path: DB_PATH },
      "SQLite database not found — bot may not have been run yet. Returning empty results.",
    );
  }

  _db = new Database(DB_PATH);
  _db.pragma("journal_mode = WAL");
  _db.pragma("foreign_keys = ON");
  _db.pragma("cache_size = -4000");
  _db.pragma("busy_timeout = 5000");

  logger.info({ path: DB_PATH }, "SQLite database connected");
  return _db;
}

export function dbExists(): boolean {
  return fs.existsSync(DB_PATH);
}
