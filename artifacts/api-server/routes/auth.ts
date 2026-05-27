import { Router } from "express";
import type { Request, Response } from "express";
import { validateTelegramInitData } from "../lib/telegram.js";
import { signToken } from "../middlewares/auth.js";
import { getDb, dbExists } from "../lib/sqlite.js";

const router = Router();

function buildUserProfile(row: Record<string, unknown>) {
  const isPremium = Boolean(row["is_premium"]);
  let premiumUntil: string | null = null;
  if (row["premium_until"]) {
    premiumUntil = String(row["premium_until"]);
  }
  return {
    tgId: Number(row["tg_id"]),
    username: (row["username"] as string | null) ?? null,
    fullName: String(row["full_name"] ?? ""),
    lang: String(row["lang"] ?? "uz"),
    isPremium,
    premiumUntil,
    balance: Number(row["balance"] ?? 0),
    photoUrl: (row["photo_url"] as string | null) ?? null,
  };
}

router.post("/auth/telegram", async (req: Request, res: Response) => {
  const { initData } = req.body as { initData?: string };

  if (!initData) {
    res.status(400).json({ error: "initData required" });
    return;
  }

  let tgId: number | null = null;
  let firstName = "User";
  let lastName = "";
  let username: string | null = null;

  const isDev = process.env["NODE_ENV"] !== "production";

  if (initData === "test") {
    if (!isDev) {
      res.status(401).json({ error: "Test mode not allowed in production" });
      return;
    }
    tgId = 999999999;
    firstName = "Test";
    lastName = "User";
    username = "testuser";
  } else {
    const botToken = process.env["BOT_TOKEN"];
    if (!botToken) {
      res.status(503).json({ error: "BOT_TOKEN not configured on the server" });
      return;
    }

    const parsed = validateTelegramInitData(initData, botToken);
    if (!parsed) {
      res.status(401).json({ error: "Invalid Telegram initData" });
      return;
    }

    try {
      const userData = JSON.parse(parsed["user"] ?? "{}") as Record<string, unknown>;
      tgId = Number(userData["id"]);
      firstName = String(userData["first_name"] ?? "User");
      lastName = String(userData["last_name"] ?? "");
      username = (userData["username"] as string | null) ?? null;
    } catch {
      res.status(400).json({ error: "Failed to parse user data" });
      return;
    }
  }

  if (!tgId || isNaN(tgId)) {
    res.status(400).json({ error: "Could not determine Telegram user ID" });
    return;
  }

  if (!dbExists()) {
    res.status(503).json({
      error: "Database not ready — please start the Telegram bot first to initialise the database",
    });
    return;
  }

  const db = getDb();
  const fullName = [firstName, lastName].filter(Boolean).join(" ");

  let user = db.prepare("SELECT * FROM users WHERE tg_id = ?").get(tgId) as
    | Record<string, unknown>
    | undefined;

  if (!user) {
    db.prepare(
      `INSERT OR IGNORE INTO users (tg_id, username, full_name, lang, is_premium, balance, created_at)
       VALUES (?, ?, ?, 'uz', 0, 0, datetime('now'))`,
    ).run(tgId, username, fullName);

    user = db.prepare("SELECT * FROM users WHERE tg_id = ?").get(tgId) as
      | Record<string, unknown>
      | undefined;
  } else {
    db.prepare(`UPDATE users SET username = ?, full_name = ? WHERE tg_id = ?`).run(username, fullName, tgId);
    user["username"] = username;
    user["full_name"] = fullName;
  }

  if (!user) {
    res.status(500).json({ error: "Failed to create user" });
    return;
  }

  const userId = Number(user["id"]);
  const token = signToken(userId);

  res.json({ token, user: buildUserProfile(user) });
});

router.post("/auth/register-phone", (req: Request, res: Response) => {
  const { phone, tg_id } = req.body as { phone?: string; tg_id?: number };

  if (!phone || !tg_id) {
    res.status(400).json({ error: "phone and tg_id required" });
    return;
  }

  if (!dbExists()) {
    res.status(503).json({ error: "Database not ready" });
    return;
  }

  const db = getDb();
  db.prepare(`UPDATE users SET phone = ? WHERE tg_id = ?`).run(phone, tg_id);

  res.json({ ok: true });
});

export default router;
