import { Router } from "express";
import type { Response } from "express";
import { authMiddleware, type AuthRequest } from "../middlewares/auth.js";
import { getDb, dbExists } from "../lib/sqlite.js";
import { makePosterUrl, getTelegramFileUrl } from "../lib/telegram.js";

const router = Router();

type SeriesRow = {
  id: number;
  title_uz: string | null;
  title_ru: string | null;
  year: number | null;
  genres: string | null;
  description: string | null;
  poster_file_id: string | null;
  is_premium: number;
};

type EpisodeRow = {
  id: number;
  series_id: number;
  season_number: number;
  episode_number: number;
  video_file_id: string | null;
};

function toSeriesSummary(row: SeriesRow) {
  return {
    id: row.id,
    titleUz: row.title_uz ?? row.title_ru ?? "—",
    titleRu: row.title_ru ?? null,
    posterUrl: makePosterUrl(row.poster_file_id),
    year: row.year ?? null,
    isPremium: Boolean(row.is_premium),
    genres: row.genres ?? null,
  };
}

router.get("/series", authMiddleware, (req: AuthRequest, res: Response) => {
  if (!dbExists()) {
    res.json({ series: [], hasMore: false, total: 0 });
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
    db.prepare(`SELECT COUNT(*) as cnt FROM series ${where}`).get(...params) as { cnt: number }
  ).cnt;

  const rows = db
    .prepare(`SELECT * FROM series ${where} ORDER BY id DESC LIMIT ? OFFSET ?`)
    .all(...params, limit + 1, page * limit) as SeriesRow[];

  const hasMore = rows.length > limit;
  if (hasMore) rows.pop();

  res.json({ series: rows.map(toSeriesSummary), hasMore, total });
});

router.get("/series/:id", authMiddleware, (req: AuthRequest, res: Response) => {
  if (!dbExists()) {
    res.status(404).json({ error: "Not found" });
    return;
  }

  const db = getDb();
  const id = Number(req.params["id"]);

  const row = db.prepare("SELECT * FROM series WHERE id = ?").get(id) as SeriesRow | undefined;

  if (!row) {
    res.status(404).json({ error: "Serial topilmadi" });
    return;
  }

  const seasonRows = db
    .prepare("SELECT DISTINCT season_number FROM episodes WHERE series_id = ? ORDER BY season_number")
    .all(id) as { season_number: number }[];

  const seasons = seasonRows.map(({ season_number }) => {
    const episodes = (
      db
        .prepare(
          "SELECT id, season_number, episode_number FROM episodes WHERE series_id = ? AND season_number = ? ORDER BY episode_number",
        )
        .all(id, season_number) as EpisodeRow[]
    ).map((ep) => ({
      id: ep.id,
      seasonNumber: ep.season_number,
      episodeNumber: ep.episode_number,
    }));

    return { seasonNumber: season_number, episodes };
  });

  res.json({
    id: row.id,
    titleUz: row.title_uz ?? row.title_ru ?? "—",
    titleRu: row.title_ru ?? null,
    posterUrl: makePosterUrl(row.poster_file_id),
    year: row.year ?? null,
    isPremium: Boolean(row.is_premium),
    genres: row.genres ?? null,
    description: row.description ?? null,
    seasons,
  });
});

router.get("/episodes/:id/stream-url", authMiddleware, async (req: AuthRequest, res: Response) => {
  if (!dbExists()) {
    res.status(404).json({ error: "Not found" });
    return;
  }

  const db = getDb();
  const episodeId = Number(req.params["id"]);

  const episode = db.prepare("SELECT * FROM episodes WHERE id = ?").get(episodeId) as
    | EpisodeRow
    | undefined;

  if (!episode) {
    res.status(404).json({ error: "Qism topilmadi" });
    return;
  }

  const series = db.prepare("SELECT * FROM series WHERE id = ?").get(episode.series_id) as
    | SeriesRow
    | undefined;

  if (series?.is_premium) {
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

  const fileId = episode.video_file_id;

  if (!fileId) {
    res.status(404).json({ error: "Bu qism uchun video topilmadi" });
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
