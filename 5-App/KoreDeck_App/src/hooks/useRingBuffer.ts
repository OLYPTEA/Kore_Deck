// =============================================================================
// useRingBuffer.ts — Buffer circulaire pour historiques de stats (sparklines)
// =============================================================================

import { useEffect, useRef, useState } from "react";

/**
 * Maintient un historique de N derniers échantillons, mis à jour à `intervalMs`.
 * - `value` est lu via une ref pour éviter la dépendance de l'intervalle.
 * - Le buffer initial est rempli avec la valeur courante (pas de NaN visible).
 */
export function useRingBuffer(value: number, capacity = 60, intervalMs = 1000): number[] {
  const valueRef = useRef(value);
  valueRef.current = value;

  const [buf, setBuf] = useState<number[]>(() => Array(capacity).fill(value));

  useEffect(() => {
    const id = setInterval(() => {
      setBuf((prev) => {
        const next = prev.slice(1);
        next.push(valueRef.current);
        return next;
      });
    }, intervalMs);
    return () => clearInterval(id);
  }, [capacity, intervalMs]);

  return buf;
}
