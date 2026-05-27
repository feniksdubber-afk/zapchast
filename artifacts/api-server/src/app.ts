import express, { type Express, type Request, type Response } from "express";
import cors from "cors";
import pinoHttp from "pino-http";
import path from "node:path";
import fs from "node:fs";
import { fileURLToPath } from "node:url";
import router from "./routes/index.js";
import { logger } from "./lib/logger.js";

const app: Express = express();

app.use(
  pinoHttp({
    logger,
    serializers: {
      req(req) {
        return {
          id: req.id,
          method: req.method,
          url: req.url?.split("?")[0],
        };
      },
      res(res) {
        return {
          statusCode: res.statusCode,
        };
      },
    },
  }),
);
app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

app.use("/api", router);

const isProd = process.env["NODE_ENV"] === "production";
if (isProd) {
  const __dirname = path.dirname(fileURLToPath(import.meta.url));
  const staticDir = path.join(__dirname, "public");

  if (fs.existsSync(staticDir)) {
    app.use(express.static(staticDir));

    app.get("/{*path}", (_req: Request, res: Response) => {
      res.sendFile(path.join(staticDir, "index.html"));
    });

    logger.info({ staticDir }, "Serving static frontend files");
  } else {
    logger.warn({ staticDir }, "Static frontend directory not found — serving API only");
  }
}

export default app;
