export type ExamId = 'ielts' | 'toefl' | 'toeic' | 'cambridge';

export type ExamTrackStep = {
  id: string;
  title: string;
  description: string;
  href: string;
  cadence: string;
  minutes: number;
};

export type ExamTrack = {
  id: ExamId;
  title: string;
  goal: string;
  scoreHint: string;
  targets: {
    wordsLearned: number;
    streakDays: number;
    dailyGoalProgress: number;
  };
  weeklySteps: ExamTrackStep[];
};

export const EXAM_TRACKS: Record<ExamId, ExamTrack> = {
  ielts: {
    id: 'ielts',
    title: 'IELTS',
    goal: 'Band score 6.0+ com equilíbrio entre Reading, Listening, Writing e Speaking.',
    scoreHint: 'Band score (1-9)',
    targets: {
      wordsLearned: 180,
      streakDays: 7,
      dailyGoalProgress: 85,
    },
    weeklySteps: [
      {
        id: 'vocab-core',
        title: 'Base de vocabulário',
        description: 'Revisar e aprender vocabulário de alta frequência para o exame.',
        href: '/study',
        cadence: 'Diário',
        minutes: 20,
      },
      {
        id: 'reading-focus',
        title: 'Leitura orientada',
        description: 'Treinar skimming, scanning e inferência com textos curtos.',
        href: '/texts',
        cadence: '4x na semana',
        minutes: 25,
      },
      {
        id: 'listening-practice',
        title: 'Listening de precisão',
        description: 'Praticar captura de detalhes e ortografia com ditado.',
        href: '/games/dictation',
        cadence: '3x na semana',
        minutes: 15,
      },
      {
        id: 'speaking-drill',
        title: 'Speaking guiado',
        description: 'Responder com clareza e fluência usando frases do dia a dia.',
        href: '/sentences',
        cadence: '3x na semana',
        minutes: 20,
      },
      {
        id: 'mock-ai',
        title: 'Mini-simulado IA',
        description: 'Aplicar em contexto de prova e revisar plano de estudo.',
        href: '#coach-ia',
        cadence: '1x na semana',
        minutes: 25,
      },
    ],
  },
  toefl: {
    id: 'toefl',
    title: 'TOEFL iBT',
    goal: 'Pontuação 80+ com foco em contexto acadêmico e respostas integradas.',
    scoreHint: 'TOEFL iBT (0-120)',
    targets: {
      wordsLearned: 220,
      streakDays: 10,
      dailyGoalProgress: 90,
    },
    weeklySteps: [
      {
        id: 'vocab-academic',
        title: 'Vocabulário acadêmico',
        description: 'Fortalecer termos acadêmicos e conectores para leitura/escrita.',
        href: '/study',
        cadence: 'Diário',
        minutes: 20,
      },
      {
        id: 'reading-academic',
        title: 'Reading acadêmico',
        description: 'Treinar interpretação de textos informativos e argumentativos.',
        href: '/texts',
        cadence: '4x na semana',
        minutes: 30,
      },
      {
        id: 'listening-notes',
        title: 'Listening + anotações',
        description: 'Praticar compreensão de aulas e registro de pontos-chave.',
        href: '/games/dictation',
        cadence: '3x na semana',
        minutes: 20,
      },
      {
        id: 'speaking-integrated',
        title: 'Speaking integrado',
        description: 'Responder com estrutura em tempo controlado.',
        href: '/sentences',
        cadence: '3x na semana',
        minutes: 20,
      },
      {
        id: 'mock-ai',
        title: 'Mini-simulado IA',
        description: 'Avaliar desempenho por habilidade e ajustar a próxima semana.',
        href: '#coach-ia',
        cadence: '1x na semana',
        minutes: 30,
      },
    ],
  },
  toeic: {
    id: 'toeic',
    title: 'TOEIC',
    goal: 'Pontuação 700+ com foco em comunicação profissional e velocidade de leitura.',
    scoreHint: 'TOEIC (10-990)',
    targets: {
      wordsLearned: 150,
      streakDays: 7,
      dailyGoalProgress: 80,
    },
    weeklySteps: [
      {
        id: 'vocab-business',
        title: 'Vocabulário de negócios',
        description: 'Treinar collocations e expressões comuns no ambiente de trabalho.',
        href: '/study',
        cadence: 'Diário',
        minutes: 15,
      },
      {
        id: 'reading-speed',
        title: 'Reading com velocidade',
        description: 'Ganhar ritmo em e-mails, avisos e textos funcionais.',
        href: '/texts',
        cadence: '4x na semana',
        minutes: 20,
      },
      {
        id: 'listening-accuracy',
        title: 'Listening operacional',
        description: 'Focar em detalhes e tomada de decisão rápida.',
        href: '/games/dictation',
        cadence: '3x na semana',
        minutes: 15,
      },
      {
        id: 'quick-response',
        title: 'Respostas rápidas',
        description: 'Praticar clareza e objetividade em respostas orais.',
        href: '/sentences',
        cadence: '2x na semana',
        minutes: 15,
      },
      {
        id: 'mock-ai',
        title: 'Mini-simulado IA',
        description: 'Checar consistência e planejar pontos de maior retorno.',
        href: '#coach-ia',
        cadence: '1x na semana',
        minutes: 20,
      },
    ],
  },
  cambridge: {
    id: 'cambridge',
    title: 'Cambridge',
    goal: 'Preparação consistente para B2/C1/C2 com precisão gramatical e lexical.',
    scoreHint: 'Feedback por nível (B2/C1/C2)',
    targets: {
      wordsLearned: 260,
      streakDays: 12,
      dailyGoalProgress: 90,
    },
    weeklySteps: [
      {
        id: 'vocab-depth',
        title: 'Vocabulário de profundidade',
        description: 'Trabalhar nuance lexical, collocations e registro.',
        href: '/study',
        cadence: 'Diário',
        minutes: 25,
      },
      {
        id: 'reading-challenge',
        title: 'Reading de alta complexidade',
        description: 'Treinar leitura crítica e inferência em textos densos.',
        href: '/texts',
        cadence: '4x na semana',
        minutes: 30,
      },
      {
        id: 'grammar-control',
        title: 'Controle gramatical',
        description: 'Praticar precisão e transformação de estruturas.',
        href: '/games/grammar-builder',
        cadence: '3x na semana',
        minutes: 20,
      },
      {
        id: 'speaking-precision',
        title: 'Speaking com precisão',
        description: 'Refinar fluência, pronúncia e organização de resposta.',
        href: '/sentences',
        cadence: '3x na semana',
        minutes: 20,
      },
      {
        id: 'mock-ai',
        title: 'Mini-simulado IA',
        description: 'Validar consistência geral e priorizar próximo ciclo.',
        href: '#coach-ia',
        cadence: '1x na semana',
        minutes: 30,
      },
    ],
  },
};

