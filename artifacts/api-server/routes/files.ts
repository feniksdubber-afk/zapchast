import { Router } from "express";
import type { Request, Response } from "express";
import { getTelegramFileUrl } from "../lib/telegram.js";

const router = Router();

router.get("/files/:fileId", async (req: Request, res: Response) => {
  const { fileId } = req.params;

  if (!fileId) {
    res.status(400).json({ error: "fileId required" });
    return;
  }

  const decodedFileId = decodeURIComponent(fileId);
  const url = await getTelegramFileUrl(decodedFileId);

  if (!url) {
    res.status(404).json({ error: "Could not resolve file URL" });
    return;
  }

  res.redirect(302, url);
});

export default router;
