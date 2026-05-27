import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/contexts/AuthContext";
import { apiFetch } from "@/lib/api";
import { useState } from "react";
import { useLocation } from "wouter";

type Tariff = {
  id: number;
  name: string;
  duration: number;
  price: number;
  description: string | null;
  pointsPrice: number;
};

type PaymentResponse = {
  paymentId: number;
  cardNumber: string;
  cardOwner: string;
  amount: number;
  tariffName: string;
};

export function TariffsPage() {
  const { token, user, refetchProfile } = useAuth();
  const queryClient = useQueryClient();
  const [, navigate] = useLocation();
  const [paymentInfo, setPaymentInfo] = useState<PaymentResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const { data: tariffs, isLoading } = useQuery<Tariff[]>({
    queryKey: ["tariffs"],
    queryFn: () => apiFetch("/tariffs", token!),
    enabled: !!token,
  });

  const cardMutation = useMutation({
    mutationFn: (tariffId: number) =>
      apiFetch<PaymentResponse>("/payments", token!, {
        method: "POST",
        body: JSON.stringify({ tariffId }),
      }),
    onSuccess: (data) => {
      setPaymentInfo(data);
      setError(null);
    },
    onError: (err) => {
      setError(err instanceof Error ? err.message : "Xato yuz berdi");
    },
  });

  const pointsMutation = useMutation({
    mutationFn: (tariffId: number) =>
      apiFetch<{ ok: boolean; premiumUntil: string | null }>("/payments/points", token!, {
        method: "POST",
        body: JSON.stringify({ tariffId }),
      }),
    onSuccess: () => {
      refetchProfile();
      queryClient.invalidateQueries({ queryKey: ["tariffs"] });
      navigate("/profile");
    },
    onError: (err) => {
      setError(err instanceof Error ? err.message : "Balans yetarli emas");
    },
  });

  return (
    <div className="pb-24">
      <div className="sticky top-0 bg-background/95 backdrop-blur z-10 px-4 py-3 border-b border-border flex items-center gap-2">
        <button onClick={() => navigate("/profile")} className="text-muted-foreground text-sm">←</button>
        <h1 className="text-base font-bold text-foreground">⭐ Premium Tariflar</h1>
      </div>

      <div className="px-4 mt-4">
        <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-xl p-3 mb-4">
          <p className="text-yellow-400 font-semibold text-sm">Premium afzalliklari:</p>
          <ul className="mt-2 space-y-1">
            {["Barcha filmlarni cheklovsiz tomosha qilish", "Seriyalarni oldinroq ko'rish", "Reklama yo'q"].map(
              (t) => (
                <li key={t} className="text-xs text-foreground/80 flex items-start gap-1.5">
                  <span className="text-yellow-400 mt-0.5">✓</span>
                  {t}
                </li>
              ),
            )}
          </ul>
        </div>

        {isLoading ? (
          <p className="text-center text-sm text-muted-foreground animate-pulse">Yuklanmoqda...</p>
        ) : !tariffs?.length ? (
          <p className="text-center text-sm text-muted-foreground mt-8">Tariflar mavjud emas</p>
        ) : (
          <div className="space-y-3">
            {tariffs.map((t) => (
              <div key={t.id} className="bg-card rounded-xl p-4 border border-border">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-semibold text-foreground">{t.name}</p>
                    <p className="text-xs text-muted-foreground mt-0.5">{t.duration} kun</p>
                    {t.description && (
                      <p className="text-xs text-muted-foreground mt-1">{t.description}</p>
                    )}
                  </div>
                  <div className="text-right">
                    <p className="text-lg font-bold text-primary">{t.price.toLocaleString()} UZS</p>
                    {t.pointsPrice > 0 && (
                      <p className="text-xs text-muted-foreground">{t.pointsPrice} 💎</p>
                    )}
                  </div>
                </div>

                <div className="flex gap-2 mt-3">
                  <button
                    onClick={() => cardMutation.mutate(t.id)}
                    disabled={cardMutation.isPending}
                    className="flex-1 bg-primary text-primary-foreground text-xs font-medium py-2 rounded-lg disabled:opacity-60"
                  >
                    💳 Karta orqali
                  </button>
                  {t.pointsPrice > 0 && (
                    <button
                      onClick={() => pointsMutation.mutate(t.id)}
                      disabled={
                        pointsMutation.isPending ||
                        (user?.balance ?? 0) < t.pointsPrice
                      }
                      className="flex-1 bg-yellow-500/20 text-yellow-400 text-xs font-medium py-2 rounded-lg disabled:opacity-40"
                    >
                      💎 Balans ({user?.balance ?? 0})
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        {error && (
          <div className="mt-4 bg-destructive/10 text-destructive text-xs px-3 py-2 rounded-lg">
            {error}
          </div>
        )}

        {paymentInfo && (
          <div className="mt-4 bg-card border border-border rounded-xl p-4">
            <p className="font-semibold text-foreground text-sm mb-3">To'lov ma'lumotlari</p>
            <div className="space-y-2">
              <div className="flex justify-between text-xs">
                <span className="text-muted-foreground">Karta raqami:</span>
                <span className="font-mono font-bold text-foreground">{paymentInfo.cardNumber}</span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-muted-foreground">Egasi:</span>
                <span className="text-foreground">{paymentInfo.cardOwner}</span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-muted-foreground">Summa:</span>
                <span className="font-bold text-primary">{paymentInfo.amount.toLocaleString()} UZS</span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-muted-foreground">Tarif:</span>
                <span className="text-foreground">{paymentInfo.tariffName}</span>
              </div>
            </div>
            <p className="text-[10px] text-muted-foreground mt-3 leading-relaxed">
              To'lov amalga oshirilgandan so'ng admin tomonidan aktivatsiya qilinadi.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
