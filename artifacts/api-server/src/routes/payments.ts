import { Router } from "express";
import type { Response } from "express";
import { authMiddleware, type AuthRequest } from "../middlewares/auth.js";
import { getDb, dbExists } from "../lib/sqlite.js";

const router = Router();

type SubscriptionSettings = {
  card_number: string | null;
  card_owner: string | null;
};

router.post("/payments", authMiddleware, (req: AuthRequest, res: Response) => {
  if (!dbExists()) {
    res.status(503).json({ error: "Baza tayyor emas" });
    return;
  }

  const db = getDb();
  const userId = req.userId!;
  const { tariffId } = req.body as { tariffId?: number };

  if (!tariffId) {
    res.status(400).json({ error: "tariffId kerak" });
    return;
  }

  const tariff = db.prepare("SELECT * FROM tariffs WHERE id = ?").get(tariffId) as
    | { id: number; name: string | null; price: number | null; duration: number | null }
    | undefined;

  if (!tariff) {
    res.status(404).json({ error: "Tarif topilmadi" });
    return;
  }

  const settings = db
    .prepare("SELECT card_number, card_owner FROM subscription_settings LIMIT 1")
    .get() as SubscriptionSettings | undefined;

  const cardNumber = settings?.card_number ?? "0000 0000 0000 0000";
  const cardOwner = settings?.card_owner ?? "AFSONA TV";

  const result = db
    .prepare(
      `INSERT INTO payments (user_id, tariff_id, amount, status, created_at)
       VALUES (?, ?, ?, 'pending', datetime('now'))`,
    )
    .run(userId, tariffId, tariff.price ?? 0);

  res.json({
    paymentId: result.lastInsertRowid,
    cardNumber,
    cardOwner,
    amount: tariff.price ?? 0,
    tariffName: tariff.name ?? "—",
  });
});

router.post("/payments/points", authMiddleware, (req: AuthRequest, res: Response) => {
  if (!dbExists()) {
    res.status(503).json({ error: "Baza tayyor emas" });
    return;
  }

  const db = getDb();
  const userId = req.userId!;
  const { tariffId } = req.body as { tariffId?: number };

  if (!tariffId) {
    res.status(400).json({ error: "tariffId kerak" });
    return;
  }

  const tariff = db.prepare("SELECT * FROM tariffs WHERE id = ?").get(tariffId) as
    | {
        id: number;
        name: string | null;
        price: number | null;
        duration: number | null;
        points_price: number | null;
      }
    | undefined;

  if (!tariff) {
    res.status(404).json({ error: "Tarif topilmadi" });
    return;
  }

  const pointsRequired = tariff.points_price ?? 0;

  const user = db.prepare("SELECT * FROM users WHERE id = ?").get(userId) as
    | Record<string, unknown>
    | undefined;

  if (!user) {
    res.status(404).json({ error: "Foydalanuvchi topilmadi" });
    return;
  }

  const balance = Number(user["balance"] ?? 0);

  if (balance < pointsRequired) {
    res.status(400).json({
      error: `Balans yetarli emas. Kerak: ${pointsRequired}, mavjud: ${balance}`,
    });
    return;
  }

  const durationDays = tariff.duration ?? 30;
  const now = new Date();
  const currentPremiumUntil = user["premium_until"]
    ? new Date(String(user["premium_until"]))
    : now;
  const baseDate = currentPremiumUntil > now ? currentPremiumUntil : now;
  const newPremiumUntil = new Date(baseDate.getTime() + durationDays * 24 * 60 * 60 * 1000);
  const newBalance = balance - pointsRequired;

  db.prepare(
    `UPDATE users SET is_premium = 1, premium_until = ?, balance = ? WHERE id = ?`,
  ).run(newPremiumUntil.toISOString(), newBalance, userId);

  res.json({ ok: true, premiumUntil: newPremiumUntil.toISOString() });
});

export default router;
