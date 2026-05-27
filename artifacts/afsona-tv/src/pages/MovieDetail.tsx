import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRoute, useLocation } from "wouter";
import { useAuth } from "@/contexts/AuthContext";
import { apiFetch } from "@/lib/api";
import { useState } from "react";

type MovieDetail = {
  id: number;
  title: string;
  posterUrl: string | null;
  year: number | null;
  rating: number;
  isPremium: boolean;
  country: string | null;
  genres: string | null;
  description: string | null;
  views: number;
};

type FavoriteItem = { id: number; movieId: number | null; seriesId: number | null };

export function MovieDetailPage() {
  const [match, params] = useRoute("/movies/:id");
  const [, navigate] = useLocation();
  const { token } = useAuth();
  const queryClient = useQueryClient();
  const [streamUrl, setStreamUrl] = useState<string | null>(null);
  const [streamError, setStreamError] = useState<string | null>(null);

  const id = match ? Number(params?.id) : null;

  const { data: movie, isLoading } = useQuery<MovieDetail>({
    queryKey: ["movie", id],
    queryFn: () => apiFetch(`/movies/${id}`, token!),
    enabled: !!token && !!id,
  });

  const { data: favorites } = useQuery<FavoriteItem[]>({
    queryKey: ["favorites"],
    queryFn: () => apiFetch("/favorites", token!),
    enabled: !!token,
  });

  const favMutation = useMutation({
    mutationFn: () =>
      apiFetch<{ favorited: boolean }>("/favorites", token!, {
        method: "POST",
        body: JSON.stringify({ movieId: id }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["favorites"] });
    },
  });

  const historyMutation = useMutation({
    mutationFn: () =>
      apiFetch("/watch-history", token!, {
        method: "POST",
        body: JSON.stringify({ movieId: id }),
      }),
  });

  const isFavorited = favorites?.some((f) => f.movieId === id) ?? false;

  async function handleWatch() {
    setStreamError(null);
    try {
      const data = await apiFetch<{ url: string }>(`/movies/${id}/stream-url`, token!);
      setStreamUrl(data.url);
      historyMutation.mutate();
    } catch (err) {
      setStreamError(err instanceof Error ? err.message : "Xato yuz berdi");
    }
  }

  if (!match) return null;

  if (isLoading) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <p className="text-sm text-muted-foreground animate-pulse">Yuklanmoqda...</p>
      </div>
    );
  }

  if (!movie) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen gap-3">
        <p className="text-3xl">😢</p>
        <p className="text-sm text-muted-foreground">Film topilmadi</p>
        <button onClick={() => navigate("/movies")} className="text-primary text-sm">← Orqaga</button>
      </div>
    );
  }

  return (
    <div className="pb-24">
      <div className="relative w-full aspect-[16/9] bg-muted">
        {streamUrl ? (
          <video
            src={streamUrl}
            controls
            autoPlay
            className="w-full h-full object-contain bg-black"
          />
        ) : movie.posterUrl ? (
          <img src={movie.posterUrl} alt={movie.title} className="w-full h-full object-cover" />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-6xl">🎬</div>
        )}

        <button
          onClick={() => navigate("/movies")}
          className="absolute top-3 left-3 bg-black/60 text-white text-xs px-3 py-1.5 rounded-full"
        >
          ← Orqaga
        </button>
      </div>

      <div className="px-4 mt-4">
        <div className="flex items-start justify-between gap-2">
          <h1 className="text-lg font-bold text-foreground flex-1">{movie.title}</h1>
          <button
            onClick={() => favMutation.mutate()}
            className={`text-2xl transition-transform active:scale-90 ${isFavorited ? "text-red-400" : "text-muted-foreground"}`}
          >
            {isFavorited ? "❤️" : "🤍"}
          </button>
        </div>

        <div className="flex flex-wrap gap-2 mt-2">
          {movie.year && (
            <span className="bg-secondary text-secondary-foreground text-xs px-2 py-0.5 rounded">
              {movie.year}
            </span>
          )}
          {movie.country && (
            <span className="bg-secondary text-secondary-foreground text-xs px-2 py-0.5 rounded">
              {movie.country}
            </span>
          )}
          {movie.rating > 0 && (
            <span className="bg-yellow-500/20 text-yellow-400 text-xs px-2 py-0.5 rounded">
              ⭐ {movie.rating.toFixed(1)}
            </span>
          )}
          {movie.isPremium && (
            <span className="bg-yellow-500 text-black text-xs font-bold px-2 py-0.5 rounded">
              VIP
            </span>
          )}
        </div>

        {movie.genres && (
          <p className="text-xs text-muted-foreground mt-2">{movie.genres}</p>
        )}

        {movie.description && (
          <p className="text-sm text-foreground/80 mt-3 leading-relaxed">{movie.description}</p>
        )}

        <p className="text-xs text-muted-foreground mt-2">👁 {movie.views.toLocaleString()} marta ko'rilgan</p>

        {streamError && (
          <div className="mt-3 bg-destructive/10 text-destructive text-xs px-3 py-2 rounded-lg">
            {streamError}
            {streamError.includes("Premium") && (
              <button
                onClick={() => navigate("/tariffs")}
                className="block mt-1 text-primary font-medium"
              >
                Premium olish →
              </button>
            )}
          </div>
        )}

        {!streamUrl && (
          <button
            onClick={handleWatch}
            className="w-full mt-4 bg-primary text-primary-foreground font-bold py-3 rounded-xl text-sm flex items-center justify-center gap-2"
          >
            ▶ Ko'rish
          </button>
        )}
      </div>
    </div>
  );
}
