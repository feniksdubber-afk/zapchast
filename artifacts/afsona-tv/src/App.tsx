import { Switch, Route, Router as WouterRouter } from "wouter";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider, useAuth } from "@/contexts/AuthContext";
import { BottomNav } from "@/components/BottomNav";
import { LoadingScreen } from "@/components/LoadingScreen";
import { HomePage } from "@/pages/Home";
import { MoviesPage } from "@/pages/Movies";
import { SeriesPage } from "@/pages/Series";
import { MovieDetailPage } from "@/pages/MovieDetail";
import { SeriesDetailPage } from "@/pages/SeriesDetail";
import { SearchPage } from "@/pages/Search";
import { FavoritesPage } from "@/pages/Favorites";
import { ProfilePage } from "@/pages/Profile";
import { TariffsPage } from "@/pages/Tariffs";
import NotFound from "@/pages/not-found";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 60_000,
    },
  },
});

function AppRoutes() {
  const { isLoading, error, token } = useAuth();

  if (isLoading) return <LoadingScreen />;

  if (error || !token) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-background gap-4 px-6">
        <p className="text-5xl">🔐</p>
        <h1 className="text-xl font-bold text-foreground text-center">Kirish kerak</h1>
        <p className="text-sm text-muted-foreground text-center">
          {error ?? "Iltimos, Telegram orqali kiring"}
        </p>
        {import.meta.env.DEV && (
          <p className="text-xs text-muted-foreground/60 text-center">
            Test rejimi: initData = "test" sifatida yuborildi
          </p>
        )}
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <Switch>
        <Route path="/" component={HomePage} />
        <Route path="/movies" component={MoviesPage} />
        <Route path="/movies/:id" component={MovieDetailPage} />
        <Route path="/series" component={SeriesPage} />
        <Route path="/series/:id" component={SeriesDetailPage} />
        <Route path="/search" component={SearchPage} />
        <Route path="/favorites" component={FavoritesPage} />
        <Route path="/profile" component={ProfilePage} />
        <Route path="/tariffs" component={TariffsPage} />
        <Route component={NotFound} />
      </Switch>
      <BottomNav />
    </div>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <WouterRouter base={import.meta.env.BASE_URL.replace(/\/$/, "")}>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </WouterRouter>
    </QueryClientProvider>
  );
}

export default App;
