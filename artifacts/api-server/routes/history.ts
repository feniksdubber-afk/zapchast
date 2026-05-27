import { Router } from "express";
import type { Response } from "express";
import { authMiddleware, type AuthRequest } from "../middlewares/auth.js";
import { getDb, dbExists } from "../lib/sqlite.js";

const router = Router();

router.get("/watch-history", authMiddleware, (req: AuthRequest, res: Response) => {
  if (!dbExists()) {
    res.json([]);
    return;
  }

  const db = getDb();
  const userId = req.userId!;

  const rows = db
    .prepare(
      `SELECT wh.id,
        COALESCE(m.title_uz, m.title_ru, s.title_uz, s.title_ru, '—') as title,
        wh.movie_id, wh.series_id,
        CASE WHEN wh.movie_id IS NOT NULL THEN 'movie' ELSE 'series' END as type,
        wh.season_number, wh.episode_number,
        wh.watched_at
      FROM watch_history wh
      LEFT JOIN movies m ON wh.movie_id = m.id
      LEFT JOIN series s ON wh.series_id = s.id
      WHERE wh.user_id = ?
      ORDER BY wh.watched_at DESC
      LIMIT 50`,
    )
    .all(userId) as {
    id: number;
    title: string;
    movie_id: number | null;
    series_id: number | null;
    type: string;
    season_number: number | null;
    episode_number: number | null;
    watched_at: string;
  }[];

  res.json(
    rows.map((r) => ({
      id: r.id,
      title: r.title,
      movieId: r.movie_id,
      seriesId: r.series_id,
      type: r.type,
      seasonNumber: r.season_number,
      episodeNumber: r.episode_number,
      watchedAt: r.watched_at,
    })),
  );
});

router.post("/watch-history", authMiddleware, (req: AuthRequest, res: Response) => {
  if (!dbExists()) {
    res.json({ ok: true });
    return;
  }

  const db = getDb();
  const userId = req.userId!;
  const { movieId, seriesId, seasonNumber, episodeNumber } = req.body as {
    movieId?: number | null;
    seriesId?: number | null;
    seasonNumber?: number | null;
    episodeNumber?: number | null;
  };

  if (!movieId && !seriesId) {
    res.status(400).json({ error: "movieId or seriesId required" });
    return;
  }

  db.prepare(
    `INSERT INTO watch_history (user_id, movie_id, series_id, season_number, episode_number, watched_at)
     VALUES (?, ?, ?, ?, ?, datetime('now'))`,
  ).run(userId, movieId ?? null, seriesId ?? null, seasonNumber ?? null, episodeNumber ?? null);

  res.json({ ok: true });
});

export default router;
