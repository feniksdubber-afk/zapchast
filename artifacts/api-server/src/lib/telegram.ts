import crypto from "node:crypto";
import { logger } from "./logger.js";

const urlCache = new Map<string, { url: string; expires: number }>();
const CACHE_TTL_MS = 50 * 60 * 1000;

export function validateTelegramInitData(
  initData: string,
  botToken: string,
): Record<string, string> | null {
  try {
    const params = new URLSearchParams(initData);
    const hash = params.get("hash");
    if (!hash) return null;

    params.delete("hash");

    const dataCheckString = [...params.entries()]
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([k, v]) => `${k}=${v}`)
      .join("\n");

    const secretKey = crypto
      .createHmac("sha256", "WebAppData")
      .update(botToken)
      .digest();

    const expectedHash = crypto
      .createHmac("sha256", secretKey)
      .update(dataCheckString)
      .digest("hex");

    if (expectedHash !== hash) return null;

    const result: Record<string, string> = {};
    for (const [k, v] of params.entries()) {
      result[k] = v;
    }
    return result;
  } catch (err) {
    logger.error({ err }, "Error validating Telegram initData");
    return null;
  }
}

export async function getTelegramFileUrl(
  fileId: string,
): Promise<string | null> {
  const cached = urlCache.get(fileId);
  if (cached && cached.expires > Date.now()) return cached.url;

  const botToken = process.env["BOT_TOKEN"];
  if (!botToken) {
    logger.warn("BOT_TOKEN not set — cannot resolve Telegram file URLs");
    return null;
  }

  try {
    const res = await fetch(
      `https://api.telegram.org/bot${botToken}/getFile?file_id=${encodeURIComponent(fileId)}`,
    );
    const data = (await res.json()) as {
      ok: boolean;
      result?: { file_path?: string };
    };

    if (!data.ok || !data.result?.file_path) return null;

    const url = `https://api.telegram.org/file/bot${botToken}/${data.result.file_path}`;
    urlCache.set(fileId, { url, expires: Date.now() + CACHE_TTL_MS });
    return url;
  } catch (err) {
    logger.error({ err, fileId }, "Failed to get Telegram file URL");
    return null;
  }
}

export function makePosterUrl(
  fileId: string | null | undefined,
): string | null {
  if (!fileId) return null;
  return `/api/files/${encodeURIComponent(fileId)}`;
}
