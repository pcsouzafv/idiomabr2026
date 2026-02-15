import os
import json
import hashlib
import io
import re
import math
import asyncio
from difflib import SequenceMatcher
from typing import Optional, Dict, Any, List, Tuple
import httpx
from openai import OpenAI, OpenAIError

from sqlalchemy.orm import Session
from sqlalchemy import update

from app.models.ai_cache import AICacheEntry
from app.services.ai_usage_tracking import parse_usage_tokens, parse_model_name, track_ai_usage


class AITeacherService:
    """
    Serviço de professor de IA com integração OpenAI e fallback para Ollama.
    Usa RAG para buscar contexto relevante do banco de dados.
    """

    @staticmethod
    def _normalize_tts_speed(value: Any, default: float = 0.88) -> float:
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            parsed = float(default)

        if not math.isfinite(parsed):
            parsed = float(default)

        # Faixa pensada para estudo: evita extremos muito lentos/rápidos.
        bounded = max(0.65, min(1.05, parsed))
        return round(bounded, 2)

    @staticmethod
    def _clamp_float(value: Any, default: float, *, min_value: float, max_value: float) -> float:
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            parsed = float(default)

        if not math.isfinite(parsed):
            parsed = float(default)

        return max(min_value, min(max_value, parsed))

    @staticmethod
    def _clamp_int(value: Any, default: int, *, min_value: int, max_value: int) -> int:
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            parsed = int(default)
        return max(min_value, min(max_value, parsed))

    def __init__(self):
        self.deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.lemonfox_api_key = os.getenv("LEMONFOX_API_KEY")
        self.lemonfox_base_url = os.getenv("LEMONFOX_BASE_URL", "https://api.lemonfox.ai/v1")
        self.lemonfox_enabled = os.getenv("LEMONFOX_ENABLED", "false").lower() == "true"
        self.tts_speed = self._normalize_tts_speed(os.getenv("OPENAI_TTS_SPEED", "0.88"), default=0.88)
        self.ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
        self.use_ollama_fallback = os.getenv("USE_OLLAMA_FALLBACK", "false").lower() == "true"
        self.ai_chat_timeout_seconds = self._clamp_float(
            os.getenv("AI_TEACHER_CHAT_TIMEOUT_SECONDS", "18"),
            default=18.0,
            min_value=5.0,
            max_value=120.0,
        )
        self.ai_chat_max_retries = self._clamp_int(
            os.getenv("AI_TEACHER_CHAT_MAX_RETRIES", "0"),
            default=0,
            min_value=0,
            max_value=3,
        )
        self.ai_chat_temperature = self._clamp_float(
            os.getenv("AI_TEACHER_CHAT_TEMPERATURE", "0.55"),
            default=0.55,
            min_value=0.0,
            max_value=1.2,
        )
        self.openai_chat_model = os.getenv("AI_TEACHER_OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"
        self.deepseek_chat_model = os.getenv("AI_TEACHER_DEEPSEEK_MODEL", "deepseek-chat").strip() or "deepseek-chat"
        self.openai_chat_max_tokens = self._clamp_int(
            os.getenv("AI_TEACHER_OPENAI_MAX_TOKENS", "550"),
            default=550,
            min_value=150,
            max_value=1800,
        )
        self.deepseek_chat_max_tokens = self._clamp_int(
            os.getenv("AI_TEACHER_DEEPSEEK_MAX_TOKENS", "700"),
            default=700,
            min_value=150,
            max_value=2200,
        )

        print(f"[INIT] DeepSeek API Key: {'SET' if self.deepseek_api_key else 'NOT SET'}")
        print(f"[INIT] OpenAI API Key: {'SET' if self.openai_api_key else 'NOT SET'}")
        print(f"[INIT] Lemonfox API Key: {'SET' if self.lemonfox_api_key else 'NOT SET'}")
        print(f"[INIT] Lemonfox enabled: {self.lemonfox_enabled}")
        print(f"[INIT] TTS speed: {self.tts_speed}")
        print(f"[INIT] Ollama fallback: {self.use_ollama_fallback}")
        print(f"[INIT] AI chat timeout: {self.ai_chat_timeout_seconds}s")
        print(f"[INIT] AI chat retries: {self.ai_chat_max_retries}")
        print(f"[INIT] AI chat temperature: {self.ai_chat_temperature}")
        print(f"[INIT] AI chat models: openai={self.openai_chat_model}, deepseek={self.deepseek_chat_model}")

        # Inicializar clientes
        self.deepseek_client = None
        self.openai_client = None
        self.openai_chat_client = None

        if self.deepseek_api_key:
            print("[INIT] Initializing DeepSeek client...")
            self.deepseek_client = OpenAI(
                api_key=self.deepseek_api_key,
                base_url="https://api.deepseek.com",
                max_retries=self.ai_chat_max_retries,
            )
            print("[INIT] DeepSeek client initialized!")

        if self.openai_api_key:
            self.openai_client = OpenAI(api_key=self.openai_api_key)
            self.openai_chat_client = OpenAI(
                api_key=self.openai_api_key,
                max_retries=self.ai_chat_max_retries,
            )

    def _build_system_prompt(self) -> str:
        """Constrói o prompt do sistema para o professor de IA"""
        return """You are Sarah, an experienced and enthusiastic English teacher in a virtual classroom, helping Brazilian Portuguese speakers learn English through natural conversation.

Your teaching personality:
- Warm, patient, and genuinely excited about teaching
- Celebrate every small victory and progress
- Create a safe, judgment-free learning environment
- Use real-world examples and situations
- Make learning fun and engaging

Your teaching methodology (IMPORTANT):
1. Start with encouragement and context about the sentence
2. ASK questions instead of just explaining (Socratic method)
3. Wait for student responses and build on them
4. Use the sentence as a starting point for natural conversation
5. Guide students to discover answers themselves
6. Always end interactions with motivation and next steps

Conversation structure:
- Begin: "Ótima escolha! Essa frase é muito útil. Vamos explorar juntos?"
- Question 1: Ask about vocabulary or context
- Question 2: Ask about grammar or usage
- Question 3: Ask them to use it in a real situation
- Always praise attempts: "Muito bem!", "Excelente!", "Você está progredindo!"
- End with: Practical tip + Encouragement + Next step suggestion

Response format:
- Start with warm greeting and encouragement
- Ask 1-2 engaging questions about the sentence
- Provide clear, simple explanations in Portuguese
- Include 2-3 practical examples
- End with motivation and a challenge/practice suggestion

Remember: You're not a dictionary - you're an interactive teacher building confidence!

Always respond in Portuguese unless the student practices in English."""

    def _prompt_version(self) -> str:
        # Any change in the system prompt should naturally bust cache.
        system_prompt = self._build_system_prompt()
        return hashlib.sha256(system_prompt.encode("utf-8")).hexdigest()[:16]

    def _stable_json(self, obj: Any) -> str:
        return json.dumps(
            obj,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
            default=str,
        )

    def _make_cache_key(self, *, operation: str, scope: str, payload: Any) -> str:
        raw = f"v={self._prompt_version()}|op={operation}|scope={scope}|payload={self._stable_json(payload)}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _get_cache_entry(self, db: Session, cache_key: str) -> Optional[AICacheEntry]:
        return db.query(AICacheEntry).filter(AICacheEntry.cache_key == cache_key).first()

    def _touch_cache_hit(self, db: Session, entry_id: int) -> None:
        db.execute(update(AICacheEntry).where(AICacheEntry.id == entry_id).values(hit_count=AICacheEntry.hit_count + 1))

    def _store_cache_entry(
        self,
        db: Session,
        *,
        cache_key: str,
        scope: str,
        operation: str,
        provider: Optional[str],
        model: Optional[str],
        request_json: Any,
        response_text: Optional[str] = None,
        response_json: Any = None,
        response_bytes: Optional[bytes] = None,
        status: str = "ok",
        error: Optional[str] = None,
    ) -> None:
        entry = AICacheEntry(
            cache_key=cache_key,
            scope=scope,
            operation=operation,
            provider=provider,
            model=model,
            request_json=request_json,
            response_text=response_text,
            response_json=response_json,
            response_bytes=response_bytes,
            status=status,
            error=error,
        )
        db.add(entry)

    def _extract_user_id_from_scope(self, scope: str) -> Optional[int]:
        if not scope:
            return None
        if not scope.startswith("user:"):
            return None
        raw = scope.split(":", 1)[1].strip()
        if not raw:
            return None
        try:
            value = int(raw)
            return value if value > 0 else None
        except (TypeError, ValueError):
            return None

    def _track_usage_if_possible(
        self,
        *,
        db: Optional[Session],
        scope: str,
        operation: str,
        provider: str,
        model: Optional[str],
        usage: Optional[Dict[str, int]],
    ) -> None:
        if db is None:
            return
        if not usage:
            return
        prompt_tokens = int(usage.get("prompt_tokens") or 0)
        completion_tokens = int(usage.get("completion_tokens") or 0)
        total_tokens = int(usage.get("total_tokens") or 0)
        if total_tokens <= 0 and prompt_tokens <= 0 and completion_tokens <= 0:
            return

        track_ai_usage(
            db,
            user_id=self._extract_user_id_from_scope(scope),
            provider=provider,
            operation=operation,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cached=False,
        )

    def _build_context_prompt(self, context: Optional[Dict[str, Any]]) -> str:
        """Constrói o contexto adicional baseado nos dados do RAG"""
        if not context:
            return ""

        prompt_parts = ["\n\n**Contexto relevante:**\n"]

        if context.get("sentence"):
            sent = context["sentence"]
            prompt_parts.append(f"**Frase em estudo:**")
            prompt_parts.append(f"EN: {sent.get('english')}")
            prompt_parts.append(f"PT: {sent.get('portuguese')}")
            prompt_parts.append(f"Nível: {sent.get('level')}")

            if sent.get("grammar_points"):
                prompt_parts.append(f"Pontos gramaticais: {sent.get('grammar_points')}")

        if context.get("related_vocabulary"):
            prompt_parts.append(f"\n**Vocabulário relacionado:**")
            for word in context["related_vocabulary"][:5]:
                prompt_parts.append(f"- {word.get('english')} = {word.get('portuguese')}")

        if context.get("user_stats"):
            stats = context["user_stats"]
            prompt_parts.append(f"\n**Progresso do aluno:**")
            prompt_parts.append(f"- Palavras aprendidas: {stats.get('total_words_learned', 0)}")
            prompt_parts.append(f"- Nível estimado: {stats.get('estimated_level', 'A1')}")

        return "\n".join(prompt_parts)

    async def get_ai_response(
        self,
        user_message: str,
        context: Optional[Dict[str, Any]] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        db: Optional[Session] = None,
        cache_operation: str = "chat",
        cache_scope: str = "global",
    ) -> Dict[str, Any]:
        """
        Obtém resposta do professor de IA.
        Ordem: OpenAI (principal) → DeepSeek → Ollama (fallback opcional).
        """

        # Construir mensagens
        messages = [
            {"role": "system", "content": self._build_system_prompt()}
        ]

        # Adicionar contexto se disponível
        if context:
            context_prompt = self._build_context_prompt(context)
            if context_prompt:
                messages.append({"role": "system", "content": context_prompt})

        # Adicionar histórico de conversa
        if conversation_history:
            messages.extend(conversation_history)

        # Adicionar mensagem do usuário
        messages.append({"role": "user", "content": user_message})

        # Cache lookup (safe default: scope-aware; caller can set scope=user:{id})
        if db is not None:
            cache_payload = {
                "messages": messages,
                "operation": cache_operation,
            }
            cache_key = self._make_cache_key(operation=cache_operation, scope=cache_scope, payload=cache_payload)
            cached = self._get_cache_entry(db, cache_key)
            if cached and cached.status == "ok" and (cached.response_text is not None or cached.response_json is not None):
                self._touch_cache_hit(db, cached.id)
                db.commit()
                return {
                    "response": cached.response_text or "",
                    "model_used": cached.provider or "cache",
                    "context_used": context,
                    "cached": True,
                }

        # 1) OpenAI (principal)
        if self.openai_chat_client:
            try:
                openai_result = await self._get_openai_response(messages)
                response_text = openai_result["text"]
                response_model = openai_result.get("model") or "gpt-4o-mini"
                response_usage = openai_result.get("usage")
                result = {
                    "response": response_text,
                    "model_used": "openai",
                    "context_used": context
                }
                if db is not None:
                    self._track_usage_if_possible(
                        db=db,
                        scope=cache_scope,
                        operation=cache_operation,
                        provider="openai",
                        model=response_model,
                        usage=response_usage,
                    )
                    self._store_cache_entry(
                        db,
                        cache_key=cache_key,
                        scope=cache_scope,
                        operation=cache_operation,
                        provider="openai",
                        model=response_model,
                        request_json=cache_payload,
                        response_text=response_text,
                    )
                    db.commit()
                return result
            except Exception as e:
                print(f"OpenAI error: {e}")
                if not self.use_ollama_fallback:
                    # Se Ollama não está habilitado, ainda tentamos DeepSeek se estiver configurado.
                    pass

        # 2) DeepSeek (fallback)
        if self.deepseek_client:
            try:
                print("[REQUEST] Sending request to DeepSeek...")
                deepseek_result = await self._get_deepseek_response(messages)
                response_text = deepseek_result["text"]
                response_model = deepseek_result.get("model") or "deepseek-chat"
                response_usage = deepseek_result.get("usage")
                print(f"[SUCCESS] DeepSeek responded: {len(response_text)} characters")
                result = {
                    "response": response_text,
                    "model_used": "deepseek",
                    "context_used": context
                }
                if db is not None:
                    self._track_usage_if_possible(
                        db=db,
                        scope=cache_scope,
                        operation=cache_operation,
                        provider="deepseek",
                        model=response_model,
                        usage=response_usage,
                    )
                    self._store_cache_entry(
                        db,
                        cache_key=cache_key,
                        scope=cache_scope,
                        operation=cache_operation,
                        provider="deepseek",
                        model=response_model,
                        request_json=cache_payload,
                        response_text=response_text,
                    )
                    db.commit()
                return result
            except Exception as e:
                print(f"[ERROR] DeepSeek error: {e}")
                # Continua para próxima opção

        # 3) Ollama (fallback opcional)
        if self.use_ollama_fallback:
            try:
                ollama_result = await self._get_ollama_response(messages)
                response_text = ollama_result["text"]
                result = {
                    "response": response_text,
                    "model_used": "ollama",
                    "context_used": context
                }
                if db is not None:
                    self._track_usage_if_possible(
                        db=db,
                        scope=cache_scope,
                        operation=cache_operation,
                        provider="ollama",
                        model=ollama_result.get("model") or "llama3.2",
                        usage=ollama_result.get("usage"),
                    )
                    self._store_cache_entry(
                        db,
                        cache_key=cache_key,
                        scope=cache_scope,
                        operation=cache_operation,
                        provider="ollama",
                        model="llama3.2",
                        request_json=cache_payload,
                        response_text=response_text,
                    )
                    db.commit()
                return result
            except Exception as e:
                print(f"Ollama error: {e}")
                raise Exception("Nenhum modelo de IA disponível no momento. Verifique as configurações.")

        raise Exception("Nenhum modelo de IA configurado.")

    async def get_ai_response_messages_prefer_deepseek(
        self,
        messages: List[Dict[str, str]],
        *,
        db: Optional[Session] = None,
        cache_operation: str = "chat.messages.deepseek",
        cache_scope: str = "global",
    ) -> Dict[str, Any]:
        """Executa uma chamada de IA priorizando DeepSeek, com fallback para OpenAI/Ollama."""

        if not messages:
            return {"response": "", "model_used": "none", "context_used": None}

        cache_key: Optional[str] = None
        cache_payload: Optional[Dict[str, Any]] = None

        if db is not None:
            cache_payload = {
                "messages": messages,
                "operation": cache_operation,
            }
            cache_key = self._make_cache_key(operation=cache_operation, scope=cache_scope, payload=cache_payload)
            cached = self._get_cache_entry(db, cache_key)
            if cached and cached.status == "ok" and (cached.response_text is not None or cached.response_json is not None):
                self._touch_cache_hit(db, cached.id)
                db.commit()
                return {
                    "response": cached.response_text or "",
                    "model_used": cached.provider or "cache",
                    "context_used": None,
                    "cached": True,
                }

        # 1) DeepSeek (preferido)
        if self.deepseek_client:
            try:
                print("[REQUEST] Sending request to DeepSeek...")
                deepseek_result = await self._get_deepseek_response(messages)
                response_text = deepseek_result["text"]
                response_model = deepseek_result.get("model") or "deepseek-chat"
                response_usage = deepseek_result.get("usage")
                print(f"[SUCCESS] DeepSeek responded: {len(response_text)} characters")
                if db is not None and cache_key is not None and cache_payload is not None:
                    self._track_usage_if_possible(
                        db=db,
                        scope=cache_scope,
                        operation=cache_operation,
                        provider="deepseek",
                        model=response_model,
                        usage=response_usage,
                    )
                    self._store_cache_entry(
                        db,
                        cache_key=cache_key,
                        scope=cache_scope,
                        operation=cache_operation,
                        provider="deepseek",
                        model=response_model,
                        request_json=cache_payload,
                        response_text=response_text,
                    )
                    db.commit()
                return {"response": response_text, "model_used": "deepseek", "context_used": None}
            except Exception as e:
                print(f"[ERROR] DeepSeek error: {e}")

        # 2) OpenAI (fallback)
        if self.openai_chat_client:
            try:
                openai_result = await self._get_openai_response(messages)
                response_text = openai_result["text"]
                response_model = openai_result.get("model") or "gpt-4o-mini"
                response_usage = openai_result.get("usage")
                if db is not None and cache_key is not None and cache_payload is not None:
                    self._track_usage_if_possible(
                        db=db,
                        scope=cache_scope,
                        operation=cache_operation,
                        provider="openai",
                        model=response_model,
                        usage=response_usage,
                    )
                    self._store_cache_entry(
                        db,
                        cache_key=cache_key,
                        scope=cache_scope,
                        operation=cache_operation,
                        provider="openai",
                        model=response_model,
                        request_json=cache_payload,
                        response_text=response_text,
                    )
                    db.commit()
                return {"response": response_text, "model_used": "openai", "context_used": None}
            except Exception as e:
                print(f"OpenAI error: {e}")

        # 3) Ollama (fallback opcional)
        if self.use_ollama_fallback:
            try:
                ollama_result = await self._get_ollama_response(messages)
                response_text = ollama_result["text"]
                if db is not None and cache_key is not None and cache_payload is not None:
                    self._track_usage_if_possible(
                        db=db,
                        scope=cache_scope,
                        operation=cache_operation,
                        provider="ollama",
                        model=ollama_result.get("model") or "llama3.2",
                        usage=ollama_result.get("usage"),
                    )
                    self._store_cache_entry(
                        db,
                        cache_key=cache_key,
                        scope=cache_scope,
                        operation=cache_operation,
                        provider="ollama",
                        model="llama3.2",
                        request_json=cache_payload,
                        response_text=response_text,
                    )
                    db.commit()
                return {"response": response_text, "model_used": "ollama", "context_used": None}
            except Exception as e:
                print(f"Ollama error: {e}")
                raise Exception("Nenhum modelo de IA disponível no momento. Verifique as configurações.")

        raise Exception("Nenhum modelo de IA configurado.")

    async def get_ai_response_messages(
        self,
        messages: List[Dict[str, str]],
        *,
        db: Optional[Session] = None,
        cache_operation: str = "chat.messages",
        cache_scope: str = "global",
    ) -> Dict[str, Any]:
        """Executa uma chamada de IA usando mensagens fornecidas pelo caller.

        Mantém o mesmo comportamento de cache no Postgres (ai_cache) e a mesma ordem
        de provedores: OpenAI → DeepSeek → Ollama (opcional).

        Isso é útil para tarefas estruturadas (ex.: exigir JSON estrito) onde o prompt
        padrão da "Sarah" não é desejável.
        """

        if not messages:
            return {"response": "", "model_used": "none", "context_used": None}

        cache_key: Optional[str] = None
        cache_payload: Optional[Dict[str, Any]] = None

        if db is not None:
            cache_payload = {
                "messages": messages,
                "operation": cache_operation,
            }
            cache_key = self._make_cache_key(operation=cache_operation, scope=cache_scope, payload=cache_payload)
            cached = self._get_cache_entry(db, cache_key)
            if cached and cached.status == "ok" and (cached.response_text is not None or cached.response_json is not None):
                self._touch_cache_hit(db, cached.id)
                db.commit()
                return {
                    "response": cached.response_text or "",
                    "model_used": cached.provider or "cache",
                    "context_used": None,
                    "cached": True,
                }

        # 1) OpenAI (principal)
        if self.openai_chat_client:
            try:
                openai_result = await self._get_openai_response(messages)
                response_text = openai_result["text"]
                response_model = openai_result.get("model") or "gpt-4o-mini"
                response_usage = openai_result.get("usage")
                if db is not None and cache_key is not None and cache_payload is not None:
                    self._track_usage_if_possible(
                        db=db,
                        scope=cache_scope,
                        operation=cache_operation,
                        provider="openai",
                        model=response_model,
                        usage=response_usage,
                    )
                    self._store_cache_entry(
                        db,
                        cache_key=cache_key,
                        scope=cache_scope,
                        operation=cache_operation,
                        provider="openai",
                        model=response_model,
                        request_json=cache_payload,
                        response_text=response_text,
                    )
                    db.commit()
                return {"response": response_text, "model_used": "openai", "context_used": None}
            except Exception as e:
                print(f"OpenAI error (messages): {e}")

        # 2) DeepSeek (fallback)
        if self.deepseek_client:
            try:
                deepseek_result = await self._get_deepseek_response(messages)
                response_text = deepseek_result["text"]
                response_model = deepseek_result.get("model") or "deepseek-chat"
                response_usage = deepseek_result.get("usage")
                if db is not None and cache_key is not None and cache_payload is not None:
                    self._track_usage_if_possible(
                        db=db,
                        scope=cache_scope,
                        operation=cache_operation,
                        provider="deepseek",
                        model=response_model,
                        usage=response_usage,
                    )
                    self._store_cache_entry(
                        db,
                        cache_key=cache_key,
                        scope=cache_scope,
                        operation=cache_operation,
                        provider="deepseek",
                        model=response_model,
                        request_json=cache_payload,
                        response_text=response_text,
                    )
                    db.commit()
                return {"response": response_text, "model_used": "deepseek", "context_used": None}
            except Exception as e:
                print(f"DeepSeek error (messages): {e}")

        # 3) Ollama (fallback opcional)
        if self.use_ollama_fallback:
            try:
                ollama_result = await self._get_ollama_response(messages)
                response_text = ollama_result["text"]
                if db is not None and cache_key is not None and cache_payload is not None:
                    self._track_usage_if_possible(
                        db=db,
                        scope=cache_scope,
                        operation=cache_operation,
                        provider="ollama",
                        model=ollama_result.get("model") or "llama3.2",
                        usage=ollama_result.get("usage"),
                    )
                    self._store_cache_entry(
                        db,
                        cache_key=cache_key,
                        scope=cache_scope,
                        operation=cache_operation,
                        provider="ollama",
                        model="llama3.2",
                        request_json=cache_payload,
                        response_text=response_text,
                    )
                    db.commit()
                return {"response": response_text, "model_used": "ollama", "context_used": None}
            except Exception as e:
                print(f"Ollama error (messages): {e}")

        return {"response": "", "model_used": "none", "context_used": None}

    async def _get_deepseek_response(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Obtém resposta da DeepSeek API com metadados de uso quando disponível."""
        if not self.deepseek_client:
            raise Exception("Cliente DeepSeek não configurado.")
        try:
            response = await asyncio.to_thread(
                self.deepseek_client.chat.completions.create,
                model=self.deepseek_chat_model,
                messages=messages,
                temperature=self.ai_chat_temperature,
                max_tokens=self.deepseek_chat_max_tokens,
                timeout=self.ai_chat_timeout_seconds,
            )
            text = (response.choices[0].message.content or "").strip()
            usage = parse_usage_tokens(getattr(response, "usage", None))
            model = parse_model_name(response, self.deepseek_chat_model)
            return {"text": text, "usage": usage, "model": model}
        except Exception as e:
            raise Exception(f"Erro na DeepSeek API: {str(e)}")

    async def generate_speech(
        self,
        text: str,
        voice: str = "nova",
        speed: Optional[float] = None,
        *,
        db: Optional[Session] = None,
        cache_operation: str = "tts",
        cache_scope: str = "global",
    ) -> bytes:
        """
        Gera áudio a partir de texto usando OpenAI TTS.
        Vozes disponíveis: alloy, echo, fable, onyx, nova, shimmer
        'nova' é uma voz feminina calorosa (perfeita para a professora Sarah)

        Nota: TTS requer OpenAI API Key. Se não configurada, retorna erro explicativo.
        """
        if not self.openai_client and not (self.lemonfox_enabled and self.lemonfox_api_key):
            print("[TTS] OpenAI/Lemonfox API Key não configurada - TTS não disponível")
            raise Exception("TTS requer LEMONFOX_API_KEY ou OPENAI_API_KEY no arquivo .env para usar áudio.")

        # Cache lookup
        cache_key = None
        cache_payload = None
        tts_speed = self._normalize_tts_speed(speed, default=self.tts_speed)
        if db is not None:
            cache_payload = {
                "text": text[:4096],
                "voice": voice,
                "model": "tts-1",
                "speed": tts_speed,
                "operation": cache_operation,
            }
            cache_key = self._make_cache_key(operation=cache_operation, scope=cache_scope, payload=cache_payload)
            cached = self._get_cache_entry(db, cache_key)
            if cached and cached.status == "ok" and cached.response_bytes:
                self._touch_cache_hit(db, cached.id)
                db.commit()
                return bytes(cached.response_bytes)

        try:
            print(f"[TTS] Gerando áudio para {len(text)} caracteres...")
            safe_text = text[:4096]

            if self.lemonfox_enabled and self.lemonfox_api_key:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(
                        f"{self.lemonfox_base_url}/audio/speech",
                        headers={
                            "Authorization": f"Bearer {self.lemonfox_api_key}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "input": safe_text,
                            "voice": voice,
                            "response_format": "mp3",
                            "language": "en-us",
                            "speed": tts_speed,
                        },
                    )
                    response.raise_for_status()
                    audio_bytes = response.content
                    provider = "lemonfox"
                    model = "tts"
            else:
                response = self.openai_client.audio.speech.create(
                    model="tts-1",  # Modelo mais rápido e barato
                    voice=voice,
                    input=safe_text,  # Limite de caracteres do OpenAI TTS
                    speed=tts_speed,
                )
                audio_bytes = response.content
                provider = "openai"
                model = "tts-1"

            print("[TTS] Áudio gerado com sucesso!")
            if db is not None and cache_key and cache_payload:
                self._store_cache_entry(
                    db,
                    cache_key=cache_key,
                    scope=cache_scope,
                    operation=cache_operation,
                    provider=provider,
                    model=model,
                    request_json=cache_payload,
                    response_bytes=audio_bytes,
                )
                db.commit()
            return audio_bytes
        except Exception as e:
            print(f"[TTS ERROR] {str(e)}")
            raise Exception(f"Erro ao gerar áudio: {str(e)}")

    async def transcribe_audio(
        self,
        audio_bytes: bytes,
        filename: str = "audio.webm",
        content_type: str = "audio/webm",
        language: Optional[str] = None,
        prompt: Optional[str] = None,
    ) -> str:
        """Transcreve áudio para texto (STT) usando OpenAI Whisper."""
        if not self.openai_client and not (self.lemonfox_enabled and self.lemonfox_api_key):
            raise Exception("STT requer LEMONFOX_API_KEY ou OPENAI_API_KEY para transcrição.")

        if self.lemonfox_enabled and self.lemonfox_api_key:
            lang = (language or "").strip().lower()
            language_map = {
                "en": "english",
                "en-us": "english",
                "en_us": "english",
                "pt": "portuguese",
                "pt-br": "portuguese",
                "pt_br": "portuguese",
            }
            lemonfox_lang = language_map.get(lang, language or None)

            data = {
                "response_format": "json",
            }
            if lemonfox_lang:
                data["language"] = lemonfox_lang
            if prompt:
                data["prompt"] = prompt

            files = {
                "file": (filename, audio_bytes, content_type),
            }

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.lemonfox_base_url}/audio/transcriptions",
                    headers={"Authorization": f"Bearer {self.lemonfox_api_key}"},
                    data=data,
                    files=files,
                )
                response.raise_for_status()
                payload = response.json()
                return (payload.get("text") or "").strip()

        bio = io.BytesIO(audio_bytes)
        # OpenAI client uses filename from file object name when available
        try:
            setattr(bio, "name", filename)
        except Exception:
            pass

        kwargs = {
            "model": "whisper-1",
            "file": bio,
        }
        if language:
            kwargs["language"] = language
        if prompt:
            kwargs["prompt"] = prompt

        result = self.openai_client.audio.transcriptions.create(**kwargs)

        # SDK may return {text: ...} or an object with .text
        text = getattr(result, "text", None)
        if text is None and isinstance(result, dict):
            text = result.get("text")
        return (text or "").strip()

    def _coerce_dict(self, value: Any) -> Dict[str, Any]:
        if isinstance(value, dict):
            return value
        if hasattr(value, "model_dump"):
            try:
                dumped = value.model_dump()
                if isinstance(dumped, dict):
                    return dumped
            except Exception:
                pass
        if hasattr(value, "to_dict"):
            try:
                dumped = value.to_dict()
                if isinstance(dumped, dict):
                    return dumped
            except Exception:
                pass
        return {}

    def _normalize_alignment_word(self, value: str) -> str:
        lowered = (value or "").strip().lower().replace("’", "'")
        return re.sub(r"[^a-z0-9']+", "", lowered)

    def _tokenize_text_words(self, text: str) -> List[str]:
        return re.findall(r"[A-Za-z0-9]+(?:['’-][A-Za-z0-9]+)*", text or "")

    def _alignment_variants(self, word: str) -> List[str]:
        normalized = self._normalize_alignment_word(word)
        if not normalized:
            return []

        variants = {normalized, normalized.replace("'", "")}

        if normalized.endswith("'s") and len(normalized) > 2:
            base = normalized[:-2]
            variants.add(base)
            variants.add(base.replace("'", ""))
        if normalized.endswith("s'") and len(normalized) > 2:
            base = normalized[:-1]
            variants.add(base)
            variants.add(base.replace("'", ""))

        plain = normalized.replace("'", "")
        if len(plain) > 3 and plain.endswith("es"):
            variants.add(plain[:-2])
        if len(plain) > 3 and plain.endswith("s"):
            variants.add(plain[:-1])

        return [candidate for candidate in variants if candidate]

    def _alignment_words_match(self, expected: str, observed: str) -> bool:
        if not expected or not observed:
            return False
        if expected == observed:
            return True

        expected_variants = set(self._alignment_variants(expected))
        observed_variants = set(self._alignment_variants(observed))
        if expected_variants.intersection(observed_variants):
            return True

        if min(len(expected), len(observed)) >= 5:
            return SequenceMatcher(None, expected, observed).ratio() >= 0.87
        return False

    def _build_lcs_alignment_pairs(
        self,
        *,
        normalized_text_words: List[str],
        normalized_observed_words: List[str],
    ) -> List[Tuple[int, int]]:
        n = len(normalized_text_words)
        m = len(normalized_observed_words)
        if n == 0 or m == 0:
            return []

        # Proteção para textos extremamente longos (evita custo O(n*m) excessivo).
        if n * m > 240000:
            return []

        dp: List[List[int]] = [[0] * (m + 1) for _ in range(n + 1)]

        for text_idx in range(n - 1, -1, -1):
            row = dp[text_idx]
            next_row = dp[text_idx + 1]
            expected = normalized_text_words[text_idx]
            for observed_idx in range(m - 1, -1, -1):
                observed = normalized_observed_words[observed_idx]
                if self._alignment_words_match(expected, observed):
                    row[observed_idx] = next_row[observed_idx + 1] + 1
                else:
                    down = next_row[observed_idx]
                    right = row[observed_idx + 1]
                    row[observed_idx] = down if down >= right else right

        pairs: List[Tuple[int, int]] = []
        text_idx = 0
        observed_idx = 0

        while text_idx < n and observed_idx < m:
            expected = normalized_text_words[text_idx]
            observed = normalized_observed_words[observed_idx]

            if (
                self._alignment_words_match(expected, observed)
                and dp[text_idx][observed_idx] == dp[text_idx + 1][observed_idx + 1] + 1
            ):
                pairs.append((text_idx, observed_idx))
                text_idx += 1
                observed_idx += 1
                continue

            if dp[text_idx + 1][observed_idx] >= dp[text_idx][observed_idx + 1]:
                text_idx += 1
            else:
                observed_idx += 1

        return pairs

    def _build_greedy_alignment_pairs(
        self,
        *,
        normalized_text_words: List[str],
        normalized_observed_words: List[str],
        max_lookahead: int = 12,
    ) -> List[Tuple[int, int]]:
        pairs: List[Tuple[int, int]] = []
        text_idx = 0
        observed_idx = 0

        while text_idx < len(normalized_text_words) and observed_idx < len(normalized_observed_words):
            expected = normalized_text_words[text_idx]
            observed = normalized_observed_words[observed_idx]

            if self._alignment_words_match(expected, observed):
                pairs.append((text_idx, observed_idx))
                text_idx += 1
                observed_idx += 1
                continue

            moved = False

            for lookahead in range(1, max_lookahead + 1):
                probe_idx = observed_idx + lookahead
                if probe_idx >= len(normalized_observed_words):
                    break
                if self._alignment_words_match(expected, normalized_observed_words[probe_idx]):
                    observed_idx = probe_idx
                    moved = True
                    break
            if moved:
                continue

            for lookahead in range(1, max_lookahead + 1):
                probe_idx = text_idx + lookahead
                if probe_idx >= len(normalized_text_words):
                    break
                if self._alignment_words_match(normalized_text_words[probe_idx], observed):
                    text_idx = probe_idx
                    moved = True
                    break
            if moved:
                continue

            pairs.append((text_idx, observed_idx))
            text_idx += 1
            observed_idx += 1

        return pairs

    def _build_segment_word_timings(self, payload: Dict[str, Any]) -> List[Dict[str, float | str]]:
        segments = payload.get("segments")
        if not isinstance(segments, list):
            return []

        timing_rows: List[Dict[str, float | str]] = []
        for raw_segment in segments:
            segment = self._coerce_dict(raw_segment)
            seg_text = str(segment.get("text") or "").strip()
            if not seg_text:
                continue

            words = re.findall(r"[A-Za-z0-9]+(?:['’-][A-Za-z0-9]+)*", seg_text)
            if not words:
                continue

            try:
                seg_start = float(segment.get("start"))
                seg_end = float(segment.get("end"))
            except (TypeError, ValueError):
                continue

            if seg_end <= seg_start:
                continue

            # Distribui o tempo do segmento por peso de palavra (palavras maiores recebem ligeiramente mais tempo).
            weights = [1.0 + min(10.0, float(len(w))) * 0.06 for w in words]
            total_weight = sum(weights) or 1.0
            cursor = seg_start
            segment_duration = seg_end - seg_start

            for idx, word in enumerate(words):
                weight = weights[idx]
                duration = max(0.04, segment_duration * (weight / total_weight))
                end = min(seg_end, cursor + duration)
                if end <= cursor:
                    end = cursor + 0.04
                timing_rows.append(
                    {
                        "word": word,
                        "start": round(cursor, 4),
                        "end": round(end, 4),
                    }
                )
                cursor = end

        return timing_rows

    def _extract_transcription_word_timings(
        self,
        payload: Dict[str, Any],
    ) -> Tuple[List[Dict[str, float | str]], str]:
        raw_words = payload.get("words")
        if isinstance(raw_words, list):
            word_timings: List[Dict[str, float | str]] = []
            for raw_word in raw_words:
                item = self._coerce_dict(raw_word)
                word = str(item.get("word") or item.get("text") or "").strip()
                if not word:
                    continue

                try:
                    start = float(item.get("start"))
                    end = float(item.get("end"))
                except (TypeError, ValueError):
                    continue

                if end <= start:
                    end = start + 0.04

                word_timings.append(
                    {
                        "word": word,
                        "start": round(max(0.0, start), 4),
                        "end": round(max(0.0, end), 4),
                    }
                )

            if word_timings:
                return word_timings, "transcription_words"

        segment_timings = self._build_segment_word_timings(payload)
        if segment_timings:
            return segment_timings, "transcription_segments"

        return [], "none"

    def _build_alignment_transcription_prompt(self, text: str) -> Optional[str]:
        cleaned = re.sub(r"\s+", " ", (text or "")).strip()
        if not cleaned:
            return None

        # Prompt curto para "puxar" a transcrição para o conteúdo esperado sem estourar limite.
        return cleaned[:420]

    def _align_timings_with_text(
        self,
        *,
        text_words: List[str],
        observed_timings: List[Dict[str, float | str]],
    ) -> List[Dict[str, float | str | int]]:
        if not text_words:
            return []

        normalized_text_words = [self._normalize_alignment_word(word) for word in text_words]

        observed_rows: List[Dict[str, float | str]] = []
        for row in observed_timings:
            raw_word = str(row.get("word") or "").strip()
            normalized = self._normalize_alignment_word(raw_word)
            if not normalized:
                continue

            try:
                start = float(row.get("start"))
                end = float(row.get("end"))
            except (TypeError, ValueError):
                continue

            if end <= start:
                end = start + 0.04

            observed_rows.append(
                {
                    "word": raw_word,
                    "normalized": normalized,
                    "start": start,
                    "end": end,
                }
            )

        if not observed_rows:
            return []

        normalized_observed_words = [str(row["normalized"]) for row in observed_rows]

        matched_pairs = self._build_lcs_alignment_pairs(
            normalized_text_words=normalized_text_words,
            normalized_observed_words=normalized_observed_words,
        )
        if not matched_pairs:
            matched_pairs = self._build_greedy_alignment_pairs(
                normalized_text_words=normalized_text_words,
                normalized_observed_words=normalized_observed_words,
            )

        matched_count = len(matched_pairs)
        word_count = len(text_words)
        min_required_anchors = 3 if word_count <= 12 else 5
        match_ratio = matched_count / max(1, word_count)
        # Se quase nada casou, o áudio provavelmente não bate com o texto atual.
        if matched_count < min_required_anchors or (word_count >= 20 and match_ratio < 0.22):
            return []

        assignments: List[Optional[Dict[str, float | str]]] = [None] * len(text_words)
        for text_idx, observed_idx in matched_pairs:
            if 0 <= text_idx < len(assignments) and 0 <= observed_idx < len(observed_rows):
                assignments[text_idx] = observed_rows[observed_idx]

        resolved: List[Tuple[float, float]] = []
        first_observed_start = float(observed_rows[0]["start"])  # type: ignore[index]
        last_observed_end = float(observed_rows[-1]["end"])  # type: ignore[index]
        observed_duration = max(0.5, last_observed_end - first_observed_start)
        estimated_step = max(0.09, observed_duration / max(1, len(text_words)))

        for idx, item in enumerate(assignments):
            if item:
                start = float(item["start"])  # type: ignore[index]
                end = float(item["end"])  # type: ignore[index]
                resolved.append((start, end))
                continue

            prev_idx = idx - 1
            while prev_idx >= 0 and assignments[prev_idx] is None:
                prev_idx -= 1

            next_idx = idx + 1
            while next_idx < len(assignments) and assignments[next_idx] is None:
                next_idx += 1

            if prev_idx >= 0 and next_idx < len(assignments):
                prev_end = float(assignments[prev_idx]["end"])  # type: ignore[index]
                next_start = float(assignments[next_idx]["start"])  # type: ignore[index]
                span_slots = max(1, next_idx - prev_idx)
                span = max(0.08, next_start - prev_end)
                slot = span / span_slots
                start = prev_end + slot * (idx - prev_idx - 1)
                end = start + slot * 0.9
            elif prev_idx >= 0:
                prev_end = float(assignments[prev_idx]["end"])  # type: ignore[index]
                start = prev_end + estimated_step * (idx - prev_idx - 1)
                end = start + estimated_step * 0.9
            elif next_idx < len(assignments):
                next_start = float(assignments[next_idx]["start"])  # type: ignore[index]
                distance = max(1, next_idx - idx)
                slot = estimated_step
                start = max(0.0, next_start - slot * distance)
                end = start + slot * 0.9
            else:
                start = first_observed_start + idx * estimated_step
                end = start + estimated_step * 0.9

            resolved.append((start, end))

        word_timings: List[Dict[str, float | str | int]] = []
        last_end = 0.0
        for idx, word in enumerate(text_words):
            start, end = resolved[idx]
            safe_start = max(last_end, start)
            safe_end = max(safe_start + 0.03, end)
            last_end = safe_end
            word_timings.append(
                {
                    "index": idx,
                    "word": word,
                    "start": round(safe_start, 4),
                    "end": round(safe_end, 4),
                }
            )

        return word_timings

    async def transcribe_audio_verbose(
        self,
        audio_bytes: bytes,
        filename: str = "audio.webm",
        content_type: str = "audio/webm",
        language: Optional[str] = None,
        prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not self.openai_client and not (self.lemonfox_enabled and self.lemonfox_api_key):
            raise Exception("STT requer LEMONFOX_API_KEY ou OPENAI_API_KEY para transcrição.")

        if self.lemonfox_enabled and self.lemonfox_api_key:
            data = {
                "response_format": "verbose_json",
            }
            if language:
                data["language"] = language
            if prompt:
                data["prompt"] = prompt

            files = {
                "file": (filename, audio_bytes, content_type),
            }

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.lemonfox_base_url}/audio/transcriptions",
                    headers={"Authorization": f"Bearer {self.lemonfox_api_key}"},
                    data=data,
                    files=files,
                )
                response.raise_for_status()
                payload = response.json()
                if isinstance(payload, dict):
                    return payload
                return {}

        bio = io.BytesIO(audio_bytes)
        try:
            setattr(bio, "name", filename)
        except Exception:
            pass

        request_kwargs: Dict[str, Any] = {
            "model": "whisper-1",
            "file": bio,
            "response_format": "verbose_json",
            "timestamp_granularities": ["word"],
        }
        if language:
            request_kwargs["language"] = language
        if prompt:
            request_kwargs["prompt"] = prompt

        try:
            result = self.openai_client.audio.transcriptions.create(**request_kwargs)
        except Exception as e:
            # Alguns clientes/contas não aceitam timestamp_granularities.
            lowered = str(e).lower()
            should_retry_without_granularity = (
                isinstance(e, TypeError)
                or "timestamp_granularities" in lowered
                or "unknown parameter" in lowered
                or "invalid_request_error" in lowered
            )
            if not should_retry_without_granularity:
                raise

            request_kwargs.pop("timestamp_granularities", None)
            bio.seek(0)
            result = self.openai_client.audio.transcriptions.create(**request_kwargs)

        payload = self._coerce_dict(result)
        if payload:
            return payload

        # Fallback de segurança quando o SDK retorna objeto sem model_dump.
        text = getattr(result, "text", None)
        return {"text": text or ""}

    async def get_text_audio_word_alignment(
        self,
        *,
        text: str,
        audio_bytes: bytes,
        filename: str = "audio.mp3",
        content_type: str = "audio/mpeg",
        db: Optional[Session] = None,
        cache_operation: str = "texts.audio.alignment",
        cache_scope: str = "global",
    ) -> Dict[str, Any]:
        text_words = self._tokenize_text_words(text)
        if not text_words:
            return {"source": "none", "word_timings": []}

        cache_key = None
        cache_payload = None
        if db is not None:
            cache_payload = {
                "operation": cache_operation,
                "alignment_algo_version": "lcs-v2",
                "text_sha": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                "audio_sha": hashlib.sha256(audio_bytes).hexdigest(),
            }
            cache_key = self._make_cache_key(
                operation=cache_operation,
                scope=cache_scope,
                payload=cache_payload,
            )
            cached = self._get_cache_entry(db, cache_key)
            if cached and cached.status == "ok" and isinstance(cached.response_json, dict):
                response_json = cached.response_json
                if "source" in response_json and "word_timings" in response_json:
                    self._touch_cache_hit(db, cached.id)
                    db.commit()
                    return response_json

        try:
            verbose = await self.transcribe_audio_verbose(
                audio_bytes=audio_bytes,
                filename=filename,
                content_type=content_type,
                language="en",
                prompt=self._build_alignment_transcription_prompt(text),
            )
            observed_timings, source = self._extract_transcription_word_timings(verbose)
            if not observed_timings:
                result = {"source": "none", "word_timings": []}
            else:
                aligned = self._align_timings_with_text(text_words=text_words, observed_timings=observed_timings)
                result = {
                    "source": source,
                    "word_timings": aligned,
                }
        except Exception as e:
            print(f"[AUDIO ALIGNMENT] Falha ao gerar alinhamento: {str(e)}")
            result = {"source": "none", "word_timings": []}

        if db is not None and cache_key and cache_payload:
            self._store_cache_entry(
                db,
                cache_key=cache_key,
                scope=cache_scope,
                operation=cache_operation,
                provider="openai" if self.openai_client else "lemonfox",
                model="whisper-1",
                request_json=cache_payload,
                response_json=result,
            )
            db.commit()

        return result

    async def _get_openai_response(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Obtém resposta da OpenAI API com metadados de uso quando disponível."""
        if not self.openai_chat_client:
            raise Exception("Cliente OpenAI não configurado.")
        try:
            response = await asyncio.to_thread(
                self.openai_chat_client.chat.completions.create,
                model=self.openai_chat_model,
                messages=messages,
                temperature=self.ai_chat_temperature,
                max_tokens=self.openai_chat_max_tokens,
                timeout=self.ai_chat_timeout_seconds,
            )
            text = (response.choices[0].message.content or "").strip()
            usage = parse_usage_tokens(getattr(response, "usage", None))
            model = parse_model_name(response, self.openai_chat_model)
            return {"text": text, "usage": usage, "model": model}
        except OpenAIError as e:
            raise Exception(f"Erro na OpenAI API: {str(e)}")

    async def _get_ollama_response(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Obtém resposta do Ollama (modelo local)"""
        # Configurar timeouts generosos para geração de IA
        timeout = httpx.Timeout(300.0, connect=60.0)

        async with httpx.AsyncClient(timeout=timeout) as client:
            # Converter mensagens para formato Ollama
            prompt = self._convert_messages_to_prompt(messages)

            payload = {
                "model": "llama3.2",  # ou outro modelo disponível no Ollama
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "num_predict": 800
                }
            }

            try:
                print(f"[DEBUG] Sending request to Ollama: {self.ollama_url}/api/generate")
                print(f"[DEBUG] Prompt length: {len(prompt)} characters")

                response = await client.post(
                    f"{self.ollama_url}/api/generate",
                    json=payload
                )

                print(f"[DEBUG] Ollama response status: {response.status_code}")
                response.raise_for_status()

                result = response.json()
                print(f"[DEBUG] Ollama result keys: {result.keys()}")

                ai_response = result.get("response", "")

                if not ai_response or ai_response.strip() == "":
                    raise Exception(f"Ollama returned empty response. Full result: {result}")

                print(f"[DEBUG] Ollama response length: {len(ai_response)} characters")
                usage = parse_usage_tokens(result.get("usage") if isinstance(result, dict) else None)
                model_name = result.get("model") if isinstance(result, dict) else "llama3.2"
                return {
                    "text": ai_response,
                    "usage": usage,
                    "model": model_name or "llama3.2",
                }

            except httpx.TimeoutException as e:
                print(f"[DEBUG] Timeout details: {type(e).__name__}: {str(e)}")
                raise Exception(f"Ollama timeout: {str(e)}")
            except httpx.HTTPError as e:
                print(f"[DEBUG] HTTP error details: {type(e).__name__}: {str(e)}")
                raise Exception(f"Ollama HTTP error: {str(e)}")
            except Exception as e:
                print(f"[DEBUG] General error details: {type(e).__name__}: {str(e)}")
                raise Exception(f"Ollama error: {str(e)}")

    def _convert_messages_to_prompt(self, messages: List[Dict[str, str]]) -> str:
        """Converte formato de mensagens OpenAI para prompt simples do Ollama"""
        prompt_parts = []
        for msg in messages:
            role = msg["role"]
            content = msg["content"]

            if role == "system":
                prompt_parts.append(f"SYSTEM: {content}")
            elif role == "user":
                prompt_parts.append(f"USER: {content}")
            elif role == "assistant":
                prompt_parts.append(f"ASSISTANT: {content}")

        prompt_parts.append("ASSISTANT:")
        return "\n\n".join(prompt_parts)

    async def analyze_sentence(
        self,
        sentence_en: str,
        sentence_pt: str,
        user_level: str = "A1",
        db: Optional[Session] = None,
        cache_operation: str = "sentence.analyze",
        cache_scope: str = "global",
    ) -> Dict[str, Any]:
        """Analisa uma frase e retorna explicação detalhada"""

        prompt = f"""Analise a seguinte frase em inglês e forneça uma explicação detalhada para um aluno brasileiro de nível {user_level}:

**Inglês:** {sentence_en}
**Português:** {sentence_pt}

Por favor, forneça:
1. Estrutura gramatical da frase
2. Vocabulário-chave com explicações
3. Pontos de atenção (expressões idiomáticas, falsos cognatos, etc.)
4. 2-3 exemplos similares
5. Uma dica de uso prático

Seja claro, didático e encorajador.
Mantenha a resposta objetiva, entre 6 e 10 linhas (máximo 180 palavras)."""

        response = await self.get_ai_response(
            prompt,
            db=db,
            cache_operation=cache_operation,
            cache_scope=cache_scope,
        )
        return response

    async def generate_practice_exercises(
        self,
        sentence_en: str,
        user_level: str = "A1",
        db: Optional[Session] = None,
        cache_operation: str = "sentence.exercises",
        cache_scope: str = "global",
    ) -> Dict[str, Any]:
        """Gera exercícios práticos baseados em uma frase"""

        prompt = f"""Baseado na frase: "{sentence_en}"

Crie 3 exercícios práticos para um aluno de nível {user_level}:
1. Um exercício de completar lacunas
2. Um exercício de tradução
3. Uma pergunta de compreensão

Forneça as respostas corretas ao final."""

        response = await self.get_ai_response(
            prompt,
            db=db,
            cache_operation=cache_operation,
            cache_scope=cache_scope,
        )
        return response

    async def correct_user_sentence(
        self,
        user_sentence: str,
        target_sentence: Optional[str] = None,
        db: Optional[Session] = None,
        cache_operation: str = "sentence.correct",
        cache_scope: str = "global",
    ) -> Dict[str, Any]:
        """Corrige uma frase escrita pelo usuário"""

        prompt = f"""O aluno escreveu: "{user_sentence}"
"""

        if target_sentence:
            prompt += f'\nA frase correta seria: "{target_sentence}"\n'

        prompt += """
Por favor:
1. Identifique os erros (se houver)
2. Explique cada erro de forma didática
3. Forneça a versão corrigida
4. Dê dicas para evitar esse erro no futuro"""

        response = await self.get_ai_response(
            prompt,
            db=db,
            cache_operation=cache_operation,
            cache_scope=cache_scope,
        )
        return response


# Singleton instance
ai_teacher_service = AITeacherService()
