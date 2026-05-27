import { Router } from "express";
import type { Response } from "express";
import { authMiddleware, type AuthRequest } from "../middlewares/auth.js";
import { getDb, dbExists } from "../lib/sqlite.js";
import { makePosterUrl, getTelegramFileUrl } from "../lib/telegram.js";

const router = Router();

type MovieRow = {
  id: number;
  title: string | null;
  year: number | null;
  country: string | null;
  genres: string | null;
  description: string | null;
  poster_file_id: string | null;
  video_file_id: string | null;
  is_premium: number;
  rating: number | null;
  views: number | null;
  added_date: string | null;
};

function toMovieSummary(row: MovieRow) {
  return {
    id: row.id,
    title: row.title ?? "—",
    posterUrl: makePosterUrl(row.poster_file_id),
    year: row.year ?? null,
    rating: row.rating ?? 0,
    isPremium: Boolean(row.is_premium),
    isSeries: false,
  };
}

function toMovieDetail(row: MovieRow) {
  return {
    id: row.id,
    title: row.title ?? "—",
    posterUrl: makePosterUrl(row.poster_file_id),
    year: row.year ?? null,
    rating: row.rating ?? 0,
    isPremium: Boolean(row.is_premium),
    country: row.country ?? null,
    genres: row.genres ?? null,
    description: row.description ?? null,
    views: row.views ?? 0,
  };
}

router.get("/movies/featured", authMiddleware, (_req: AuthRequest, res: Response) => {
  if (!dbExists()) {
    res.json({ trending: [], recent: [], newSeries: [] });
    return;
  }

  const db = getDb();

  const trending = (
    db.prepare(`SELECT * FROM movies ORDER BY views DESC, id DESC LIMIT 10`).all() as MovieRow[]
  ).map(toMovieSummary);

  const recent = (
    db.prepare(`SELECT * FROM movies ORDER BY id DESC LIMIT 10`).all() as MovieRow[]
  ).map(toMovieSummary);

  type SeriesRow = {
    id: number;
    title_uz: string | null;
    title_ru: string | null;
    year: number | null;
    genres: string | null;
    poster_file_id: string | null;
    is_premium: number;
  };

  const newSeriesRows = db.prepare(`SELECT * FROM series ORDER BY id DESC LIMIT 10`).all() as SeriesRow[];

  const newSeries = newSeriesRows.map((s) => ({
    id: s.id,
    titleUz: s.title_uz ?? s.title_ru ?? "—",
    titleRu: s.title_ru ?? null,
    posterUrl: makePosterUrl(s.poster_file_id),
    year: s.year ?? null,
    isPremium: Boolean(s.is_premium),
    genres: s.genres ?? null,
  }));

  res.json({ trending, recent, newSeries });
});

router.get("/movies", authMiddleware, (req: AuthRequest, res: Response) => {
  if (!dbExists()) {
    res.json({ movies: [], hasMore: false, total: 0 });
    return;
  }

  const db = getDb();
  const page = Math.max(0, Number(req.query["page"] ?? 0));
  const limit = Math.min(50, Math.max(1, Number(req.query["limit"] ?? 18)));
  const genre = (req.query["genre"] as string | undefined) ?? "";

  let where = "";
  const params: unknown[] = [];

  if (genre) {
    where = "WHERE genres LIKE ?";
    params.push(`%${genre}%`);
  }

  const total = (
    db.prepare(`SELECT COUNT(*) as cnt FROM movies ${where}`).get(...params) as { cnt: number }
  ).cnt;

  const rows = db
    .prepare(`SELECT * FROM movies ${where} ORDER BY id DESC LIMIT ? OFFSET ?`)
    .all(...params, limit + 1, page * limit) as MovieRow[];

  const hasMore = rows.length > limit;
  if (hasMore) rows.pop();

  res.json({ movies: rows.map(toMovieSummary), hasMore, total });
});

router.get("/movies/:id", authMiddleware, (req: AuthRequest, res: Response) => {
  if (!dbExists()) {
    res.status(404).json({ error: "Not found" });
    return;
  }

  const db = getDb();
  const id = Number(req.params["id"]);

  const row = db.prepare("SELECT * FROM movies WHERE id = ?").get(id) as MovieRow | undefined;

  if (!row) {
    res.status(404).json({ error: "Movie not found" });
    return;
  }

  db.prepare("UPDATE movies SET views = COALESCE(views, 0) + 1 WHERE id = ?").run(id);

  res.json(toMovieDetail(row));
});

router.get("/movies/:id/stream-url", authMiddleware, async (req: AuthRequest, res: Response) => {
  if (!dbExists()) {
    res.status(404).json({ error: "Not found" });
    return;
  }

  const db = getDb();
  const id = Number(req.params["id"]);

  const row = db.prepare("SELECT * FROM movies WHERE id = ?").get(id) as MovieRow | undefined;

  if (!row) {
    res.status(404).json({ error: "Movie not found" });
    return;
  }

  if (row.is_premium) {
    const userId = req.userId!;
    const user = db.prepare("SELECT * FROM users WHERE id = ?").get(userId) as
      | Record<string, unknown>
      | undefined;

    const isPremium = Boolean(user?.["is_premium"]);
    const premiumUntil = user?.["premium_until"] as string | null;
    const isActive = isPremium && premiumUntil && new Date(premiumUntil) > new Date();

    if (!isActive) {
      res.status(403).json({ error: "Premium obuna kerak" });
      return;
    }
  }

  const fileId = row.video_file_id ?? row.poster_file_id;

  if (!fileId) {
    res.status(404).json({ error: "Video fayl topilmadi" });
    return;
  }

  const url = await getTelegramFileUrl(fileId);
  if (!url) {
    res.status(503).json({ error: "Stream URL olib bo'lmadi" });
    return;
  }

  res.json({ url });
});

export default router;
