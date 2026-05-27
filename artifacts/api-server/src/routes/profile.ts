import { Router } from "express";
import type { Response } from "express";
import { authMiddleware, type AuthRequest } from "../middlewares/auth.js";
import { getDb, dbExists } from "../lib/sqlite.js";

const router = Router();

router.get("/users/profile", authMiddleware, (req: AuthRequest, res: Response) => {
  if (!dbExists()) {
    res.status(503).json({ error: "Database not ready" });
    return;
  }

  const db = getDb();
  const userId = req.userId!;

  const user = db.prepare("SELECT * FROM users WHERE id = ?").get(userId) as
    | Record<string, unknown>
    | undefined;

  if (!user) {
    res.status(404).json({ error: "User not found" });
    return;
  }

  const isPremium = Boolean(user["is_premium"]);
  const premiumUntil = user["premium_until"] as string | null;

  res.json({
    tgId: Number(user["tg_id"]),
    username: (user["username"] as string | null) ?? null,
    fullName: String(user["full_name"] ?? ""),
    lang: String(user["lang"] ?? "uz"),
    isPremium,
    premiumUntil: premiumUntil ?? null,
    balance: Number(user["balance"] ?? 0),
    photoUrl: (user["photo_url"] as string | null) ?? null,
  });
});

export default router;
