import { useLocation } from "wouter";

type Props = {
  id: number;
  title: string;
  posterUrl?: string | null;
  year?: number | null;
  rating?: number;
  isPremium?: boolean;
  isSeries?: boolean;
};

export function MovieCard({
  id,
  title,
  posterUrl,
  year,
  rating,
  isPremium,
  isSeries,
}: Props) {
  const [, navigate] = useLocation();

  function handleClick() {
    navigate(isSeries ? `/series/${id}` : `/movies/${id}`);
  }

  return (
    <button
      onClick={handleClick}
      className="flex flex-col gap-1 text-left w-full group"
    >
      <div className="relative w-full aspect-[2/3] rounded-lg overflow-hidden bg-muted">
        {posterUrl ? (
          <img
            src={posterUrl}
            alt={title}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
            loading="lazy"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-4xl text-muted-foreground">
            {isSeries ? "📺" : "🎬"}
          </div>
        )}

        {isPremium && (
          <span className="absolute top-1.5 right-1.5 bg-yellow-500 text-black text-[10px] font-bold px-1.5 py-0.5 rounded">
            VIP
          </span>
        )}
      </div>

      <div className="px-0.5">
        <p className="text-xs font-medium text-foreground truncate">{title}</p>
        <div className="flex items-center gap-1 mt-0.5">
          {year && <span className="text-[10px] text-muted-foreground">{year}</span>}
          {rating !== undefined && rating > 0 && (
            <span className="text-[10px] text-yellow-400 ml-auto">⭐ {rating.toFixed(1)}</span>
          )}
        </div>
      </div>
    </button>
  );
}
