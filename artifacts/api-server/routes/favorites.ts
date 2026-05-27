import { Router } from "express";
import type { Response } from "express";
import { authMiddleware, type AuthRequest } from "../middlewares/auth.js";
import { getDb, dbExists } from "../lib/sqlite.js";
import { makePosterUrl } from "../lib/telegram.js";

const router = Router();

router.get("/favorites", authMiddleware, (req: AuthRequest, res: Response) => {
  if (!dbExists()) {
    res.json([]);
    return;
  }

  const db = getDb();
  const userId = req.userId!;

  const rows = db
    .prepare(
      `SELECT f.id, f.movie_id, f.series_id,
        COALESCE(m.title_uz, m.title_ru, s.title_uz, s.title_ru, '—') as title,
        COALESCE(m.poster_file_id, s.poster_file_id) as poster_file_id,
        COALESCE(m.is_premium, s.is_premium, 0) as is_premium,
        CASE WHEN f.movie_id IS NOT NULL THEN 'movie' ELSE 'series' END as type
      FROM favorites f
      LEFT JOIN movies m ON f.movie_id = m.id
      LEFT JOIN series s ON f.series_id = s.id
      WHERE f.user_id = ?
      ORDER BY f.id DESC`,
    )
    .all(userId) as {
    id: number;
    movie_id: number | null;
    series_id: number | null;
    title: string;
    poster_file_id: string | null;
    is_premium: number;
    type: string;
  }[];

  res.json(
    rows.map((r) => ({
      id: r.id,
      movieId: r.movie_id,
      seriesId: r.series_id,
      title: r.title,
      posterUrl: makePosterUrl(r.poster_file_id),
      isPremium: Boolean(r.is_premium),
      type: r.type,
    })),
  );
});

router.post("/favorites", authMiddleware, (req: AuthRequest, res: Response) => {
  if (!dbExists()) {
    res.status(503).json({ error: "Database not ready" });
    return;
  }

  const db = getDb();
  const userId = req.userId!;
  const { movieId, seriesId } = req.body as {
    movieId?: number | null;
    seriesId?: number | null;
  };

  if (!movieId && !seriesId) {
    res.status(400).json({ error: "movieId or seriesId required" });
    return;
  }

  const existing = db
    .prepare(
      "SELECT id FROM favorites WHERE user_id = ? AND movie_id IS ? AND series_id IS ?",
    )
    .get(userId, movieId ?? null, seriesId ?? null) as { id: number } | undefined;

  if (existing) {
    db.prepare("DELETE FROM favorites WHERE id = ?").run(existing.id);
    res.json({ favorited: false });
  } else {
    db.prepare(
      "INSERT OR IGNORE INTO favorites (user_id, movie_id, series_id, created_at) VALUES (?, ?, ?, datetime('now'))",
    ).run(userId, movieId ?? null, seriesId ?? null);
    res.json({ favorited: true });
  }
});

export default router;
