'use client';

import { useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';

function mapLegacyLevelToGrammar(level: string | null): string {
  const normalized = (level || '').trim().toUpperCase();
  if (normalized === 'A1') return '1';
  if (normalized === 'A2') return '2';
  if (['B1', 'B2', 'C1', 'C2'].includes(normalized)) return '3';
  if (['1', '2', '3'].includes(normalized)) return normalized;
  return '';
}

export default function SentenceBuilderRedirectPage() {
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    const nextParams = new URLSearchParams(searchParams.toString());
    const mappedLevel = mapLegacyLevelToGrammar(nextParams.get('level'));
    if (mappedLevel) {
      nextParams.set('level', mappedLevel);
    } else {
      nextParams.delete('level');
    }

    const query = nextParams.toString();
    router.replace(query ? `/games/grammar-builder?${query}` : '/games/grammar-builder');
  }, [router, searchParams]);

  return null;
}
