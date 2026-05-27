import { Router } from "express";
import type { Response } from "express";
import { authMiddleware, type AuthRequest } from "../middlewares/auth.js";
import { getDb, dbExists } from "../lib/sqlite.js";

const router = Router();

router.get("/genres", authMiddleware, (_req: AuthRequest, res: Response) => {
  if (!dbExists()) {
    res.json([]);
    return;
  }

  const db = getDb();

  const movieGenres = db
    .prepare("SELECT genres FROM movies WHERE genres IS NOT NULL AND genres != ''")
    .all() as { genres: string }[];

  const seriesGenres = db
    .prepare("SELECT genres FROM series WHERE genres IS NOT NULL AND genres != ''")
    .all() as { genres: string }[];

  const countMap = new Map<string, number>();

  for (const row of [...movieGenres, ...seriesGenres]) {
    const parts = row.genres.split(/[,|;\n]/).map((g) => g.trim()).filter(Boolean);
    for (const g of parts) {
      countMap.set(g, (countMap.get(g) ?? 0) + 1);
    }
  }

  const genres = [...countMap.entries()]
    .sort((a, b) => b[1] - a[1])
    .map(([name, count]) => ({ name, count }));

  res.json(genres);
});

export default router;
