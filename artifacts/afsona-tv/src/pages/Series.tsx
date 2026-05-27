import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@/contexts/AuthContext";
import { apiFetch } from "@/lib/api";
import { MovieCard } from "@/components/MovieCard";
import { useState } from "react";

type SeriesSummary = {
  id: number;
  titleUz: string;
  titleRu: string | null;
  posterUrl: string | null;
  year: number | null;
  isPremium: boolean;
  genres: string | null;
};

type SeriesListResponse = {
  series: SeriesSummary[];
  hasMore: boolean;
  total: number;
};

export function SeriesPage() {
  const { token } = useAuth();
  const [page, setPage] = useState(0);
  const [genre, setGenre] = useState("");

  const { data, isLoading } = useQuery<SeriesListResponse>({
    queryKey: ["series", page, genre],
    queryFn: () =>
      apiFetch(`/series?page=${page}&limit=18${genre ? `&genre=${encodeURIComponent(genre)}` : ""}`, token!),
    enabled: !!token,
  });

  const { data: genres } = useQuery<{ name: string; count: number }[]>({
    queryKey: ["genres"],
    queryFn: () => apiFetch("/genres", token!),
    enabled: !!token,
  });

  return (
    <div className="pb-24">
      <div className="sticky top-0 bg-background/95 backdrop-blur z-10 px-4 py-3 border-b border-border">
        <h1 className="text-base font-bold text-foreground mb-2">📺 Seriallar</h1>
        <div className="flex gap-2 overflow-x-auto scrollbar-hide">
          <button
            onClick={() => { setGenre(""); setPage(0); }}
            className={`flex-none text-xs px-3 py-1.5 rounded-full font-medium transition-colors ${
              !genre ? "bg-primary text-primary-foreground" : "bg-secondary text-secondary-foreground"
            }`}
          >
            Barchasi
          </button>
          {genres?.slice(0, 10).map((g) => (
            <button
              key={g.name}
              onClick={() => { setGenre(g.name); setPage(0); }}
              className={`flex-none text-xs px-3 py-1.5 rounded-full font-medium transition-colors ${
                genre === g.name ? "bg-primary text-primary-foreground" : "bg-secondary text-secondary-foreground"
              }`}
            >
              {g.name}
            </button>
          ))}
        </div>
      </div>

      {isLoading ? (
        <div className="flex justify-center mt-8">
          <p className="text-sm text-muted-foreground animate-pulse">Yuklanmoqda...</p>
        </div>
      ) : (
        <>
          {data?.total !== undefined && (
            <p className="text-xs text-muted-foreground px-4 mt-3 mb-1">
              Jami: {data.total} ta serial
            </p>
          )}
          <div className="grid grid-cols-3 gap-3 px-4 mt-2">
            {data?.series.map((s) => (
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

          {data?.series.length === 0 && (
            <div className="flex flex-col items-center mt-16 gap-2">
              <p className="text-3xl">📭</p>
              <p className="text-sm text-muted-foreground">Serial topilmadi</p>
            </div>
          )}

          <div className="flex justify-center gap-3 mt-6 px-4">
            <button
              disabled={page === 0}
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              className="text-xs px-4 py-2 rounded-full bg-secondary text-secondary-foreground disabled:opacity-40"
            >
              ← Oldingi
            </button>
            <span className="text-xs text-muted-foreground py-2">{page + 1}</span>
            <button
              disabled={!data?.hasMore}
              onClick={() => setPage((p) => p + 1)}
              className="text-xs px-4 py-2 rounded-full bg-secondary text-secondary-foreground disabled:opacity-40"
            >
              Keyingi →
            </button>
          </div>
        </>
      )}
    </div>
  );
}
