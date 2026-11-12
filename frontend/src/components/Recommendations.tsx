import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { apiGet } from "../api/client";
import type { TitleListItem } from "../api/types";
import { useAuth } from "../auth/AuthProvider";
import { TitleCard, TitleCardSkeleton } from "./TitleCard";

type Strategy = "hybrid" | "genre" | "popular";

interface RecommendationItem {
  title: TitleListItem;
  score: number;
  reason: string;
}

const STRATEGIES: { value: Strategy; label: string }[] = [
  { value: "hybrid", label: "Для вас" },
  { value: "genre", label: "За жанрами" },
  { value: "popular", label: "Популярне" },
];

/** A row of recommendations; the tabs switch the backend strategy. */
export function Recommendations() {
  const { user } = useAuth();
  const [strategy, setStrategy] = useState<Strategy>("hybrid");
  const effective: Strategy = user ? strategy : "popular";

  const { data, isPending } = useQuery({
    // "history" prefix: dropped on sign-out together with other per-user data.
    queryKey: ["history", "recommendations", user?.id, effective],
    queryFn: ({ signal }) =>
      apiGet<RecommendationItem[]>("/recommendations", { strategy: effective, limit: 12 }, signal),
    staleTime: 60_000,
  });

  return (
    <section className="recommendations" aria-label="Рекомендації">
      <div className="recommendations__header">
        <h2 className="section-title section-title--compact">
          {user ? "Рекомендовано для вас" : "Популярне зараз"}
        </h2>
        {user && (
          <div className="segmented" role="tablist" aria-label="Алгоритм рекомендацій">
            {STRATEGIES.map((option) => (
              <button
                key={option.value}
                role="tab"
                aria-selected={strategy === option.value}
                className={`segmented__item ${strategy === option.value ? "segmented__item--active" : ""}`}
                onClick={() => setStrategy(option.value)}
              >
                {option.label}
              </button>
            ))}
          </div>
        )}
      </div>

      {isPending ? (
        <div className="recommendations__row">
          {[0, 1, 2, 3, 4, 5].map((i) => (
            <TitleCardSkeleton key={i} />
          ))}
        </div>
      ) : !data?.length ? (
        <p className="muted">Подивіться кілька фільмів — і тут з'являться добірки за вашими жанрами.</p>
      ) : (
        <div className="recommendations__row">
          {data.map((item) => (
            <div key={item.title.id} className="recommendations__item">
              <TitleCard title={item.title} />
              <p className="recommendations__reason">{item.reason}</p>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
