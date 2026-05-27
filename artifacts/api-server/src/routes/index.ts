import { Router, type IRouter } from "express";
import healthRouter from "./health.js";
import authRouter from "./auth.js";
import homeRouter from "./home.js";
import genresRouter from "./genres.js";
import moviesRouter from "./movies.js";
import seriesRouter from "./series.js";
import favoritesRouter from "./favorites.js";
import historyRouter from "./history.js";
import profileRouter from "./profile.js";
import tariffsRouter from "./tariffs.js";
import paymentsRouter from "./payments.js";
import searchRouter from "./search.js";
import filesRouter from "./files.js";

const router: IRouter = Router();

router.use(healthRouter);
router.use(authRouter);
router.use(homeRouter);
router.use(genresRouter);
router.use(moviesRouter);
router.use(seriesRouter);
router.use(favoritesRouter);
router.use(historyRouter);
router.use(profileRouter);
router.use(tariffsRouter);
router.use(paymentsRouter);
router.use(searchRouter);
router.use(filesRouter);

export default router;
