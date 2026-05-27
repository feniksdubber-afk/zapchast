import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/contexts/AuthContext";
import { apiFetch } from "@/lib/api";
import { MovieCard } from "@/components/MovieCard";

type FavoriteItem = {
  id: number;
  movieId: number | null;
  seriesId: number | null;
  title: string;
  posterUrl: string | null;
  isPremium: boolean;
  type: string;
};

export function FavoritesPage() {
  const { token } = useAuth();
  const queryClient = useQueryClient();

  const { data: favorites, isLoading } = useQuery<FavoriteItem[]>({
    queryKey: ["favorites"],
    queryFn: () => apiFetch("/favorites", token!),
    enabled: !!token,
  });

  const removeMutation = useMutation({
    mutationFn: (item: FavoriteItem) =>
      apiFetch<{ favorited: boolean }>("/favorites", token!, {
        method: "POST",
        body: JSON.stringify({ movieId: item.movieId, seriesId: item.seriesId }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["favorites"] });
    },
  });

  return (
    <div className="pb-24">
      <div className="sticky top-0 bg-background/95 backdrop-blur z-10 px-4 py-3 border-b border-border">
        <h1 className="text-base font-bold text-foreground">❤️ Sevimlilar</h1>
      </div>

      <div className="px-4 mt-4">
        {isLoading ? (
          <p className="text-sm text-muted-foreground text-center mt-8 animate-pulse">Yuklanmoqda...</p>
        ) : !favorites?.length ? (
          <div className="flex flex-col items-center mt-16 gap-3 text-center">
            <p className="text-5xl">💔</p>
            <p className="text-foreground font-medium">Sevimlilar bo'sh</p>
            <p className="text-sm text-muted-foreground">Film yoki serial sahifasida ❤️ ni bosing</p>
          </div>
        ) : (
          <div className="grid grid-cols-3 gap-3">
            {favorites.map((fav) => (
              <div key={fav.id} className="relative">
                <MovieCard
                  id={(fav.movieId ?? fav.seriesId)!}
                  title={fav.title}
                  posterUrl={fav.posterUrl}
                  isPremium={fav.isPremium}
                  isSeries={fav.type === "series"}
                />
                <button
                  onClick={() => removeMutation.mutate(fav)}
                  className="absolute top-1.5 left-1.5 bg-black/60 text-white text-xs w-6 h-6 rounded-full flex items-center justify-center"
                >
                  ✕
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
