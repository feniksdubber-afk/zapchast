import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRoute, useLocation } from "wouter";
import { useAuth } from "@/contexts/AuthContext";
import { apiFetch } from "@/lib/api";
import { useState } from "react";

type Episode = { id: number; seasonNumber: number; episodeNumber: number };
type Season = { seasonNumber: number; episodes: Episode[] };
type SeriesDetail = {
  id: number;
  titleUz: string;
  titleRu: string | null;
  posterUrl: string | null;
  year: number | null;
  isPremium: boolean;
  genres: string | null;
  description: string | null;
  seasons: Season[];
};

type FavoriteItem = { id: number; movieId: number | null; seriesId: number | null };

export function SeriesDetailPage() {
  const [match, params] = useRoute("/series/:id");
  const [, navigate] = useLocation();
  const { token } = useAuth();
  const queryClient = useQueryClient();
  const [activeSeason, setActiveSeason] = useState(0);
  const [streamUrl, setStreamUrl] = useState<string | null>(null);
  const [streamError, setStreamError] = useState<string | null>(null);
  const [playingEp, setPlayingEp] = useState<Episode | null>(null);

  const id = match ? Number(params?.id) : null;

  const { data: series, isLoading } = useQuery<SeriesDetail>({
    queryKey: ["series", id],
    queryFn: () => apiFetch(`/series/${id}`, token!),
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
        body: JSON.stringify({ seriesId: id }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["favorites"] });
    },
  });

  const historyMutation = useMutation({
    mutationFn: (ep: Episode) =>
      apiFetch("/watch-history", token!, {
        method: "POST",
        body: JSON.stringify({
          seriesId: id,
          seasonNumber: ep.seasonNumber,
          episodeNumber: ep.episodeNumber,
        }),
      }),
  });

  const isFavorited = favorites?.some((f) => f.seriesId === id) ?? false;

  async function handleWatchEpisode(ep: Episode) {
    setStreamError(null);
    setStreamUrl(null);
    setPlayingEp(ep);
    try {
      const data = await apiFetch<{ url: string }>(`/episodes/${ep.id}/stream-url`, token!);
      setStreamUrl(data.url);
      historyMutation.mutate(ep);
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

  if (!series) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen gap-3">
        <p className="text-3xl">😢</p>
        <p className="text-sm text-muted-foreground">Serial topilmadi</p>
        <button onClick={() => navigate("/series")} className="text-primary text-sm">← Orqaga</button>
      </div>
    );
  }

  const currentSeason = series.seasons[activeSeason];

  return (
    <div className="pb-24">
      <div className="relative w-full aspect-[16/9] bg-muted">
        {streamUrl ? (
          <video src={streamUrl} controls autoPlay className="w-full h-full object-contain bg-black" />
        ) : series.posterUrl ? (
          <img src={series.posterUrl} alt={series.titleUz} className="w-full h-full object-cover" />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-6xl">📺</div>
        )}
        <button
          onClick={() => navigate("/series")}
          className="absolute top-3 left-3 bg-black/60 text-white text-xs px-3 py-1.5 rounded-full"
        >
          ← Orqaga
        </button>
      </div>

      <div className="px-4 mt-4">
        <div className="flex items-start justify-between gap-2">
          <h1 className="text-lg font-bold text-foreground flex-1">{series.titleUz}</h1>
          <button
            onClick={() => favMutation.mutate()}
            className={`text-2xl transition-transform active:scale-90 ${isFavorited ? "text-red-400" : "text-muted-foreground"}`}
          >
            {isFavorited ? "❤️" : "🤍"}
          </button>
        </div>

        {series.titleRu && (
          <p className="text-xs text-muted-foreground">{series.titleRu}</p>
        )}

        <div className="flex flex-wrap gap-2 mt-2">
          {series.year && (
            <span className="bg-secondary text-secondary-foreground text-xs px-2 py-0.5 rounded">
              {series.year}
            </span>
          )}
          {series.isPremium && (
            <span className="bg-yellow-500 text-black text-xs font-bold px-2 py-0.5 rounded">VIP</span>
          )}
        </div>

        {series.description && (
          <p className="text-sm text-foreground/80 mt-3 leading-relaxed">{series.description}</p>
        )}

        {streamError && (
          <div className="mt-3 bg-destructive/10 text-destructive text-xs px-3 py-2 rounded-lg">
            {streamError}
            {streamError.includes("Premium") && (
              <button onClick={() => navigate("/tariffs")} className="block mt-1 text-primary font-medium">
                Premium olish →
              </button>
            )}
          </div>
        )}

        {series.seasons.length > 0 && (
          <div className="mt-4">
            <div className="flex gap-2 overflow-x-auto scrollbar-hide mb-3">
              {series.seasons.map((s, i) => (
                <button
                  key={s.seasonNumber}
                  onClick={() => setActiveSeason(i)}
                  className={`flex-none text-xs px-3 py-1.5 rounded-full font-medium ${
                    activeSeason === i
                      ? "bg-primary text-primary-foreground"
                      : "bg-secondary text-secondary-foreground"
                  }`}
                >
                  Mavsum {s.seasonNumber}
                </button>
              ))}
            </div>

            <div className="grid grid-cols-4 gap-2">
              {currentSeason?.episodes.map((ep) => {
                const isPlaying = playingEp?.id === ep.id;
                return (
                  <button
                    key={ep.id}
                    onClick={() => handleWatchEpisode(ep)}
                    className={`py-2.5 rounded-lg text-xs font-medium transition-colors ${
                      isPlaying
                        ? "bg-primary text-primary-foreground"
                        : "bg-secondary text-secondary-foreground hover:bg-primary/20"
                    }`}
                  >
                    {ep.episodeNumber}
                  </button>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
