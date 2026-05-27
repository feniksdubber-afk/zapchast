import { Router } from "express";
import type { Response } from "express";
import { authMiddleware, type AuthRequest } from "../middlewares/auth.js";
import { getDb, dbExists } from "../lib/sqlite.js";
import { makePosterUrl } from "../lib/telegram.js";

const router = Router();

router.get("/search", authMiddleware, (req: AuthRequest, res: Response) => {
  const q = ((req.query["q"] as string) ?? "").trim();

  if (!q) {
    res.json({ movies: [], series: [] });
    return;
  }

  if (!dbExists()) {
    res.json({ movies: [], series: [] });
    return;
  }

  const db = getDb();
  const pattern = `%${q}%`;

  const movies = db
    .prepare(
      `SELECT id, title, poster_file_id, year, rating, is_premium
       FROM movies
       WHERE title LIKE ?
       LIMIT 20`,
    )
    .all(pattern) as {
    id: number;
    title: string | null;
    poster_file_id: string | null;
    year: number | null;
    rating: number | null;
    is_premium: number;
  }[];

  const series = db
    .prepare(
      `SELECT id, title_uz, title_ru, poster_file_id, year, genres, is_premium
       FROM series
       WHERE title_uz LIKE ? OR title_ru LIKE ?
       LIMIT 20`,
    )
    .all(pattern, pattern) as {
    id: number;
    title_uz: string | null;
    title_ru: string | null;
    poster_file_id: string | null;
    year: number | null;
    genres: string | null;
    is_premium: number;
  }[];

  res.json({
    movies: movies.map((m) => ({
      id: m.id,
      title: m.title ?? "—",
      posterUrl: makePosterUrl(m.poster_file_id),
      year: m.year ?? null,
      rating: m.rating ?? 0,
      isPremium: Boolean(m.is_premium),
      isSeries: false,
    })),
    series: series.map((s) => ({
      id: s.id,
      titleUz: s.title_uz ?? s.title_ru ?? "—",
      titleRu: s.title_ru ?? null,
      posterUrl: makePosterUrl(s.poster_file_id),
      year: s.year ?? null,
      isPremium: Boolean(s.is_premium),
      genres: s.genres ?? null,
    })),
  });
});

export default router;
