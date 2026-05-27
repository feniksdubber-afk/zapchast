import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@/contexts/AuthContext";
import { apiFetch } from "@/lib/api";
import { MovieCard } from "@/components/MovieCard";
import { useState, useCallback } from "react";

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
  posterUrl: string | null;
  year: number | null;
  isPremium: boolean;
};

type SearchResponse = {
  movies: MovieSummary[];
  series: SeriesSummary[];
};

export function SearchPage() {
  const { token } = useAuth();
  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [timer, setTimer] = useState<ReturnType<typeof setTimeout> | null>(null);

  const handleChange = useCallback((val: string) => {
    setQuery(val);
    if (timer) clearTimeout(timer);
    const t = setTimeout(() => setDebouncedQuery(val), 400);
    setTimer(t);
  }, [timer]);

  const { data, isLoading } = useQuery<SearchResponse>({
    queryKey: ["search", debouncedQuery],
    queryFn: () => apiFetch(`/search?q=${encodeURIComponent(debouncedQuery)}`, token!),
    enabled: !!token && debouncedQuery.length >= 2,
  });

  const hasResults = (data?.movies.length ?? 0) + (data?.series.length ?? 0) > 0;

  return (
    <div className="pb-24">
      <div className="sticky top-0 z-10 bg-background/95 backdrop-blur px-4 pt-4 pb-3 border-b border-border">
        <h1 className="text-base font-bold text-foreground mb-2">🔍 Qidiruv</h1>
        <input
          value={query}
          onChange={(e) => handleChange(e.target.value)}
          placeholder="Film yoki serial nomini kiriting..."
          className="w-full bg-secondary text-foreground placeholder:text-muted-foreground text-sm px-4 py-2.5 rounded-full focus:ring-2 ring-primary"
        />
      </div>

      <div className="px-4 mt-4">
        {debouncedQuery.length < 2 && (
          <div className="flex flex-col items-center mt-12 gap-2 text-center">
            <p className="text-4xl">🔎</p>
            <p className="text-sm text-muted-foreground">
              Kamida 2 ta harf kiriting
            </p>
          </div>
        )}

        {debouncedQuery.length >= 2 && isLoading && (
          <p className="text-sm text-muted-foreground text-center mt-8 animate-pulse">
            Qidirilmoqda...
          </p>
        )}

        {debouncedQuery.length >= 2 && !isLoading && !hasResults && (
          <div className="flex flex-col items-center mt-12 gap-2">
            <p className="text-4xl">😔</p>
            <p className="text-sm text-muted-foreground">Natija topilmadi</p>
          </div>
        )}

        {(data?.movies.length ?? 0) > 0 && (
          <section className="mb-5">
            <h2 className="text-sm font-semibold text-foreground mb-3">
              🎬 Filmlar ({data!.movies.length})
            </h2>
            <div className="grid grid-cols-3 gap-3">
              {data!.movies.map((m) => (
                <MovieCard key={m.id} {...m} />
              ))}
            </div>
          </section>
        )}

        {(data?.series.length ?? 0) > 0 && (
          <section>
            <h2 className="text-sm font-semibold text-foreground mb-3">
              📺 Seriallar ({data!.series.length})
            </h2>
            <div className="grid grid-cols-3 gap-3">
              {data!.series.map((s) => (
                <MovieCard
                  key={s.id}
                  id={s.id}
                  title={s.titleUz}
                  posterUrl={s.posterUrl}
                  year={s.year}
                  isPremium={s.isPremium}
                  isSeries={true}
                />
              ))}
            </div>
          </section>
        )}
      </div>
    </div>
  );
}
