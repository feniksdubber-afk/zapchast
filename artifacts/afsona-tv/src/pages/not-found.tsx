import { useLocation } from "wouter";

export default function NotFound() {
  const [, navigate] = useLocation();

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-background gap-4 text-center px-6">
      <p className="text-6xl">🎬</p>
      <h1 className="text-xl font-bold text-foreground">404 - Sahifa topilmadi</h1>
      <p className="text-sm text-muted-foreground">Siz izlayotgan sahifa mavjud emas</p>
      <button
        onClick={() => navigate("/")}
        className="mt-2 bg-primary text-primary-foreground text-sm font-medium px-5 py-2.5 rounded-full"
      >
        Bosh sahifaga qaytish
      </button>
    </div>
  );
}
