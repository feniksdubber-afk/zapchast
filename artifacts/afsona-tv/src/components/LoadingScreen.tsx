export function LoadingScreen() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-background gap-4">
      <div className="text-5xl animate-bounce">🎬</div>
      <p className="text-muted-foreground text-sm animate-pulse">Yuklanmoqda...</p>
    </div>
  );
}
