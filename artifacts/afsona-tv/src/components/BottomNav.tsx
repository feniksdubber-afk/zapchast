import { useLocation } from "wouter";

const navItems = [
  { path: "/", icon: "🏠", label: "Asosiy" },
  { path: "/movies", icon: "🎬", label: "Filmlar" },
  { path: "/series", icon: "📺", label: "Seriallar" },
  { path: "/search", icon: "🔍", label: "Qidiruv" },
  { path: "/profile", icon: "👤", label: "Profil" },
];

export function BottomNav() {
  const [location, navigate] = useLocation();

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50 bg-card border-t border-border flex items-stretch">
      {navItems.map((item) => {
        const active = location === item.path;
        return (
          <button
            key={item.path}
            onClick={() => navigate(item.path)}
            className={`flex-1 flex flex-col items-center justify-center py-2 gap-0.5 text-xs transition-colors ${
              active
                ? "text-primary"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            <span className="text-xl leading-none">{item.icon}</span>
            <span className={`font-medium ${active ? "text-primary" : ""}`}>{item.label}</span>
          </button>
        );
      })}
    </nav>
  );
}
