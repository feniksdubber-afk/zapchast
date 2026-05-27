import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@/contexts/AuthContext";
import { apiFetch } from "@/lib/api";
import { useLocation } from "wouter";

type WatchHistoryItem = {
  id: number;
  title: string;
  type: string;
  seasonNumber: number | null;
  episodeNumber: number | null;
  watchedAt: string;
};

export function ProfilePage() {
  const { user, refetchProfile } = useAuth();
  const { token } = useAuth();
  const [, navigate] = useLocation();

  const { data: history } = useQuery<WatchHistoryItem[]>({
    queryKey: ["watchHistory"],
    queryFn: () => apiFetch("/watch-history", token!),
    enabled: !!token,
  });

  const isPremiumActive =
    user?.isPremium &&
    user?.premiumUntil &&
    new Date(user.premiumUntil) > new Date();

  return (
    <div className="pb-24">
      <div className="bg-card border-b border-border px-4 py-6">
        <div className="flex items-center gap-4">
          <div className="w-16 h-16 rounded-full bg-primary/20 flex items-center justify-center text-3xl">
            {user?.photoUrl ? (
              <img
                src={user.photoUrl}
                alt={user.fullName}
                className="w-full h-full object-cover rounded-full"
              />
            ) : (
              "👤"
            )}
          </div>
          <div className="flex-1">
            <h1 className="text-base font-bold text-foreground">{user?.fullName ?? "Foydalanuvchi"}</h1>
            {user?.username && (
              <p className="text-sm text-muted-foreground">@{user.username}</p>
            )}
            <p className="text-xs text-muted-foreground mt-0.5">ID: {user?.tgId}</p>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3 mt-4">
          <div className="bg-background rounded-xl p-3">
            <p className="text-xs text-muted-foreground">Balans</p>
            <p className="text-lg font-bold text-primary mt-0.5">{user?.balance ?? 0} 💎</p>
          </div>
          <div className={`rounded-xl p-3 ${isPremiumActive ? "bg-yellow-500/10" : "bg-background"}`}>
            <p className="text-xs text-muted-foreground">Premium</p>
            {isPremiumActive ? (
              <>
                <p className="text-sm font-bold text-yellow-400 mt-0.5">⭐ Faol</p>
                <p className="text-[10px] text-muted-foreground">
                  {new Date(user!.premiumUntil!).toLocaleDateString("uz-UZ")} gacha
                </p>
              </>
            ) : (
              <button
                onClick={() => navigate("/tariffs")}
                className="text-sm font-bold text-primary mt-0.5"
              >
                Sotib olish →
              </button>
            )}
          </div>
        </div>
      </div>

      <div className="px-4 mt-4">
        <h2 className="text-sm font-semibold text-foreground mb-3">🕐 Ko'rish tarixi</h2>
        {!history?.length ? (
          <div className="text-center py-6">
            <p className="text-3xl mb-2">📋</p>
            <p className="text-sm text-muted-foreground">Tarix bo'sh</p>
          </div>
        ) : (
          <div className="space-y-2">
            {history.slice(0, 20).map((item) => (
              <div key={item.id} className="bg-card rounded-xl px-3 py-2.5 flex items-center justify-between">
                <div>
                  <p className="text-xs font-medium text-foreground">{item.title}</p>
                  <p className="text-[10px] text-muted-foreground mt-0.5">
                    {item.type === "series" && item.seasonNumber
                      ? `S${item.seasonNumber} E${item.episodeNumber}`
                      : "Film"}
                    {" · "}
                    {new Date(item.watchedAt).toLocaleDateString("uz-UZ")}
                  </p>
                </div>
                <span className="text-base">{item.type === "series" ? "📺" : "🎬"}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
