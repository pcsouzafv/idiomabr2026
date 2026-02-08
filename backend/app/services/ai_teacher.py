import os
import json
import hashlib
import io
from typing import Optional, Dict, Any, List, Tuple
import httpx
from openai import OpenAI, OpenAIError

from sqlalchemy.orm import Session
from sqlalchemy import update

from app.models.ai_cache import AICacheEntry


class AITeacherService:
    """
    Serviço de professor de IA com integração OpenAI e fallback para Ollama.
    Usa RAG para buscar contexto relevante do banco de dados.
    """

    def __init__(self):
        self.deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.lemonfox_api_key = os.getenv("LEMONFOX_API_KEY")
        self.lemonfox_base_url = os.getenv("LEMONFOX_BASE_URL", "https://api.lemonfox.ai/v1")
        self.lemonfox_enabled = os.getenv("LEMONFOX_ENABLED", "false").lower() == "true"
        self.ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
        self.use_ollama_fallback = os.getenv("USE_OLLAMA_FALLBACK", "false").lower() == "true"

        print(f"[INIT] DeepSeek API Key: {'SET' if self.deepseek_api_key else 'NOT SET'}")
        print(f"[INIT] OpenAI API Key: {'SET' if self.openai_api_key else 'NOT SET'}")
        print(f"[INIT] Lemonfox API Key: {'SET' if self.lemonfox_api_key else 'NOT SET'}")
        print(f"[INIT] Lemonfox enabled: {self.lemonfox_enabled}")
        print(f"[INIT] Ollama fallback: {self.use_ollama_fallback}")

        # Inicializar clientes
        self.deepseek_client = None
        self.openai_client = None

        if self.deepseek_api_key:
            print("[INIT] Initializing DeepSeek client...")
            self.deepseek_client = OpenAI(
                api_key=self.deepseek_api_key,
                base_url="https://api.deepseek.com"
            )
            print("[INIT] DeepSeek client initialized!")

        if self.openai_api_key:
            self.openai_client = OpenAI(api_key=self.openai_api_key)

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
        if self.openai_client:
            try:
                response = await self._get_openai_response(messages)
                result = {
                    "response": response,
                    "model_used": "openai",
                    "context_used": context
                }
                if db is not None:
                    self._store_cache_entry(
                        db,
                        cache_key=cache_key,
                        scope=cache_scope,
                        operation=cache_operation,
                        provider="openai",
                        model="gpt-4o-mini",
                        request_json=cache_payload,
                        response_text=response,
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
                response = await self._get_deepseek_response(messages)
                print(f"[SUCCESS] DeepSeek responded: {len(response)} characters")
                result = {
                    "response": response,
                    "model_used": "deepseek",
                    "context_used": context
                }
                if db is not None:
                    self._store_cache_entry(
                        db,
                        cache_key=cache_key,
                        scope=cache_scope,
                        operation=cache_operation,
                        provider="deepseek",
                        model="deepseek-chat",
                        request_json=cache_payload,
                        response_text=response,
                    )
                    db.commit()
                return result
            except Exception as e:
                print(f"[ERROR] DeepSeek error: {e}")
                # Continua para próxima opção

        # 3) Ollama (fallback opcional)
        if self.use_ollama_fallback:
            try:
                response = await self._get_ollama_response(messages)
                result = {
                    "response": response,
                    "model_used": "ollama",
                    "context_used": context
                }
                if db is not None:
                    self._store_cache_entry(
                        db,
                        cache_key=cache_key,
                        scope=cache_scope,
                        operation=cache_operation,
                        provider="ollama",
                        model="llama3.2",
                        request_json=cache_payload,
                        response_text=response,
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
                response = await self._get_deepseek_response(messages)
                print(f"[SUCCESS] DeepSeek responded: {len(response)} characters")
                if db is not None and cache_key is not None and cache_payload is not None:
                    self._store_cache_entry(
                        db,
                        cache_key=cache_key,
                        scope=cache_scope,
                        operation=cache_operation,
                        provider="deepseek",
                        model="deepseek-chat",
                        request_json=cache_payload,
                        response_text=response,
                    )
                    db.commit()
                return {"response": response, "model_used": "deepseek", "context_used": None}
            except Exception as e:
                print(f"[ERROR] DeepSeek error: {e}")

        # 2) OpenAI (fallback)
        if self.openai_client:
            try:
                response = await self._get_openai_response(messages)
                if db is not None and cache_key is not None and cache_payload is not None:
                    self._store_cache_entry(
                        db,
                        cache_key=cache_key,
                        scope=cache_scope,
                        operation=cache_operation,
                        provider="openai",
                        model="gpt-4o-mini",
                        request_json=cache_payload,
                        response_text=response,
                    )
                    db.commit()
                return {"response": response, "model_used": "openai", "context_used": None}
            except Exception as e:
                print(f"OpenAI error: {e}")

        # 3) Ollama (fallback opcional)
        if self.use_ollama_fallback:
            try:
                response = await self._get_ollama_response(messages)
                if db is not None and cache_key is not None and cache_payload is not None:
                    self._store_cache_entry(
                        db,
                        cache_key=cache_key,
                        scope=cache_scope,
                        operation=cache_operation,
                        provider="ollama",
                        model="llama3.2",
                        request_json=cache_payload,
                        response_text=response,
                    )
                    db.commit()
                return {"response": response, "model_used": "ollama", "context_used": None}
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
        if self.openai_client:
            try:
                response = await self._get_openai_response(messages)
                if db is not None and cache_key is not None and cache_payload is not None:
                    self._store_cache_entry(
                        db,
                        cache_key=cache_key,
                        scope=cache_scope,
                        operation=cache_operation,
                        provider="openai",
                        model="gpt-4o-mini",
                        request_json=cache_payload,
                        response_text=response,
                    )
                    db.commit()
                return {"response": response, "model_used": "openai", "context_used": None}
            except Exception as e:
                print(f"OpenAI error (messages): {e}")

        # 2) DeepSeek (fallback)
        if self.deepseek_client:
            try:
                response = await self._get_deepseek_response(messages)
                if db is not None and cache_key is not None and cache_payload is not None:
                    self._store_cache_entry(
                        db,
                        cache_key=cache_key,
                        scope=cache_scope,
                        operation=cache_operation,
                        provider="deepseek",
                        model="deepseek-chat",
                        request_json=cache_payload,
                        response_text=response,
                    )
                    db.commit()
                return {"response": response, "model_used": "deepseek", "context_used": None}
            except Exception as e:
                print(f"DeepSeek error (messages): {e}")

        # 3) Ollama (fallback opcional)
        if self.use_ollama_fallback:
            try:
                response = await self._get_ollama_response(messages)
                if db is not None and cache_key is not None and cache_payload is not None:
                    self._store_cache_entry(
                        db,
                        cache_key=cache_key,
                        scope=cache_scope,
                        operation=cache_operation,
                        provider="ollama",
                        model="llama3.2",
                        request_json=cache_payload,
                        response_text=response,
                    )
                    db.commit()
                return {"response": response, "model_used": "ollama", "context_used": None}
            except Exception as e:
                print(f"Ollama error (messages): {e}")

        return {"response": "", "model_used": "none", "context_used": None}

    async def _get_deepseek_response(self, messages: List[Dict[str, str]]) -> str:
        """Obtém resposta da DeepSeek API"""
        try:
            response = self.deepseek_client.chat.completions.create(
                model="deepseek-chat",  # Modelo principal da DeepSeek
                messages=messages,
                temperature=0.7,
                max_tokens=1200  # Aumentado para conversas mais longas
            )
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"Erro na DeepSeek API: {str(e)}")

    async def generate_speech(
        self,
        text: str,
        voice: str = "nova",
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
        if db is not None:
            cache_payload = {
                "text": text[:4096],
                "voice": voice,
                "model": "tts-1",
                "speed": 0.95,
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
                            "speed": 0.95,
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
                    speed=0.95  # Um pouco mais devagar para aprendizes
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

    async def _get_openai_response(self, messages: List[Dict[str, str]]) -> str:
        """Obtém resposta da OpenAI API"""
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",  # Modelo mais barato e rápido
                messages=messages,
                temperature=0.7,
                max_tokens=800
            )
            return response.choices[0].message.content
        except OpenAIError as e:
            raise Exception(f"Erro na OpenAI API: {str(e)}")

    async def _get_ollama_response(self, messages: List[Dict[str, str]]) -> str:
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
                return ai_response

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

Seja claro, didático e encorajador."""

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
