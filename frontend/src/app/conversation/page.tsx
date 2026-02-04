'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import type { PointerEvent as ReactPointerEvent } from 'react';
import { conversationApi } from '@/lib/api';
import Link from 'next/link';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  audio_url?: string;
  timestamp: Date;
}

interface LessonAttempt {
  id: number;
  created_at: string;
  questions: string[];
  answers: string[];
  ai_feedback?: string | null;
  topic?: string | null;
  num_questions?: number | null;
  score?: number | null;
}

interface PronunciationAttempt {
  question_index?: number | null;
  transcript: string;
  similarity?: number | null;
  feedback: string;
  created_at: string;
}

type Voice = {
  voice_id: string;
  name: string;
};

export default function ConversationPage() {
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [autoPlay, setAutoPlay] = useState(true);
  const [autoSendOnMicEnd, setAutoSendOnMicEnd] = useState(false);
  const [autoPronunciationOnMic, setAutoPronunciationOnMic] = useState(true);
  const [pressToTalk, setPressToTalk] = useState(false);
  const [showInterimTranscript, setShowInterimTranscript] = useState(false);
  const [interimTranscript, setInterimTranscript] = useState('');
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [selectedVoice, setSelectedVoice] = useState<string>('');
  const [voices, setVoices] = useState<Voice[]>([]);
  const [browserSttAvailable, setBrowserSttAvailable] = useState(false);
  const [preferBrowserStt, setPreferBrowserStt] = useState(true);
  const [lessonMode, setLessonMode] = useState(false);
  const [lessonActive, setLessonActive] = useState(false);
  const [lessonQuestionsText, setLessonQuestionsText] = useState('');
  const [lessonNativeLanguage, setLessonNativeLanguage] = useState('pt-BR');
  const [lessonTotalQuestions, setLessonTotalQuestions] = useState(0);
  const [lessonCurrentIndex, setLessonCurrentIndex] = useState(0);
  const [lessonFinalFeedback, setLessonFinalFeedback] = useState('');
  const [lessonTopic, setLessonTopic] = useState('General conversation');
  const [lessonNumQuestions, setLessonNumQuestions] = useState(10);
  const [isGeneratingLesson, setIsGeneratingLesson] = useState(false);
  const [isRecordingPronunciation, setIsRecordingPronunciation] = useState(false);
  const [pronunciationFeedback, setPronunciationFeedback] = useState('');
  const [pronunciationMeta, setPronunciationMeta] = useState<{
    expectedText: string;
    transcript: string;
    similarity?: number | null;
  } | null>(null);
  const [lessonAttempts, setLessonAttempts] = useState<LessonAttempt[]>([]);
  const [isLoadingAttempts, setIsLoadingAttempts] = useState(false);
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const [expandedAttemptIds, setExpandedAttemptIds] = useState<number[]>([]);
  const [pronunciationByAttempt, setPronunciationByAttempt] = useState<Record<number, PronunciationAttempt[]>>({});
  const [systemPrompt, setSystemPrompt] = useState(
    `You are Alex, a friendly English coach for a Brazilian student.
Keep replies concise and natural. Ask open-ended questions.
If there are mistakes, add a short Coach's Corner with **bold** fixes and 1-2 tips.
Prefer English.`
  );
  const [isConfigOpen, setIsConfigOpen] = useState(false);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const audioRef = useRef<HTMLAudioElement>(null);
  const ttsUnavailableRef = useRef(false);
  const autoSendOnMicEndRef = useRef(false);
  const currentAudioUrlRef = useRef<string | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const lastUserMessageRef = useRef<string>('');
  const isListeningRef = useRef<boolean>(false);
  const manualStopListeningRef = useRef<boolean>(false);
  const autoPronunciationOnMicRef = useRef<boolean>(true);
  const resumeListeningAfterSendRef = useRef<boolean>(false);
  const showInterimTranscriptRef = useRef<boolean>(false);
  const interimTranscriptRef = useRef<string>('');
  const preferBrowserSttRef = useRef<boolean>(true);
  const pressToTalkRef = useRef<boolean>(false);
  const startListeningRef = useRef<() => void>(() => {});
  const stopListeningRef = useRef<() => void>(() => {});
  const micRecorderRef = useRef<MediaRecorder | null>(null);
  const micStreamRef = useRef<MediaStream | null>(null);
  const micAudioChunksRef = useRef<Blob[]>([]);
  const pendingMicExpectedTextRef = useRef<string>('');
  const sttWsRef = useRef<WebSocket | null>(null);
  const sttStreamRef = useRef<MediaStream | null>(null);
  const sttAudioContextRef = useRef<AudioContext | null>(null);
  const sttProcessorRef = useRef<ScriptProcessorNode | null>(null);
  const sttSourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const sttRecorderRef = useRef<MediaRecorder | null>(null);
  const sttChunksRef = useRef<Blob[]>([]);
  const startServerSttRecordingRef = useRef<() => void>(() => {});
  const isSpeakingRef = useRef<boolean>(false);
  const speechRecognitionRef = useRef<SpeechRecognition | null>(null);
  const speechRecognitionActiveRef = useRef<boolean>(false);
  const useWebSpeechRef = useRef<boolean>(false);

  const conversationIdRef = useRef<string | null>(null);
  const systemPromptRef = useRef<string>('');
  const inputMessageRef = useRef<string>('');
  const isLoadingRef = useRef<boolean>(false);
  const lastTranscriptRef = useRef<string>('');
  const lastAutoSentTranscriptRef = useRef<string>('');
  const finalTranscriptRef = useRef<string>('');
  const sendMessageRef = useRef<(overrideMessage?: string) => Promise<void>>(
    async () => {}
  );

  const extractErrorMessage = useCallback((error: unknown): string => {
    if (error && typeof error === 'object') {
      const maybe = error as {
        response?: { data?: { detail?: string } };
        message?: string;
      };
      return maybe.response?.data?.detail ?? maybe.message ?? 'Erro desconhecido';
    }
    return String(error);
  }, []);

  const getAxiosResponseStatus = useCallback((error: unknown): number | undefined => {
    if (!error || typeof error !== 'object') return undefined;
    if (!('response' in error)) return undefined;
    const response = (error as { response?: unknown }).response;
    if (!response || typeof response !== 'object') return undefined;
    if (!('status' in response)) return undefined;
    const statusValue = (response as { status?: unknown }).status;
    return typeof statusValue === 'number' ? statusValue : undefined;
  }, []);

  useEffect(() => {
    conversationIdRef.current = conversationId;
  }, [conversationId]);

  useEffect(() => {
    systemPromptRef.current = systemPrompt;
  }, [systemPrompt]);

  useEffect(() => {
    inputMessageRef.current = inputMessage;
  }, [inputMessage]);

  useEffect(() => {
    isLoadingRef.current = isLoading;
  }, [isLoading]);

  useEffect(() => {
    autoSendOnMicEndRef.current = autoSendOnMicEnd;
  }, [autoSendOnMicEnd]);

  useEffect(() => {
    autoPronunciationOnMicRef.current = autoPronunciationOnMic;
  }, [autoPronunciationOnMic]);

  useEffect(() => {
    showInterimTranscriptRef.current = showInterimTranscript;
    const recognition = speechRecognitionRef.current;
    if (recognition) {
      recognition.interimResults = showInterimTranscript;
    }
    if (!showInterimTranscript && interimTranscriptRef.current) {
      interimTranscriptRef.current = '';
      setInterimTranscript('');
    }
  }, [showInterimTranscript]);

  useEffect(() => {
    preferBrowserSttRef.current = preferBrowserStt;
  }, [preferBrowserStt]);

  useEffect(() => {
    pressToTalkRef.current = pressToTalk;
  }, [pressToTalk]);

  useEffect(() => {
    isListeningRef.current = isListening;
  }, [isListening]);

  useEffect(() => {
    isSpeakingRef.current = isSpeaking;
  }, [isSpeaking]);

  // Carrega vozes disponíveis
  useEffect(() => {
    loadVoices();
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const coarsePointer = window.matchMedia?.('(pointer: coarse)').matches ?? false;
    const hasTouch = navigator.maxTouchPoints > 0;
    if (coarsePointer || hasTouch) {
      setPressToTalk(true);
    }
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const SpeechRecognitionCtor =
      window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognitionCtor) return;

    const recognition = new SpeechRecognitionCtor();
    recognition.lang = 'en-US';
    recognition.interimResults = showInterimTranscriptRef.current;
    recognition.continuous = false;

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      let finalText = finalTranscriptRef.current || '';
      let interimText = '';

      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        const result = event.results[i];
        const transcript = result[0]?.transcript || '';
        if (result.isFinal) {
          finalText += `${transcript} `;
        } else {
          interimText += transcript;
        }
      }

      finalText = finalText.trim();
      interimText = interimText.trim();

      if (finalText) {
        const currentInput = inputMessageRef.current.trim();
        if (!currentInput || finalText.length >= currentInput.length) {
          if (finalText !== lastTranscriptRef.current) {
            lastTranscriptRef.current = finalText;
            inputMessageRef.current = finalText;
            setInputMessage(finalText);
          }
        }
      }

      const shouldShowInterim = showInterimTranscriptRef.current;
      if (shouldShowInterim) {
        if (interimText !== interimTranscriptRef.current) {
          interimTranscriptRef.current = interimText;
          setInterimTranscript(interimText);
        }
      } else if (interimTranscriptRef.current) {
        interimTranscriptRef.current = '';
        setInterimTranscript('');
      }

      if (finalText && autoSendOnMicEndRef.current && !isLoadingRef.current) {
        if (finalText !== lastAutoSentTranscriptRef.current) {
          lastAutoSentTranscriptRef.current = finalText;
          void sendMessageRef.current(finalText);
        }
      }

      if (finalText && !autoSendOnMicEndRef.current) {
        manualStopListeningRef.current = true;
        isListeningRef.current = false;
        setIsListening(false);
        try {
          recognition.stop();
        } catch {
          // ignore
        }
      }

      finalTranscriptRef.current = finalText;
    };

    recognition.onerror = () => {
      speechRecognitionActiveRef.current = false;
      if (manualStopListeningRef.current) return;
      if (isListeningRef.current && preferBrowserSttRef.current) {
        useWebSpeechRef.current = false;
        startServerSttRecordingRef.current();
      }
    };

    recognition.onend = () => {
      speechRecognitionActiveRef.current = false;
      if (interimTranscriptRef.current) {
        interimTranscriptRef.current = '';
        setInterimTranscript('');
      }
      if (useWebSpeechRef.current && isListeningRef.current && !manualStopListeningRef.current && !isSpeakingRef.current) {
        setTimeout(() => {
          try {
            recognition.start();
            speechRecognitionActiveRef.current = true;
          } catch {
            // ignore
          }
        }, 150);
      }
    };

    speechRecognitionRef.current = recognition;
    setBrowserSttAvailable(true);
  }, []);

  // Auto-scroll para última mensagem
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const ensureConversationStarted = useCallback(async (): Promise<string> => {
    if (conversationIdRef.current) return conversationIdRef.current;

    const response = await conversationApi.startConversation({
      system_prompt: systemPromptRef.current
    });

    const newConversationId = response.data.conversation_id as string;
    conversationIdRef.current = newConversationId;
    setConversationId(newConversationId);
    setIsConfigOpen(false);
    return newConversationId;
  }, []);

  const cleanupCurrentAudioUrl = useCallback(() => {
    if (audioRef.current) {
      try {
        audioRef.current.pause();
        audioRef.current.removeAttribute('src');
        audioRef.current.load();
      } catch {
        // ignore
      }
    }
    if (currentAudioUrlRef.current) {
      URL.revokeObjectURL(currentAudioUrlRef.current);
      currentAudioUrlRef.current = null;
    }
  }, []);

  const playTextAsAudio = useCallback(async (text: string) => {
    try {
      if (isListeningRef.current && !manualStopListeningRef.current) {
        stopListeningRef.current();
      }
      isSpeakingRef.current = true;
      setIsSpeaking(true);

      // Stop any current audio and free object URLs
      if (audioRef.current) {
        try {
          audioRef.current.pause();
          audioRef.current.currentTime = 0;
        } catch {
          // ignore
        }
      }
      cleanupCurrentAudioUrl();

      const response = await conversationApi.textToSpeech({
        text,
        voice_id: selectedVoice
      });

      // Cria URL do blob de áudio
      const audioBlob = new Blob([response.data], { type: 'audio/mpeg' });
      const audioUrl = URL.createObjectURL(audioBlob);
      currentAudioUrlRef.current = audioUrl;

      // Reproduz áudio
      if (audioRef.current) {
        audioRef.current.src = audioUrl;
        await audioRef.current.play();
      } else {
        // If audio element isn't available, stop the speaking indicator.
        cleanupCurrentAudioUrl();
        isSpeakingRef.current = false;
        setIsSpeaking(false);
        if (resumeListeningAfterSendRef.current && autoSendOnMicEndRef.current && !pressToTalkRef.current) {
          resumeListeningAfterSendRef.current = false;
          manualStopListeningRef.current = false;
          isListeningRef.current = true;
          setIsListening(true);
          startListeningRef.current();
        }
      }
    } catch (error: unknown) {
      const statusCode = getAxiosResponseStatus(error);
      // Any backend failure should disable autoplay to avoid spamming errors.
      if ((statusCode === 400 || statusCode === 429 || statusCode === 502 || statusCode === 503) && !ttsUnavailableRef.current) {
        ttsUnavailableRef.current = true;
        setAutoPlay(false);
        if (statusCode === 429) {
          alert('TTS atingiu limite (429). Auto-play foi desativado.');
        } else if (statusCode === 400 || statusCode === 503) {
          alert('TTS não está configurado/indisponível (verifique OPENAI_API_KEY). Auto-play foi desativado.');
        } else {
          alert('TTS falhou (502). Auto-play foi desativado.');
        }
      }
      console.error('Erro ao reproduzir áudio:', error);
      cleanupCurrentAudioUrl();
      isSpeakingRef.current = false;
      setIsSpeaking(false);
      if (resumeListeningAfterSendRef.current && autoSendOnMicEndRef.current && !pressToTalkRef.current) {
        resumeListeningAfterSendRef.current = false;
        manualStopListeningRef.current = false;
        isListeningRef.current = true;
        setIsListening(true);
        startListeningRef.current();
      }
    }
  }, [cleanupCurrentAudioUrl, getAxiosResponseStatus, selectedVoice]);

  const startLesson = useCallback(async () => {
    const parsedQuestions = lessonQuestionsText
      .split('\n')
      .map((q) => q.trim())
      .filter(Boolean);

    const safeNumQuestions = Number.isFinite(lessonNumQuestions)
      ? Math.max(1, lessonNumQuestions)
      : Math.max(3, parsedQuestions.length || 10);

    setIsLoading(true);
    try {
      let finalQuestions = safeNumQuestions
        ? parsedQuestions.slice(0, safeNumQuestions)
        : parsedQuestions;

      if (parsedQuestions.length === 0) {
        const topic = lessonTopic.trim() || 'general conversation';
        const generated = await conversationApi.generateLesson({
          topic,
          num_questions: Math.max(3, safeNumQuestions),
        });
        finalQuestions = (generated.data.questions || []).slice(0, Math.max(3, safeNumQuestions));
        setLessonQuestionsText(finalQuestions.join('\n'));
      }

      if (finalQuestions.length < 3) {
        alert('Informe pelo menos 3 perguntas (ou deixe em branco para gerar automaticamente).');
        return;
      }

      const response = await conversationApi.startLesson({
        questions: finalQuestions,
        native_language: lessonNativeLanguage,
        target_language: 'en',
        topic: lessonTopic,
        num_questions: lessonNumQuestions,
      });

      const newConversationId = response.data.conversation_id as string;
      setConversationId(newConversationId);
      conversationIdRef.current = newConversationId;
      setLessonActive(true);
      setLessonTotalQuestions(response.data.total_questions as number);
      setLessonCurrentIndex(0);
      setLessonFinalFeedback('');
      setPronunciationFeedback('');
      setPronunciationMeta(null);
      setMessages([
        {
          id: Date.now().toString(),
          role: 'assistant',
          content: response.data.first_question as string,
          timestamp: new Date()
        }
      ]);
      if (autoPlay) {
        void playTextAsAudio(response.data.first_question as string);
      }
      manualStopListeningRef.current = true;
      isListeningRef.current = false;
      setIsListening(false);
      setIsConfigOpen(false);
    } catch (error: unknown) {
      alert('Erro ao iniciar lição: ' + extractErrorMessage(error));
    } finally {
      setIsLoading(false);
    }
  }, [autoPlay, extractErrorMessage, lessonNativeLanguage, lessonNumQuestions, lessonQuestionsText, lessonTopic, playTextAsAudio]);

  const loadLessonAttempts = useCallback(async () => {
    setIsLoadingAttempts(true);
    try {
      const response = await conversationApi.listLessonAttempts({ limit: 5 });
      setLessonAttempts(response.data || []);
    } catch (error: unknown) {
      console.error('Erro ao carregar histórico de lições:', error);
    } finally {
      setIsLoadingAttempts(false);
    }
  }, []);

  const generateLessonQuestions = useCallback(async () => {
    const topic = lessonTopic.trim() || 'general conversation';

    const safeNumQuestions = Number.isFinite(lessonNumQuestions)
      ? Math.max(3, lessonNumQuestions)
      : 10;

    setIsGeneratingLesson(true);
    try {
      const response = await conversationApi.generateLesson({
        topic,
        num_questions: safeNumQuestions,
      });
      const questions = response.data.questions || [];
      setLessonQuestionsText(questions.slice(0, safeNumQuestions).join('\n'));
    } catch (error: unknown) {
      alert('Erro ao gerar perguntas: ' + extractErrorMessage(error));
    } finally {
      setIsGeneratingLesson(false);
    }
  }, [extractErrorMessage, lessonNumQuestions, lessonTopic]);

  const toggleAttemptExpanded = useCallback((attemptId: number) => {
    setExpandedAttemptIds((prev) =>
      prev.includes(attemptId) ? prev.filter((id) => id !== attemptId) : [...prev, attemptId]
    );
  }, []);

  const loadLessonAttemptDetails = useCallback(async (attemptId: number) => {
    if (pronunciationByAttempt[attemptId]) return;
    try {
      const response = await conversationApi.getLessonAttemptDetails(attemptId);
      const pronunciations = response.data?.pronunciations || [];
      setPronunciationByAttempt((prev) => ({ ...prev, [attemptId]: pronunciations }));
    } catch (error: unknown) {
      console.error('Erro ao carregar detalhes da lição:', error);
    }
  }, [pronunciationByAttempt]);

  const analyzePronunciationFromBlob = useCallback(async (audioBlob: Blob, expectedText: string) => {
    const formData = new FormData();
    formData.append('audio', audioBlob, 'pronunciation.webm');
    formData.append('expected_text', expectedText || '');
    formData.append('native_language', lessonNativeLanguage);
    if (conversationIdRef.current) {
      formData.append('conversation_id', conversationIdRef.current);
    }
    if (lessonActive || lessonFinalFeedback) {
      formData.append('question_index', String(lessonCurrentIndex));
    }

    const response = await conversationApi.analyzePronunciation(formData);
    setPronunciationFeedback(response.data.feedback || '');
    setPronunciationMeta({
      expectedText: expectedText || '',
      transcript: response.data.transcript || '',
      similarity: response.data.similarity ?? null,
    });
  }, [lessonActive, lessonFinalFeedback, lessonCurrentIndex, lessonNativeLanguage]);

  const cleanupMicStream = useCallback(() => {
    try {
      micStreamRef.current?.getTracks().forEach((track) => track.stop());
    } catch {
      // ignore
    }
    micStreamRef.current = null;
  }, []);

  const cleanupSttStream = useCallback(() => {
    try {
      sttStreamRef.current?.getTracks().forEach((track) => track.stop());
    } catch {
      // ignore
    }
    sttStreamRef.current = null;
    if (sttProcessorRef.current) {
      try {
        sttProcessorRef.current.disconnect();
      } catch {
        // ignore
      }
    }
    sttProcessorRef.current = null;
    if (sttSourceRef.current) {
      try {
        sttSourceRef.current.disconnect();
      } catch {
        // ignore
      }
    }
    sttSourceRef.current = null;
    if (sttAudioContextRef.current) {
      try {
        sttAudioContextRef.current.close();
      } catch {
        // ignore
      }
      sttAudioContextRef.current = null;
    }
    if (sttWsRef.current) {
      try {
        sttWsRef.current.close();
      } catch {
        // ignore
      }
      sttWsRef.current = null;
    }
  }, []);

  const stopSttRecorder = useCallback(() => {
    if (!sttRecorderRef.current) return;
    try {
      if (sttRecorderRef.current.state !== 'inactive') {
        sttRecorderRef.current.stop();
      }
    } catch {
      // ignore
    }
  }, []);

  const startServerSttRecording = useCallback(async () => {
    if (sttRecorderRef.current || typeof window === 'undefined') return;
    if (!navigator.mediaDevices?.getUserMedia) return;
    if (isSpeakingRef.current) return;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });
      sttStreamRef.current = stream;
      sttChunksRef.current = [];

      const audioContext = new AudioContext();
      sttAudioContextRef.current = audioContext;
      const source = audioContext.createMediaStreamSource(stream);
      sttSourceRef.current = source;
      const analyser = audioContext.createAnalyser();
      analyser.fftSize = 2048;
      source.connect(analyser);
      const analyserData = new Uint8Array(analyser.fftSize);
      const startedAt = Date.now();
      let lastVoiceAt = startedAt;
      let lastFrameAt = startedAt;
      let voiceDetected = false;
      let voiceMs = 0;
      const silenceMs = 900;
      const minRecordMs = 1200;
      const maxWaitForVoiceMs = 4000;
      const minVoiceMs = 300;
      const voiceThreshold = 0.03;

      const preferredTypes = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4'];
      const mimeType = preferredTypes.find(
        (t) => typeof MediaRecorder !== 'undefined' && MediaRecorder.isTypeSupported(t)
      );

      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
      sttRecorderRef.current = recorder;

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          sttChunksRef.current.push(event.data);
        }
      };

      recorder.onstop = async () => {
        const audioBlob = new Blob(sttChunksRef.current, {
          type: recorder.mimeType || 'audio/webm',
        });
        sttChunksRef.current = [];
        sttRecorderRef.current = null;
        cleanupSttStream();

        if (!audioBlob || audioBlob.size < 800 || !voiceDetected || voiceMs < minVoiceMs) {
          if (isListeningRef.current && !manualStopListeningRef.current) {
            startServerSttRecordingRef.current();
          }
          return;
        }

        const formData = new FormData();
        formData.append('audio', audioBlob, 'conversation.webm');
        formData.append('language', 'en');

        try {
          setIsTranscribing(true);
          const response = await conversationApi.transcribeAudio(formData);
          const transcript = (response.data?.transcript || '').trim();
          if (!transcript) return;

          if (transcript === lastTranscriptRef.current) {
            return;
          }
          const currentInput = inputMessageRef.current.trim();
          if (currentInput && transcript.length <= currentInput.length) {
            return;
          }

          lastTranscriptRef.current = transcript;
          finalTranscriptRef.current = transcript;
          inputMessageRef.current = transcript;
          setInputMessage(transcript);
          if (interimTranscriptRef.current) {
            interimTranscriptRef.current = '';
            setInterimTranscript('');
          }

          if (autoSendOnMicEndRef.current && !isLoadingRef.current) {
            if (transcript !== lastAutoSentTranscriptRef.current) {
              lastAutoSentTranscriptRef.current = transcript;
              void sendMessageRef.current(transcript);
            }
          }
        } catch (error: unknown) {
          alert('Erro ao transcrever áudio: ' + extractErrorMessage(error));
        } finally {
          setIsTranscribing(false);
          if (!autoSendOnMicEndRef.current) {
            manualStopListeningRef.current = true;
            isListeningRef.current = false;
            setIsListening(false);
            return;
          }
          if (isListeningRef.current && !manualStopListeningRef.current) {
            setTimeout(() => startServerSttRecordingRef.current(), 150);
          }
        }
      };

      const checkSilence = () => {
        if (!sttRecorderRef.current || sttRecorderRef.current.state !== 'recording') return;
        analyser.getByteTimeDomainData(analyserData);
        let sum = 0;
        for (let i = 0; i < analyserData.length; i += 1) {
          const normalized = (analyserData[i] - 128) / 128;
          sum += normalized * normalized;
        }
        const rms = Math.sqrt(sum / analyserData.length);
        const now = Date.now();
        const frameMs = Math.max(0, now - lastFrameAt);
        lastFrameAt = now;
        if (rms > voiceThreshold) {
          voiceDetected = true;
          voiceMs += frameMs;
          lastVoiceAt = now;
        }
        if (voiceDetected) {
          if (now - startedAt > minRecordMs && now - lastVoiceAt > silenceMs) {
            try {
              sttRecorderRef.current?.stop();
            } catch {
              // ignore
            }
            return;
          }
        } else if (now - startedAt > maxWaitForVoiceMs) {
          try {
            sttRecorderRef.current?.stop();
          } catch {
            // ignore
          }
          return;
        }
        requestAnimationFrame(checkSilence);
      };

      recorder.start(200);
      requestAnimationFrame(checkSilence);
    } catch {
      cleanupSttStream();
    }
  }, [cleanupSttStream, extractErrorMessage]);

  useEffect(() => {
    startServerSttRecordingRef.current = () => {
      void startServerSttRecording();
    };
  }, [startServerSttRecording]);

  const stopServerSttRecording = useCallback(() => {
    stopSttRecorder();
  }, [stopSttRecorder]);

  const startWebSpeechRecognition = useCallback(() => {
    const recognition = speechRecognitionRef.current;
    if (!recognition || speechRecognitionActiveRef.current) return false;
    try {
      recognition.start();
      speechRecognitionActiveRef.current = true;
      return true;
    } catch {
      return false;
    }
  }, []);

  const stopWebSpeechRecognition = useCallback(() => {
    const recognition = speechRecognitionRef.current;
    if (!recognition) return;
    try {
      recognition.stop();
    } catch {
      // ignore
    }
    speechRecognitionActiveRef.current = false;
  }, []);

  useEffect(() => {
    const shouldUseWeb = preferBrowserStt && !!speechRecognitionRef.current;
    const wasUsingWeb = useWebSpeechRef.current;
    useWebSpeechRef.current = shouldUseWeb;

    if (isListeningRef.current) {
      if (shouldUseWeb && !wasUsingWeb) {
        stopServerSttRecording();
        startWebSpeechRecognition();
      } else if (!shouldUseWeb && wasUsingWeb) {
        stopWebSpeechRecognition();
        startServerSttRecordingRef.current();
      }
      return;
    }

    if (!shouldUseWeb && speechRecognitionActiveRef.current) {
      stopWebSpeechRecognition();
    }
  }, [browserSttAvailable, preferBrowserStt, startWebSpeechRecognition, stopServerSttRecording, stopWebSpeechRecognition]);

  const startListening = useCallback(() => {
    if (useWebSpeechRef.current && speechRecognitionRef.current) {
      startWebSpeechRecognition();
      return;
    }
    startServerSttRecordingRef.current();
  }, [startWebSpeechRecognition]);

  const stopListening = useCallback(() => {
    if (useWebSpeechRef.current && speechRecognitionRef.current) {
      stopWebSpeechRecognition();
      return;
    }
    stopServerSttRecording();
  }, [stopServerSttRecording, stopWebSpeechRecognition]);

  const clearTranscriptState = useCallback(() => {
    setInputMessage('');
    inputMessageRef.current = '';
    lastTranscriptRef.current = '';
    finalTranscriptRef.current = '';
    lastAutoSentTranscriptRef.current = '';
    if (interimTranscriptRef.current) {
      interimTranscriptRef.current = '';
      setInterimTranscript('');
    }
  }, []);

  const beginListening = useCallback(() => {
    try {
      clearTranscriptState();
      manualStopListeningRef.current = false;
      isListeningRef.current = true;
      setIsListening(true);
      setIsTranscribing(false);
      startListening();
    } catch {
      isListeningRef.current = false;
      stopListening();
      setIsListening(false);
      alert('Nao foi possivel iniciar o microfone.');
    }
  }, [clearTranscriptState, startListening, stopListening]);

  const endListening = useCallback((manualStop = true) => {
    manualStopListeningRef.current = manualStop;
    isListeningRef.current = false;
    stopListening();
    setIsListening(false);
    setIsTranscribing(false);
    if (interimTranscriptRef.current) {
      interimTranscriptRef.current = '';
      setInterimTranscript('');
    }
  }, [stopListening]);

  const pauseListeningForSend = useCallback(() => {
    if (!isListeningRef.current) return;
    resumeListeningAfterSendRef.current = !pressToTalkRef.current;
    manualStopListeningRef.current = true;
    isListeningRef.current = false;
    stopListeningRef.current();
    setIsListening(false);
    setIsTranscribing(false);
    if (interimTranscriptRef.current) {
      interimTranscriptRef.current = '';
      setInterimTranscript('');
    }
  }, []);

  const resumeListeningAfterSend = useCallback(() => {
    if (!resumeListeningAfterSendRef.current) return;
    if (pressToTalkRef.current) {
      resumeListeningAfterSendRef.current = false;
      return;
    }
    if (!autoSendOnMicEndRef.current) {
      resumeListeningAfterSendRef.current = false;
      return;
    }
    if (isSpeakingRef.current) return;
    resumeListeningAfterSendRef.current = false;
    manualStopListeningRef.current = false;
    isListeningRef.current = true;
    setIsListening(true);
    setTimeout(() => startListeningRef.current(), 150);
  }, []);

  useEffect(() => {
    startListeningRef.current = startListening;
  }, [startListening]);

  useEffect(() => {
    stopListeningRef.current = stopListening;
  }, [stopListening]);

  const startMicRecording = useCallback(async () => {
    if (micRecorderRef.current || typeof window === 'undefined') return;
    if (!navigator.mediaDevices?.getUserMedia) return;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      micStreamRef.current = stream;
      micAudioChunksRef.current = [];
      const recorder = new MediaRecorder(stream);
      micRecorderRef.current = recorder;

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          micAudioChunksRef.current.push(event.data);
        }
      };

      recorder.onstop = async () => {
        const audioBlob = new Blob(micAudioChunksRef.current, { type: 'audio/webm' });
        micAudioChunksRef.current = [];
        micRecorderRef.current = null;
        cleanupMicStream();

        const expectedText = pendingMicExpectedTextRef.current.trim();
        if (expectedText && autoPronunciationOnMicRef.current) {
          try {
            await analyzePronunciationFromBlob(audioBlob, expectedText);
          } catch (error: unknown) {
            alert('Erro ao analisar pronúncia: ' + extractErrorMessage(error));
          }
        }

        if (isListeningRef.current && !manualStopListeningRef.current && autoPronunciationOnMicRef.current) {
          void startMicRecording();
        }
      };

      recorder.start();
    } catch {
      cleanupMicStream();
    }
  }, [analyzePronunciationFromBlob, cleanupMicStream, extractErrorMessage]);

  const startPronunciationRecording = useCallback(async () => {
    if (isRecordingPronunciation) return;
    if (typeof window === 'undefined' || !navigator.mediaDevices?.getUserMedia) {
      alert('Seu navegador não suporta gravação de áudio.');
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      audioChunksRef.current = [];

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      recorder.onstop = async () => {
        setIsRecordingPronunciation(false);
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        try {
          await analyzePronunciationFromBlob(audioBlob, lastUserMessageRef.current || '');
        } catch (error: unknown) {
          alert('Erro ao analisar pronúncia: ' + extractErrorMessage(error));
        }

        stream.getTracks().forEach((track) => track.stop());
      };

      mediaRecorderRef.current = recorder;
      recorder.start();
      setIsRecordingPronunciation(true);
    } catch {
      alert('Não foi possível acessar o microfone.');
    }
  }, [analyzePronunciationFromBlob, extractErrorMessage, isRecordingPronunciation]);

  const stopPronunciationRecording = useCallback(() => {
    const recorder = mediaRecorderRef.current;
    if (!recorder) return;
    if (recorder.state !== 'inactive') {
      recorder.stop();
    }
  }, []);

  const loadVoices = async () => {
    try {
      const response = await conversationApi.getVoices();
      const voiceList = (response.data.voices || []) as Voice[];
      setVoices(voiceList);
      if (voiceList.length > 0) {
        const preferredVoiceId = 'nova'; // OpenAI TTS default
        const preferred = voiceList.find((v) => v.voice_id === preferredVoiceId);
        setSelectedVoice((preferred ?? voiceList[0]).voice_id);
      }
    } catch (error: unknown) {
      console.error('Erro ao carregar vozes:', error);
    }
  };

  const startConversation = async () => {
    try {
      if (lessonMode) {
        await startLesson();
        return;
      }

      setLessonActive(false);
      setLessonFinalFeedback('');
      setPronunciationFeedback('');
      setPronunciationMeta(null);
      lastUserMessageRef.current = '';

      setIsLoading(true);
      const response = await conversationApi.startConversation({
        system_prompt: systemPrompt,
        initial_message: 'Hello! I would like to practice my English.'
      });

      setConversationId(response.data.conversation_id);

      // Adiciona mensagem inicial
      setMessages([
        {
          id: '1',
          role: 'user',
          content: 'Hello! I would like to practice my English.',
          timestamp: new Date()
        }
      ]);
      manualStopListeningRef.current = true;
      isListeningRef.current = false;
      setIsListening(false);

      setIsConfigOpen(false);
    } catch (error: unknown) {
      alert('Erro ao iniciar conversação: ' + extractErrorMessage(error));
    } finally {
      setIsLoading(false);
    }
  };


  const sendMessage = useCallback(async (overrideMessage?: string) => {
    if (isLoadingRef.current) return;

    const userMessage = (overrideMessage ?? inputMessageRef.current).trim();
    if (!userMessage) return;

    pauseListeningForSend();
    inputMessageRef.current = '';
    lastTranscriptRef.current = '';
    finalTranscriptRef.current = '';
    lastAutoSentTranscriptRef.current = '';
    setInputMessage('');
    if (interimTranscriptRef.current) {
      interimTranscriptRef.current = '';
      setInterimTranscript('');
    }
    isLoadingRef.current = true;
    setIsLoading(true);

    let activeConversationId: string | null = conversationIdRef.current;

    if (!activeConversationId && !lessonMode) {
      try {
        activeConversationId = await ensureConversationStarted();
      } catch (error: unknown) {
        isLoadingRef.current = false;
        setIsLoading(false);
        alert('Erro ao iniciar conversação: ' + extractErrorMessage(error));
        return;
      }
    }

    // Adiciona mensagem do usuário
    const userMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: userMessage,
      timestamp: new Date()
    };
    setMessages(prev => [...prev, userMsg]);
    lastUserMessageRef.current = userMessage;
    setPronunciationFeedback('');
    setPronunciationMeta(null);

    try {
      if (lessonActive && activeConversationId) {
        const response = await conversationApi.sendLessonMessage(activeConversationId, {
          message: userMessage
        });

        const aiMsg: Message = {
          id: Date.now().toString(),
          role: 'assistant',
          content: response.data.ai_response,
          timestamp: new Date()
        };
        setMessages(prev => [...prev, aiMsg]);

        if (response.data.is_final) {
          setLessonFinalFeedback(response.data.ai_response);
          setLessonActive(false);
        } else if (response.data.next_question) {
          setLessonCurrentIndex(response.data.current_index as number);
        }

        if (autoPlay) {
          void playTextAsAudio(response.data.ai_response);
        }
      } else {
        if (!activeConversationId) {
          throw new Error('Conversação não iniciada');
        }

        const response = await conversationApi.sendMessage(activeConversationId, {
          message: userMessage
        });

        const aiMsg: Message = {
          id: response.data.message_id,
          role: 'assistant',
          content: response.data.ai_response,
          audio_url: response.data.audio_url,
          timestamp: new Date(response.data.timestamp)
        };

        setMessages(prev => [...prev, aiMsg]);

        if (autoPlay) {
          void playTextAsAudio(response.data.ai_response);
        }
      }

    } catch (error: unknown) {
      alert('Erro ao enviar mensagem: ' + extractErrorMessage(error));
      console.error('Erro:', error);
    } finally {
      isLoadingRef.current = false;
      setIsLoading(false);
      resumeListeningAfterSend();
    }
  }, [autoPlay, ensureConversationStarted, extractErrorMessage, lessonActive, lessonMode, pauseListeningForSend, playTextAsAudio, resumeListeningAfterSend]);

  useEffect(() => {
    sendMessageRef.current = sendMessage;
  }, [sendMessage]);

  useEffect(() => {
    if (lessonFinalFeedback) {
      void loadLessonAttempts();
    }
  }, [lessonFinalFeedback, loadLessonAttempts]);

  const handleMicPointerDown = useCallback((event: ReactPointerEvent<HTMLButtonElement>) => {
    if (!pressToTalk) return;
    event.preventDefault();
    try {
      event.currentTarget.setPointerCapture(event.pointerId);
    } catch {
      // ignore
    }
    resumeListeningAfterSendRef.current = false;
    if (isListeningRef.current) return;
    beginListening();
  }, [beginListening, pressToTalk]);

  const handleMicPointerUp = useCallback((event: ReactPointerEvent<HTMLButtonElement>) => {
    if (!pressToTalk) return;
    event.preventDefault();
    try {
      event.currentTarget.releasePointerCapture(event.pointerId);
    } catch {
      // ignore
    }
    if (!isListeningRef.current) return;
    endListening(true);
  }, [endListening, pressToTalk]);

  const toggleListening = () => {
    resumeListeningAfterSendRef.current = false;
    if (isListening) {
      endListening(true);
      return;
    }
    beginListening();
  };

  const endConversation = async () => {
    if (!conversationId) return;

    try {
      await conversationApi.endConversation(conversationId);
      setConversationId(null);
      setMessages([]);
      setLessonActive(false);
      setLessonFinalFeedback('');
      setPronunciationFeedback('');
      setPronunciationMeta(null);
      lastUserMessageRef.current = '';
      alert('Conversação encerrada!');
    } catch (error) {
      console.error('Erro ao encerrar conversação:', error);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800">
      <div className="container mx-auto px-4 py-8 max-w-6xl">
        {/* Header */}
        <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl p-6 mb-6">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div>
              <h1 className="text-2xl sm:text-3xl font-bold text-gray-800 dark:text-white mb-2">
                🎙️ AI Conversation Practice
              </h1>
              <p className="text-gray-600 dark:text-gray-300">
                Pratique inglês com conversação full-time usando IA
              </p>
            </div>
            <div className="flex flex-wrap gap-2 w-full md:w-auto">
              <Link
                href="/dashboard"
                className="w-full sm:w-auto px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-white rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600"
              >
                ← Dashboard
              </Link>
              <button
                onClick={() => setIsConfigOpen(!isConfigOpen)}
                className="w-full sm:w-auto px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-white rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600"
              >
                ⚙️ Config
              </button>
              {conversationId && (
                <button
                  onClick={endConversation}
                  className="w-full sm:w-auto px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600"
                >
                  🛑 Encerrar
                </button>
              )}
            </div>
          </div>

          {/* Configurações */}
          {isConfigOpen && (
            <div className="mt-6 p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
              <h3 className="font-bold mb-3">Configurações</h3>
              
              <div className="mb-4">
                <label htmlFor="voiceSelect" className="block mb-2 font-medium">Voice:</label>
                <select
                  id="voiceSelect"
                  value={selectedVoice}
                  onChange={(e) => setSelectedVoice(e.target.value)}
                  aria-label="Voice"
                  className="w-full p-2 border rounded-lg dark:bg-gray-600 dark:border-gray-500"
                >
                  {voices.map(voice => (
                    <option key={voice.voice_id} value={voice.voice_id}>
                      {voice.name}
                    </option>
                  ))}
                </select>
              </div>

              <div className="mb-4">
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={autoPlay}
                    onChange={(e) => setAutoPlay(e.target.checked)}
                    className="w-4 h-4"
                  />
                  <span>Auto-play respostas em áudio</span>
                </label>
              </div>

              <div className="mb-4">
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={autoSendOnMicEnd}
                    onChange={(e) => setAutoSendOnMicEnd(e.target.checked)}
                    className="w-4 h-4"
                  />
                  <span>Auto-enviar ao terminar de falar (microfone)</span>
                </label>
                <p className="text-xs text-gray-600 dark:text-gray-300 mt-1">
                  Desative para treinar a frase com calma: o microfone só preenche o campo, e você envia quando quiser.
                </p>
              </div>

              <div className="mb-4">
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={preferBrowserStt}
                    onChange={(e) => setPreferBrowserStt(e.target.checked)}
                    className="w-4 h-4"
                    disabled={!browserSttAvailable}
                  />
                  <span>Usar reconhecimento do navegador quando disponivel</span>
                </label>
                {!browserSttAvailable && (
                  <p className="text-xs text-gray-600 dark:text-gray-300 mt-1">
                    Seu navegador nao suporta Web Speech. Usando STT do servidor.
                  </p>
                )}
              </div>

              <div className="mb-4">
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={pressToTalk}
                    onChange={(e) => setPressToTalk(e.target.checked)}
                    className="w-4 h-4"
                  />
                  <span>Segurar para falar (push-to-talk)</span>
                </label>
                <p className="text-xs text-gray-600 dark:text-gray-300 mt-1">
                  Recomendado no celular para evitar transcricoes acidentais.
                </p>
              </div>

              <div className="mb-4">
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={showInterimTranscript}
                    onChange={(e) => setShowInterimTranscript(e.target.checked)}
                    className="w-4 h-4"
                  />
                  <span>Mostrar rascunho do microfone (pode oscilar)</span>
                </label>
                <p className="text-xs text-gray-600 dark:text-gray-300 mt-1">
                  Desative para ver apenas o texto final.
                </p>
              </div>

              <div className="mb-4">
                <label className="flex items-center gap-2">
                  <span className="font-medium">Microfone (STT via servidor)</span>
                </label>
                <p className="text-xs text-gray-600 dark:text-gray-300 mt-1">
                  Envia o áudio para o backend e usa STT em nuvem (Lemonfox). Requer LEMONFOX_API_KEY.
                </p>
              </div>

              <div className="mb-4">
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={autoPronunciationOnMic}
                    onChange={(e) => setAutoPronunciationOnMic(e.target.checked)}
                    className="w-4 h-4"
                  />
                  <span>Avaliar pronúncia automaticamente ao falar no microfone</span>
                </label>
                <p className="text-xs text-gray-600 dark:text-gray-300 mt-1">
                  A avaliação aparece no chat após a sua fala.
                </p>
              </div>

              <div className="mb-4">
                <label htmlFor="systemPrompt" className="block mb-2 font-medium">System Prompt (Personalidade da IA):</label>
                <textarea
                  id="systemPrompt"
                  aria-label="System Prompt"
                  title="System Prompt"
                  value={systemPrompt}
                  onChange={(e) => setSystemPrompt(e.target.value)}
                  className="w-full p-2 border rounded-lg h-24 dark:bg-gray-600 dark:border-gray-500"
                  disabled={!!conversationId}
                />
              </div>

              <div className="mb-4">
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={lessonMode}
                    onChange={(e) => setLessonMode(e.target.checked)}
                    className="w-4 h-4"
                  />
                  <span>Modo Lição (perguntas fixas)</span>
                </label>
              </div>

              {lessonMode && (
                <div className="space-y-4">
                  <div>
                    <label htmlFor="lessonTopic" className="block mb-2 font-medium">Tema da lição (opcional):</label>
                    <input
                      id="lessonTopic"
                      aria-label="Tema da lição"
                      value={lessonTopic}
                      onChange={(e) => setLessonTopic(e.target.value)}
                      className="w-full p-2 border rounded-lg dark:bg-gray-600 dark:border-gray-500"
                      disabled={lessonActive}
                      placeholder="Ex: job interview, travel, daily routine"
                    />
                  </div>
                  <div>
                    <label htmlFor="lessonNumQuestions" className="block mb-2 font-medium">Quantidade de perguntas:</label>
                    <input
                      id="lessonNumQuestions"
                      aria-label="Quantidade de perguntas"
                      type="number"
                      min={3}
                      max={15}
                      value={lessonNumQuestions}
                      onChange={(e) => {
                        const value = Number(e.target.value);
                        setLessonNumQuestions(Number.isFinite(value) ? value : 10);
                      }}
                      className="w-full p-2 border rounded-lg dark:bg-gray-600 dark:border-gray-500"
                      disabled={lessonActive}
                    />
                    <button
                      onClick={generateLessonQuestions}
                      disabled={lessonActive || isGeneratingLesson}
                      className="mt-2 px-4 py-2 rounded-lg bg-indigo-500 text-white hover:bg-indigo-600 disabled:opacity-50"
                    >
                      {isGeneratingLesson ? 'Gerando...' : 'Gerar perguntas'}
                    </button>
                  </div>
                  <div>
                    <label htmlFor="lessonQuestions" className="block mb-2 font-medium">Perguntas (1 por linha):</label>
                    <textarea
                      id="lessonQuestions"
                      aria-label="Perguntas da lição"
                      value={lessonQuestionsText}
                      onChange={(e) => setLessonQuestionsText(e.target.value)}
                      className="w-full p-2 border rounded-lg h-28 dark:bg-gray-600 dark:border-gray-500"
                      disabled={lessonActive}
                      placeholder="Ex: What did you do today?\nWhat are your plans for tomorrow?"
                    />
                  </div>
                  <div>
                    <label htmlFor="lessonNativeLanguage" className="block mb-2 font-medium">Língua nativa (feedback final):</label>
                    <input
                      id="lessonNativeLanguage"
                      aria-label="Língua nativa"
                      value={lessonNativeLanguage}
                      onChange={(e) => setLessonNativeLanguage(e.target.value)}
                      className="w-full p-2 border rounded-lg dark:bg-gray-600 dark:border-gray-500"
                      disabled={lessonActive}
                      placeholder="pt-BR"
                    />
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Chat Area */}
        <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl overflow-hidden flex flex-col min-h-[420px] sm:min-h-[520px]">
          {/* Messages / Intro */}
          <div className="flex-1 min-h-[260px] max-h-[420px] overflow-y-auto p-6 space-y-4">
            {lessonMode && conversationId && (
              <div className="p-3 rounded-xl bg-amber-50 dark:bg-amber-900 text-gray-800 dark:text-white">
                <div className="font-semibold">Modo Lição</div>
                <div className="text-sm">
                  Pergunta {lessonCurrentIndex + 1} de {lessonTotalQuestions || 0}
                </div>
              </div>
            )}
            {!conversationId ? (
              <div className="h-full flex items-center justify-center">
                <div className="text-center">
                  <div className="text-6xl mb-4">🎯</div>
                  <h2 className="text-2xl font-bold mb-4">Iniciar Conversação</h2>
                  <p className="text-gray-600 dark:text-gray-400 mb-6">
                    Você pode clicar em “Iniciar” ou falar no microfone. Se “Auto-enviar” estiver ligado, ao terminar de falar a mensagem é enviada automaticamente.
                    {lessonMode && ' No modo lição, a IA usará as perguntas fixas e dará feedback apenas no final.'}
                  </p>
                  <button
                    onClick={startConversation}
                    disabled={isLoading}
                    className="px-8 py-4 bg-gradient-to-r from-blue-500 to-indigo-600 text-white rounded-xl font-bold text-lg hover:from-blue-600 hover:to-indigo-700 disabled:opacity-50 shadow-lg"
                  >
                    {isLoading ? '⏳ Iniciando...' : lessonMode ? '🚀 Iniciar Lição' : '🚀 Iniciar Conversação'}
                  </button>
                </div>
              </div>
            ) : (
              <>
                {messages.map((message) => (
                  <div
                    key={message.id}
                    className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`max-w-[85%] sm:max-w-[70%] rounded-2xl p-4 ${
                        message.role === 'user'
                          ? 'bg-blue-500 text-white'
                          : 'bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-white'
                      }`}
                    >
                      <div className="flex items-start gap-2">
                        <div className="flex-1">
                          <p className="whitespace-pre-wrap break-words">{message.content}</p>
                          <p className="text-xs mt-2 opacity-70">
                            {message.timestamp.toLocaleTimeString()}
                          </p>
                        </div>
                        {message.role === 'assistant' && (
                          <button
                            onClick={() => playTextAsAudio(message.content)}
                            className="flex-shrink-0 p-2 hover:bg-gray-300 dark:hover:bg-gray-600 rounded-full"
                            title="Reproduzir áudio"
                          >
                            🔊
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                ))}

                {isLoading && (
                  <div className="flex justify-start">
                    <div className="bg-gray-200 dark:bg-gray-700 rounded-2xl p-4">
                      <div className="flex gap-2">
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:200ms]"></div>
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:400ms]"></div>
                      </div>
                    </div>
                  </div>
                )}

                {pronunciationFeedback && (
                  <div className="flex justify-start">
                    <div className="bg-emerald-50 dark:bg-emerald-900 text-gray-800 dark:text-white rounded-2xl p-4 max-w-[80%]">
                      <div className="font-semibold mb-1">Feedback de pronúncia</div>
                      {pronunciationMeta && (
                        <div className="text-xs mb-2 text-gray-700 dark:text-gray-200">
                          <div><strong>Texto esperado:</strong> {pronunciationMeta.expectedText || '—'}</div>
                          <div><strong>Transcrição:</strong> {pronunciationMeta.transcript || '—'}</div>
                          <div><strong>Similaridade:</strong> {pronunciationMeta.similarity ?? '—'}%</div>
                        </div>
                      )}
                      <div className="whitespace-pre-wrap text-sm">{pronunciationFeedback}</div>
                    </div>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </>
            )}
          </div>

          {/* Input Area (sempre visível) */}
          <div className="border-t dark:border-gray-700 p-4 bg-gray-50 dark:bg-gray-900">
            <div className="flex flex-col sm:flex-row gap-2">
              <label htmlFor="messageInput" className="sr-only">Mensagem</label>
              <textarea
                id="messageInput"
                aria-label="Mensagem"
                title="Mensagem"
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder={lessonMode && !lessonActive
                  ? "Inicie a lição para responder às perguntas..."
                  : "Digite sua mensagem... (Enter para enviar — microfone pode auto-enviar ao terminar de falar)"
                }
                className="w-full sm:flex-1 p-3 border rounded-xl resize-none dark:bg-gray-800 dark:border-gray-600 dark:text-white"
                rows={2}
                disabled={isLoading}
              />
              <button
                onClick={pressToTalk ? undefined : toggleListening}
                onPointerDown={handleMicPointerDown}
                onPointerUp={handleMicPointerUp}
                onPointerLeave={handleMicPointerUp}
                onPointerCancel={handleMicPointerUp}
                disabled={isLoading}
                className={`w-full sm:w-auto px-4 py-3 rounded-xl font-bold disabled:opacity-50 disabled:cursor-not-allowed ${
                  isListening
                    ? 'bg-red-500 text-white hover:bg-red-600'
                    : 'bg-gray-200 text-gray-900 hover:bg-gray-300 dark:bg-gray-700 dark:text-white dark:hover:bg-gray-600'
                }`}
                title={
                  pressToTalk
                    ? isListening
                      ? 'Solte para parar'
                      : 'Segure para falar'
                    : isListening
                      ? 'Parar microfone'
                      : 'Falar (microfone)'
                }
              >
                {isListening ? '????' : '????'}
              </button>
              <button
                onClick={() => sendMessage()}
                disabled={isLoading || !inputMessage.trim() || (lessonMode && !lessonActive)}
                className="w-full sm:w-auto px-6 py-3 bg-blue-500 text-white rounded-xl font-bold hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading ? '⏳' : '📤'}
              </button>
              <button
                onClick={isRecordingPronunciation ? stopPronunciationRecording : startPronunciationRecording}
                disabled={isLoading || !lastUserMessageRef.current}
                className={`w-full sm:w-auto px-4 py-3 rounded-xl font-bold disabled:opacity-50 disabled:cursor-not-allowed ${
                  isRecordingPronunciation
                    ? 'bg-red-500 text-white hover:bg-red-600'
                    : 'bg-emerald-500 text-white hover:bg-emerald-600'
                }`}
                title="Avaliar pronúncia da última resposta enviada"
              >
                {isRecordingPronunciation ? '🎙️' : '🗣️ Pronúncia'}
              </button>
            </div>

            {isListening && (
              <div className="mt-2 text-sm text-red-600 dark:text-red-400">
                🎤 Ouvindo... {pressToTalk ? 'solte para parar.' : 'clique no microfone para parar.'}
              </div>
            )}
            {showInterimTranscript && interimTranscript && (
              <div className="mt-2 text-sm text-gray-600 dark:text-gray-300 italic">
                Rascunho: {interimTranscript}
              </div>
            )}

            {isTranscribing && !isListening && (
              <div className="mt-2 text-sm text-amber-600 dark:text-amber-400">
                📝 Transcrevendo áudio...
              </div>
            )}
            {isSpeaking && (
              <div className="mt-2 text-sm text-blue-600 dark:text-blue-400">
                🔊 Reproduzindo áudio...
              </div>
            )}
          </div>
        </div>

        {lessonFinalFeedback && (
          <div className="mt-4">
            <div className="rounded-xl bg-emerald-50 dark:bg-emerald-900 text-gray-900 dark:text-white p-4">
              <div className="font-semibold mb-2">Resultado final da lição</div>
              <div className="whitespace-pre-wrap text-sm">{lessonFinalFeedback}</div>
            </div>
          </div>
        )}

        {lessonAttempts.length > 0 && (
          <div className="mt-4">
            <div className="rounded-xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 p-4">
              <div
                className="flex items-center justify-between cursor-pointer"
                onClick={() => setIsHistoryOpen((prev) => !prev)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    setIsHistoryOpen((prev) => !prev);
                  }
                }}
              >
                <div className="font-semibold">
                  Histórico de lições recentes ({lessonAttempts.length})
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      loadLessonAttempts();
                    }}
                    disabled={isLoadingAttempts}
                    className="text-sm px-3 py-1 rounded-lg bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 disabled:opacity-50"
                  >
                    {isLoadingAttempts ? 'Atualizando...' : 'Atualizar'}
                  </button>
                  <span className="text-gray-500">{isHistoryOpen ? '▾' : '▸'}</span>
                </div>
              </div>
              {isHistoryOpen && (
                <div className="space-y-3 mt-3">
                  {lessonAttempts.map((attempt) => (
                    <div key={attempt.id} className="rounded-lg border border-gray-100 dark:border-gray-700 p-3">
                      <div className="text-xs text-gray-500 mb-2">{new Date(attempt.created_at).toLocaleString()}</div>
                      <div className="text-sm">
                        <strong>Perguntas:</strong> {attempt.questions.length} | <strong>Respostas:</strong> {attempt.answers.length}
                      </div>
                      {(attempt.topic || attempt.num_questions) && (
                        <div className="text-xs text-gray-500 mt-1">
                          {attempt.topic ? `Tema: ${attempt.topic}` : ''}
                          {attempt.topic && attempt.num_questions ? ' • ' : ''}
                          {attempt.num_questions ? `Planejado: ${attempt.num_questions}` : ''}
                        </div>
                      )}
                      {typeof attempt.score === 'number' && (
                        <div className="text-xs text-emerald-600 dark:text-emerald-300 mt-1">
                          Nota final: {attempt.score}
                        </div>
                      )}
                      <button
                        onClick={() => {
                          toggleAttemptExpanded(attempt.id);
                          void loadLessonAttemptDetails(attempt.id);
                        }}
                        className="mt-2 text-sm text-blue-600 dark:text-blue-300 hover:underline"
                      >
                        {expandedAttemptIds.includes(attempt.id) ? 'Ocultar detalhes' : 'Ver detalhes'}
                      </button>
                      {expandedAttemptIds.includes(attempt.id) && (
                        <div className="mt-3 space-y-3 text-sm">
                          {attempt.questions.map((question, index) => (
                            <div key={`${attempt.id}-qa-${index}`} className="rounded-lg bg-gray-50 dark:bg-gray-700 p-3">
                              <div className="font-semibold">Q{index + 1}:</div>
                              <div className="whitespace-pre-wrap">{question}</div>
                              <div className="mt-2 text-gray-700 dark:text-gray-200">
                                <div className="font-semibold">Resposta:</div>
                                <div className="whitespace-pre-wrap">{attempt.answers[index] || ''}</div>
                              </div>
                              {pronunciationByAttempt[attempt.id] && (
                                <div className="mt-3 rounded-lg bg-emerald-50 dark:bg-emerald-900 p-3">
                                  <div className="font-semibold">Pronúncia</div>
                                  {pronunciationByAttempt[attempt.id]
                                    .filter((p) => (p.question_index ?? -1) === index)
                                    .map((p, idx) => (
                                      <div key={`${attempt.id}-p-${index}-${idx}`} className="mt-2">
                                        <div className="text-xs text-gray-600 dark:text-gray-300">
                                          Similaridade: {p.similarity ?? '—'}%
                                        </div>
                                        <div className="whitespace-pre-wrap">{p.feedback}</div>
                                      </div>
                                    ))}
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                      {attempt.ai_feedback && (
                        <div className="text-sm mt-2 whitespace-pre-wrap text-gray-700 dark:text-gray-200">
                          {attempt.ai_feedback}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Audio Player (hidden) */}
        <audio
          ref={audioRef}
          onEnded={() => {
            cleanupCurrentAudioUrl();
            isSpeakingRef.current = false;
            setIsSpeaking(false);
            if (resumeListeningAfterSendRef.current && autoSendOnMicEndRef.current && !pressToTalkRef.current) {
              resumeListeningAfterSendRef.current = false;
              manualStopListeningRef.current = false;
              isListeningRef.current = true;
              setIsListening(true);
              startListening();
              return;
            }
            if (isListeningRef.current && !manualStopListeningRef.current) {
              startListening();
            }
          }}
          onError={() => {
            cleanupCurrentAudioUrl();
            isSpeakingRef.current = false;
            setIsSpeaking(false);
            if (resumeListeningAfterSendRef.current && autoSendOnMicEndRef.current && !pressToTalkRef.current) {
              resumeListeningAfterSendRef.current = false;
              manualStopListeningRef.current = false;
              isListeningRef.current = true;
              setIsListening(true);
              startListening();
            }
          }}
        />
      </div>
    </div>
  );
}
