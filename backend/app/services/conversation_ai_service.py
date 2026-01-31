"""Conversational AI service.

- Chat/LLM: DeepSeek (preferred) or OpenAI
- TTS: handled separately by /api/conversation/tts (OpenAI TTS)
"""
import uuid
import json
import re
from typing import Dict, List, Optional, Any
from datetime import datetime
from app.core.config import get_settings
from app.services.session_store import get_session_store

try:
    # OpenAI Python SDK v1+
    from openai import OpenAI  # type: ignore
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore

try:
    # OpenAI Python SDK <1.0 fallback
    import openai as openai_legacy  # type: ignore
except Exception:  # pragma: no cover
    openai_legacy = None  # type: ignore


class ConversationAIService:
    """Serviço de conversação que combina IA com Text-to-Speech"""
    
    def __init__(self):
        settings = get_settings()

        provider_pref = (settings.conversation_ai_provider or "auto").strip().lower()
        if provider_pref not in {"auto", "deepseek", "openai"}:
            raise ValueError(
                "CONVERSATION_AI_PROVIDER inválido. Use: auto|deepseek|openai"
            )

        # Chat provider selection
        if provider_pref in {"auto", "deepseek"} and settings.deepseek_api_key:
            self.ai_provider = "deepseek"
            self.model = settings.conversation_deepseek_model or "deepseek-chat"
            self._api_key = settings.deepseek_api_key
            self._base_url = "https://api.deepseek.com/v1"
        elif settings.openai_api_key:
            self.ai_provider = "openai"
            self.model = settings.conversation_openai_model or "gpt-4o-mini"
            self._api_key = settings.openai_api_key
            self._base_url = None
        else:
            raise ValueError("Nenhuma API key de IA configurada (OpenAI ou DeepSeek)")

        # Cliente SDK v1+ (preferencial); fallback para SDK antigo
        self.client = None
        if OpenAI is not None:
            if self._base_url:
                self.client = OpenAI(
                    api_key=self._api_key,
                    base_url=self._base_url,
                    timeout=settings.conversation_timeout_seconds,
                    max_retries=settings.conversation_max_retries,
                )
            else:
                self.client = OpenAI(
                    api_key=self._api_key,
                    timeout=settings.conversation_timeout_seconds,
                    max_retries=settings.conversation_max_retries,
                )
        elif openai_legacy is not None:
            openai_legacy.api_key = self._api_key
            if self._base_url:
                openai_legacy.api_base = self._base_url
            # NOTE: legacy SDK timeout/retry behavior depends on requests; keep defaults.
        else:
            raise ValueError("Biblioteca OpenAI não está instalada no backend")

        self.history_messages = max(1, int(settings.conversation_history_messages))
        self.max_tokens = max(50, int(settings.conversation_max_tokens))
        self.temperature = float(settings.conversation_temperature)
        self.store = get_session_store()
        self._prefix = "conversation:"
        ttl = int(getattr(settings, "session_ttl_seconds", 0) or 0)
        self.session_ttl_seconds = ttl if ttl > 0 else 6 * 60 * 60
    
    def _key(self, conversation_id: str) -> str:
        return f"{self._prefix}{conversation_id}"

    def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        return self.store.get(self._key(conversation_id))

    def _save_conversation(self, conversation_id: str, conversation: Dict[str, Any]) -> None:
        self.store.set(self._key(conversation_id), conversation, ttl_seconds=self.session_ttl_seconds)

    def _delete_conversation(self, conversation_id: str) -> None:
        self.store.delete(self._key(conversation_id))

    @property
    def active_conversations(self) -> Dict[str, Dict[str, Any]]:
        conversations: Dict[str, Dict[str, Any]] = {}
        for key in self.store.list_keys(self._prefix):
            conversation = self.store.get(key)
            if not isinstance(conversation, dict):
                continue
            conv_id = key[len(self._prefix) :]
            conversations[conv_id] = conversation
        return conversations

    def create_conversation(
        self,
        user_id: int,
        system_prompt: Optional[str] = None,
        voice_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Cria uma nova sessão de conversação
        
        Args:
            user_id: ID do usuário
            system_prompt: Prompt do sistema para configurar comportamento da IA
            voice_id: ID da voz do ElevenLabs
        
        Returns:
            Dados da conversação criada
        """
        conversation_id = str(uuid.uuid4())
        
        # Prompt padrão mais curto para respostas rápidas
        default_system_prompt = (
            "You are Alex, a friendly English coach for a Brazilian student. "
            "Keep replies concise and natural. Ask open-ended questions. "
            "If there are mistakes, add a short 'Coach's Corner' section with corrections in **bold** "
            "and 1-2 vocabulary tips. Prefer English."
        )
        
        conversation = {
            "id": conversation_id,
            "user_id": user_id,
            "created_at": datetime.utcnow().isoformat(),
            "system_prompt": system_prompt or default_system_prompt,
            "voice_id": voice_id,
            "messages": [],
            "status": "active",
            "lesson": None,
        }
        
        self._save_conversation(conversation_id, conversation)
        
        return {
            "conversation_id": conversation_id,
            "status": "active",
            "created_at": conversation["created_at"],
            "ai_provider": self.ai_provider
        }

    def _build_lesson_prompt(self, *, native_language: str, target_language: str, questions: List[str]) -> str:
        questions_block = "\n".join([f"- {q}" for q in questions])
        return (
            "You are an experienced language teacher. The student will answer a fixed list of questions in order. "
            f"Speak in {target_language} during the lesson. "
            "After each answer, respond naturally and briefly (1-3 sentences), without corrections. "
            "Only after the last answer, provide final feedback in the student's native language. "
            "Final feedback must include: corrections (with **bold** fixes), tips on better answers, "
            "pronunciation tips based on the written responses, and a final score (0-100)."
            "\nQuestions list (in order):\n"
            f"{questions_block}"
        )

    def create_lesson(
        self,
        user_id: int,
        questions: List[str],
        native_language: str = "pt-BR",
        target_language: str = "en",
        topic: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not questions:
            raise ValueError("Lista de perguntas vazia")

        conversation_id = str(uuid.uuid4())
        system_prompt = self._build_lesson_prompt(
            native_language=native_language,
            target_language=target_language,
            questions=questions,
        )

        conversation = {
            "id": conversation_id,
            "user_id": user_id,
            "created_at": datetime.utcnow().isoformat(),
            "system_prompt": system_prompt,
            "voice_id": None,
            "messages": [],
            "status": "active",
            "lesson": {
                "questions": questions,
                "current_index": 0,
                "native_language": native_language,
                "target_language": target_language,
                "topic": topic,
                "answers": [],
                "status": "active",
            },
        }

        self._save_conversation(conversation_id, conversation)

        return {
            "conversation_id": conversation_id,
            "status": "active",
            "created_at": conversation["created_at"],
            "first_question": questions[0],
            "total_questions": len(questions),
        }

    def generate_lesson_questions(self, *, topic: str, num_questions: int = 10) -> List[str]:
        n = max(3, min(int(num_questions), 15))
        variation_token = uuid.uuid4().hex[:8]
        prompt = (
            "Generate a list of short, natural English conversation questions for an ESL student. "
            f"Topic: {topic or 'general conversation'}. "
            "Make the list feel fresh and different each time. "
            f"Variation token: {variation_token}. "
            f"Return ONLY a JSON array with {n} questions."
        )

        messages = [
            {"role": "system", "content": "You are an English teacher. Return JSON only."},
            {"role": "user", "content": prompt},
        ]

        try:
            if self.client is not None:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=250,
                )
                raw = (response.choices[0].message.content or "").strip()
            else:
                response = openai_legacy.ChatCompletion.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=250,
                )
                raw = response.choices[0].message.content.strip()

            cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.IGNORECASE).strip()

            # Try JSON first
            try:
                data = json.loads(cleaned)
                if isinstance(data, list):
                    questions = [str(x).strip() for x in data if str(x).strip()]
                    return questions[:n]
                if isinstance(data, dict) and isinstance(data.get("questions"), list):
                    questions = [str(x).strip() for x in data["questions"] if str(x).strip()]
                    return questions[:n]
            except Exception:
                pass

            # Try to extract a JSON array inside the response
            array_match = re.search(r"\[[\s\S]*\]", cleaned)
            if array_match:
                try:
                    data = json.loads(array_match.group(0))
                    if isinstance(data, list):
                        questions = [str(x).strip() for x in data if str(x).strip()]
                        return questions[:n]
                except Exception:
                    pass

            # Fallback: split lines / bullets
            lines = [re.sub(r"^[\-\d\.\)\s]+", "", l).strip() for l in cleaned.splitlines()]
            questions = []
            for line in lines:
                if not line or line in ("{", "}", "[", "]"):
                    continue
                if line.lower().startswith('"questions"') or line.lower().startswith("'questions'"):
                    continue
                sanitized = line.strip().strip('"').strip("'").rstrip(',').strip()
                if sanitized:
                    questions.append(sanitized)
            return questions[:n]

        except Exception as e:
            raise ValueError(f"Erro ao gerar perguntas: {str(e)}")

    def send_lesson_message(self, conversation_id: str, user_message: str) -> Dict[str, Any]:
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            raise ValueError(f"Conversa nao encontrada: {conversation_id}")

        lesson = conversation.get("lesson")
        if not lesson or lesson.get("status") != "active":
            raise ValueError("Lição não ativa")

        questions: List[str] = lesson["questions"]
        idx = int(lesson["current_index"])
        is_last = idx >= len(questions) - 1

        lesson["answers"].append(user_message)

        conversation["messages"].append({
            "role": "user",
            "content": user_message,
            "timestamp": datetime.utcnow().isoformat(),
        })

        messages = [
            {"role": "system", "content": conversation["system_prompt"]}
        ]

        recent_messages = conversation["messages"][-min(self.history_messages, 6) :]
        for msg in recent_messages:
            messages.append({"role": msg["role"], "content": msg["content"]})

        if is_last:
            qa_pairs = []
            for i, question in enumerate(questions):
                answer = lesson["answers"][i] if i < len(lesson["answers"]) else ""
                qa_pairs.append(f"Q{i + 1}: {question}\nA{i + 1}: {answer}")
            qa_block = "\n\n".join(qa_pairs)
            messages.append({
                "role": "system",
                "content": (
                    f"This was the last answer. Provide FINAL feedback in {lesson['native_language']} only. "
                    "Use the FULL lesson transcript below to correct mistakes across all answers. "
                    "Include corrections with **bold**, tips, pronunciation advice, and a final score (0-100). "
                    "Add a line exactly like: Score: 85\n\n"
                    "Full lesson transcript (questions and student answers):\n"
                    f"{qa_block}"
                ),
            })
        else:
            next_question = questions[idx + 1]
            messages.append({
                "role": "system",
                "content": f"After your response, ask EXACTLY this next question: {next_question}",
            })

        try:
            max_tokens = max(120, min(self.max_tokens, 450))
            final_max_tokens = max(300, min(self.max_tokens, 900))
            lesson_max_tokens = final_max_tokens if is_last else max_tokens
            if self.client is not None:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=lesson_max_tokens,
                )
                ai_response = (response.choices[0].message.content or "").strip()
            else:
                response = openai_legacy.ChatCompletion.create(
                    model=self.model,
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=lesson_max_tokens,
                )
                ai_response = response.choices[0].message.content.strip()

        except Exception as e:
            raise ValueError(f"Erro ao gerar resposta da IA: {str(e)}")

        conversation["messages"].append({
            "role": "assistant",
            "content": ai_response,
            "timestamp": datetime.utcnow().isoformat(),
        })


        if is_last:
            lesson["status"] = "ended"
        else:
            lesson["current_index"] = idx + 1

        self._save_conversation(conversation_id, conversation)

        result = {
            "conversation_id": conversation_id,
            "user_message": user_message,
            "ai_response": ai_response,
            "is_final": is_last,
            "current_index": lesson["current_index"],
            "total_questions": len(questions),
            "timestamp": datetime.utcnow().isoformat(),
        }
        if not is_last:
            result["next_question"] = questions[idx + 1]
        return result
    
    def send_message(
        self,
        conversation_id: str,
        user_message: str,
        generate_audio: bool = True
    ) -> Dict[str, Any]:
        """
        Envia mensagem e obtém resposta da IA com áudio
        
        Args:
            conversation_id: ID da conversação
            user_message: Mensagem do usuário
            generate_audio: Se deve gerar áudio da resposta
        
        Returns:
            Resposta da IA com texto e áudio (opcional)
        """
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            raise ValueError(f"Conversa nao encontrada: {conversation_id}")
        
        # Adiciona mensagem do usuário
        conversation["messages"].append({
            "role": "user",
            "content": user_message,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Prepara mensagens para a IA
        messages = [
            {"role": "system", "content": conversation["system_prompt"]}
        ]
        
        # Adiciona histórico recente
        recent_messages = conversation["messages"][-self.history_messages :]
        for msg in recent_messages:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        # Obtém resposta da IA
        try:
            if self.client is not None:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                )
                ai_response = (response.choices[0].message.content or "").strip()
            else:
                # SDK antigo
                response = openai_legacy.ChatCompletion.create(
                    model=self.model,
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                )
                ai_response = response.choices[0].message.content.strip()

        except Exception as e:
            raise ValueError(f"Erro ao gerar resposta da IA: {str(e)}")
        
        # Adiciona resposta da IA ao histórico
        conversation["messages"].append({
            "role": "assistant",
            "content": ai_response,
            "timestamp": datetime.utcnow().isoformat()
        })

        self._save_conversation(conversation_id, conversation)
        
        result = {
            "conversation_id": conversation_id,
            "user_message": user_message,
            "ai_response": ai_response,
            "timestamp": datetime.utcnow().isoformat()
        }

        # Audio is handled by /api/conversation/tts (OpenAI TTS).
        result["has_audio"] = False
        
        return result
    
    def get_conversation_history(self, conversation_id: str) -> List[Dict[str, Any]]:
        """
        Obtem historico de mensagens de uma conversa
        
        Args:
            conversation_id: ID da conversa
        
        Returns:
            Lista de mensagens
        """
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            raise ValueError(f"Conversa nao encontrada: {conversation_id}")
        return conversation["messages"]

    def end_conversation(self, conversation_id: str) -> Dict[str, Any]:
        """
        Encerra uma conversa
        
        Args:
            conversation_id: ID da conversa
        
        Returns:
            Resumo da conversa encerrada
        """
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            raise ValueError(f"Conversa nao encontrada: {conversation_id}")

        conversation["status"] = "ended"
        conversation["ended_at"] = datetime.utcnow().isoformat()
        self._save_conversation(conversation_id, conversation)

        # Mantem em memoria por enquanto (pode ser removido apos migrar para DB)
        summary = {
            "conversation_id": conversation_id,
            "status": "ended",
            "created_at": conversation["created_at"],
            "ended_at": conversation["ended_at"],
            "message_count": len(conversation["messages"]),
            "duration_seconds": (
                datetime.fromisoformat(conversation["ended_at"])
                - datetime.fromisoformat(conversation["created_at"])
            ).total_seconds(),
        }

        return summary

    def list_active_conversations(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Lista conversações ativas de um usuário
        
        Args:
            user_id: ID do usuário
        
        Returns:
            Lista de conversações ativas
        """
        active = []
        
        for conv_id, conv in self.active_conversations.items():
            if conv["user_id"] == user_id and conv["status"] == "active":
                active.append({
                    "conversation_id": conv_id,
                    "created_at": conv["created_at"],
                    "message_count": len(conv["messages"]),
                    "last_message": (
                        conv["messages"][-1]["content"][:50] + "..."
                        if conv["messages"]
                        else None
                    )
                })
        
        return active


# Instância global do serviço
conversation_ai_service = ConversationAIService()
