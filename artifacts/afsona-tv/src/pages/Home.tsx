import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@/contexts/AuthContext";
import { apiFetch } from "@/lib/api";
import { MovieCard } from "@/components/MovieCard";
import { useLocation } from "wouter";

type MovieSummary = {
  id: number;
  title: string;
  posterUrl: string | null;
  year: number | null;
  rating: number;
  isPremium: boolean;
  isSeries: boolean;
};

type SeriesSummary = {
  id: number;
  titleUz: string;
  titleRu: string | null;
  posterUrl: string | null;
  year: number | null;
  isPremium: boolean;
  genres: string | null;
};

type FeaturedContent = {
  trending: MovieSummary[];
  recent: MovieSummary[];
  newSeries: SeriesSummary[];
};

type HomeStats = {
  totalMovies: number;
  totalSeries: number;
  newThisWeek: number;
};

function HorizontalSection({
  title,
  emoji,
  children,
}: {
  title: string;
  emoji: string;
  children: React.ReactNode;
}) {
  return (
    <section className="mt-5">
      <h2 className="text-sm font-semibold text-foreground px-4 mb-3">
        {emoji} {title}
      </h2>
      <div className="flex gap-3 overflow-x-auto scrollbar-hide px-4 pb-2">
        {children}
      </div>
    </section>
  );
}

export function HomePage() {
  const { token, user } = useAuth();
  const [, navigate] = useLocation();

  const { data: featured, isLoading } = useQuery<FeaturedContent>({
    queryKey: ["featured"],
    queryFn: () => apiFetch("/movies/featured", token!),
    enabled: !!token,
  });

  const { data: stats } = useQuery<HomeStats>({
    queryKey: ["homeStats"],
    queryFn: () => apiFetch("/home/stats", token!),
    enabled: !!token,
  });

  return (
    <div className="pb-24">
      <div className="bg-card px-4 pt-5 pb-4 border-b border-border">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-lg font-bold text-foreground">🎬 Afsona TV</h1>
            <p className="text-xs text-muted-foreground mt-0.5">
              Salom, {user?.fullName ?? "mehmon"}!
            </p>
          </div>
          {user?.isPremium && (
            <span className="bg-yellow-500/20 text-yellow-400 text-xs font-bold px-2 py-1 rounded-full">
              ⭐ VIP
            </span>
          )}
        </div>

        {stats && (
          <div className="grid grid-cols-3 gap-2 mt-4">
            {[
              { label: "Filmlar", value: stats.totalMovies },
              { label: "Seriallar", value: stats.totalSeries },
              { label: "Yangi", value: stats.newThisWeek },
            ].map((s) => (
              <div key={s.label} className="bg-background rounded-xl p-2.5 text-center">
                <p className="text-base font-bold text-primary">{s.value}</p>
                <p className="text-[10px] text-muted-foreground">{s.label}</p>
              </div>
            ))}
          </div>
        )}
      </div>

      {isLoading ? (
        <div className="flex justify-center mt-8">
          <div className="animate-pulse text-muted-foreground text-sm">Yuklanmoqda...</div>
        </div>
      ) : (
        <>
          {(featured?.trending?.length ?? 0) > 0 && (
            <HorizontalSection title="Mashhur Filmlar" emoji="🔥">
              {featured!.trending.map((m) => (
                <div key={m.id} className="flex-none w-28">
                  <MovieCard {...m} />
                </div>
              ))}
            </HorizontalSection>
          )}

          {(featured?.newSeries?.length ?? 0) > 0 && (
            <HorizontalSection title="Yangi Seriallar" emoji="📺">
              {featured!.newSeries.map((s) => (
                <div key={s.id} className="flex-none w-28">
                  <MovieCard
                    id={s.id}
                    title={s.titleUz}
                    posterUrl={s.posterUrl}
                    year={s.year}
                    isPremium={s.isPremium}
                    isSeries={true}
                  />
                </div>
              ))}
            </HorizontalSection>
          )}

          {(featured?.recent?.length ?? 0) > 0 && (
            <HorizontalSection title="Yangi Filmlar" emoji="🆕">
              {featured!.recent.map((m) => (
                <div key={m.id} className="flex-none w-28">
                  <MovieCard {...m} />
                </div>
              ))}
            </HorizontalSection>
          )}

          {!featured?.trending?.length &&
            !featured?.newSeries?.length &&
            !featured?.recent?.length && (
              <div className="flex flex-col items-center justify-center mt-16 gap-4 px-8 text-center">
                <p className="text-5xl">📭</p>
                <p className="text-foreground font-semibold">Ma'lumot yo'q</p>
                <p className="text-sm text-muted-foreground">
                  Bot ishga tushirilgandan so'ng filmlar bu yerda ko'rinadi
                </p>
                <button
                  onClick={() => navigate("/movies")}
                  className="mt-2 bg-primary text-primary-foreground text-sm font-medium px-5 py-2.5 rounded-full"
                >
                  Filmlarni ko'rish
                </button>
              </div>
            )}
        </>
      )}
    </div>
  );
}
