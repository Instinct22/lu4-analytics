import { useEffect, useState } from "react";

export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(() =>
    typeof window === "undefined" ? false : window.matchMedia(query).matches,
  );

  useEffect(() => {
    const mql = window.matchMedia(query);
    const onChange = (e: MediaQueryListEvent) => setMatches(e.matches);
    setMatches(mql.matches);
    mql.addEventListener("change", onChange);
    return () => mql.removeEventListener("change", onChange);
  }, [query]);

  return matches;
}

/** Высота графиков растёт вместе с шириной экрана. */
export function useChartHeight(base = 420): number {
  const is2xl = useMediaQuery("(min-width: 1536px)");
  const is3xl = useMediaQuery("(min-width: 2200px)");
  if (is3xl) return Math.round(base * 1.35);
  if (is2xl) return Math.round(base * 1.18);
  return base;
}
