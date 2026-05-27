import { createContext, useContext, useState, useEffect, type ReactNode } from "react";

const BASE = import.meta.env.BASE_URL;

function getApiBase() {
  const b = BASE.endsWith("/") ? BASE.slice(0, -1) : BASE;
  return b + "/api";
}

type TelegramWebApp = {
  initData: string;
  initDataUnsafe: { user?: { id: number; first_name: string; username?: string } };
  ready: () => void;
  expand: () => void;
  colorScheme: "light" | "dark";
  setHeaderColor: (color: string) => void;
  setBackgroundColor: (color: string) => void;
};

declare global {
  interface Window {
    Telegram?: { WebApp?: TelegramWebApp };
  }
}

type UserProfile = {
  tgId: number;
  username: string | null;
  fullName: string;
  lang: string;
  isPremium: boolean;
  premiumUntil: string | null;
  balance: number;
  photoUrl: string | null;
};

type AuthContextValue = {
  token: string | null;
  user: UserProfile | null;
  isLoading: boolean;
  error: string | null;
  refetchProfile: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue>({
  token: null,
  user: null,
  isLoading: true,
  error: null,
  refetchProfile: async () => {},
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<UserProfile | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function refetchProfile() {
    if (!token) return;
    try {
      const res = await fetch(`${getApiBase()}/users/profile`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = (await res.json()) as UserProfile;
        setUser(data);
      }
    } catch {
      // ignore
    }
  }

  useEffect(() => {
    (async () => {
      const twa = window.Telegram?.WebApp;

      if (twa) {
        twa.ready();
        twa.expand();
        twa.setBackgroundColor("#17212b");
        twa.setHeaderColor("#17212b");
      }

      const initData = twa?.initData || (import.meta.env.DEV ? "test" : "");

      if (!initData) {
        setError("Telegram WebApp ma'lumoti topilmadi. Iltimos, botdan oching.");
        setIsLoading(false);
        return;
      }

      try {
        const res = await fetch(`${getApiBase()}/auth/telegram`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ initData }),
        });

        if (!res.ok) {
          const body = (await res.json()) as { error?: string };
          setError(body.error ?? "Autentifikatsiya xatosi");
          setIsLoading(false);
          return;
        }

        const data = (await res.json()) as { token: string; user: UserProfile };
        setToken(data.token);
        setUser(data.user);
      } catch (err) {
        setError("Server bilan bog'lanib bo'lmadi");
        console.error(err);
      } finally {
        setIsLoading(false);
      }
    })();
  }, []);

  return (
    <AuthContext.Provider value={{ token, user, isLoading, error, refetchProfile }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
