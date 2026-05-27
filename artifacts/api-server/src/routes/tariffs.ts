import { Router } from "express";
import type { Response } from "express";
import { authMiddleware, type AuthRequest } from "../middlewares/auth.js";
import { getDb, dbExists } from "../lib/sqlite.js";

const router = Router();

router.get("/tariffs", authMiddleware, (_req: AuthRequest, res: Response) => {
  if (!dbExists()) {
    res.json([]);
    return;
  }

  const db = getDb();

  const rows = db.prepare("SELECT * FROM tariffs ORDER BY price ASC").all() as {
    id: number;
    name: string | null;
    duration: number | null;
    price: number | null;
    description: string | null;
    points_price: number | null;
  }[];

  res.json(
    rows.map((r) => ({
      id: r.id,
      name: r.name ?? "—",
      duration: r.duration ?? 30,
      price: r.price ?? 0,
      description: r.description ?? null,
      pointsPrice: r.points_price ?? 0,
    })),
  );
});

export default router;
