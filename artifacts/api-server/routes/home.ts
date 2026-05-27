import { Router } from "express";
import type { Response } from "express";
import { authMiddleware, type AuthRequest } from "../middlewares/auth.js";
import { getDb, dbExists } from "../lib/sqlite.js";

const router = Router();

router.get("/home/stats", authMiddleware, (_req: AuthRequest, res: Response) => {
  if (!dbExists()) {
    res.json({ totalMovies: 0, totalSeries: 0, newThisWeek: 0 });
    return;
  }

  const db = getDb();

  const totalMovies = (
    db.prepare("SELECT COUNT(*) as cnt FROM movies").get() as { cnt: number }
  ).cnt;

  const totalSeries = (
    db.prepare("SELECT COUNT(*) as cnt FROM series").get() as { cnt: number }
  ).cnt;

  const oneWeekAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000)
    .toISOString()
    .slice(0, 19)
    .replace("T", " ");

  let newMovies = 0;
  try {
    newMovies = (
      db
        .prepare("SELECT COUNT(*) as cnt FROM movies WHERE added_date >= ?")
        .get(oneWeekAgo) as { cnt: number }
    ).cnt;
  } catch {
    try {
      newMovies = (
        db
          .prepare("SELECT COUNT(*) as cnt FROM movies WHERE created_at >= ?")
          .get(oneWeekAgo) as { cnt: number }
      ).cnt;
    } catch {
      newMovies = 0;
    }
  }

  res.json({ totalMovies, totalSeries, newThisWeek: newMovies });
});

export default router;
