"""
Schemas para o módulo de conversação com ElevenLabs
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class VoiceInfo(BaseModel):
    """Informações sobre uma voz do ElevenLabs"""
    voice_id: str
    name: str
    category: Optional[str] = None
    description: Optional[str] = None
    preview_url: Optional[str] = None
    labels: Optional[Dict[str, str]] = None


class VoiceListResponse(BaseModel):
    """Resposta da listagem de vozes"""
    voices: List[VoiceInfo]


class TextToSpeechRequest(BaseModel):
    """Request para conversão de texto em fala"""
    text: str = Field(..., description="Texto a ser convertido em fala", min_length=1, max_length=5000)
    voice_id: Optional[str] = Field(None, description="ID da voz (opcional)")
    model_id: str = Field("eleven_multilingual_v2", description="Modelo de voz")
    voice_settings: Optional[Dict[str, Any]] = None


class ConversationCreateRequest(BaseModel):
    """Request para criar uma nova conversação"""
    system_prompt: Optional[str] = Field(
        "You are a helpful English teacher assistant. "
        "Help students practice English conversation in a friendly and encouraging way. "
        "Correct mistakes gently and provide explanations when needed.",
        description="Prompt do sistema para a IA"
    )
    agent_id: Optional[str] = Field(None, description="ID do agente customizado")
    initial_message: Optional[str] = Field(
        None,
        description="Mensagem inicial do usuário"
    )


class LessonStartRequest(BaseModel):
    """Request para iniciar uma lição com perguntas fixas"""
    questions: List[str] = Field(..., description="Lista de perguntas em inglês", min_length=1)
    native_language: str = Field("pt-BR", description="Língua nativa do aluno")
    target_language: str = Field("en", description="Língua alvo para conversação")
    topic: Optional[str] = Field(None, description="Tema/objetivo da lição")
    num_questions: Optional[int] = Field(None, description="Quantidade planejada de perguntas")


class LessonStartResponse(BaseModel):
    """Resposta ao iniciar lição"""
    conversation_id: str
    status: str
    first_question: str
    total_questions: int


class LessonMessageRequest(BaseModel):
    """Request para responder uma pergunta da lição"""
    message: str = Field(..., description="Resposta do aluno", min_length=1)


class LessonMessageResponse(BaseModel):
    """Resposta de mensagem na lição"""
    conversation_id: str
    user_message: str
    ai_response: str
    is_final: bool
    current_index: int
    total_questions: int
    next_question: Optional[str] = None


class LessonGenerateRequest(BaseModel):
    """Request para gerar perguntas de lição"""
    topic: str = Field(..., description="Tema/objetivo da lição")
    num_questions: int = Field(10, ge=3, le=15, description="Quantidade de perguntas")


class LessonGenerateResponse(BaseModel):
    """Resposta com perguntas geradas"""
    questions: List[str]


class PronunciationResponse(BaseModel):
    """Resposta da análise de pronúncia"""
    transcript: str
    similarity: Optional[int] = None
    feedback: str


class LessonAttemptResponse(BaseModel):
    """Resumo de uma lição concluída"""
    id: int
    created_at: datetime
    questions: List[str]
    answers: List[str]
    ai_feedback: Optional[str] = None
    topic: Optional[str] = None
    num_questions: Optional[int] = None
    score: Optional[int] = None


class PronunciationAttemptResponse(BaseModel):
    """Detalhe de uma tentativa de pronúncia"""
    question_index: Optional[int] = None
    transcript: str
    similarity: Optional[int] = None
    feedback: str
    created_at: datetime


class LessonAttemptDetailResponse(BaseModel):
    """Detalhes completos da lição com pronúncia"""
    attempt: LessonAttemptResponse
    pronunciations: List[PronunciationAttemptResponse]


class ConversationResponse(BaseModel):
    """Resposta da criação de conversação"""
    conversation_id: str
    status: str
    created_at: Optional[datetime] = None


class MessageRequest(BaseModel):
    """Request para enviar mensagem na conversação"""
    message: str = Field(..., description="Mensagem do usuário", min_length=1)


class MessageResponse(BaseModel):
    """Resposta de uma mensagem na conversação"""
    message_id: str
    conversation_id: str
    user_message: str
    ai_response: str
    audio_url: Optional[str] = None
    timestamp: Optional[datetime] = None


class ConversationHistoryResponse(BaseModel):
    """Histórico completo de uma conversação"""
    conversation_id: str
    messages: List[Dict[str, Any]]
    total_messages: int


class ConversationEndRequest(BaseModel):
    """Request para encerrar conversação"""
    feedback: Optional[str] = Field(None, description="Feedback opcional do usuário")


class ConversationEndResponse(BaseModel):
    """Resposta do encerramento de conversação"""
    conversation_id: str
    status: str
    total_messages: int
    duration_seconds: Optional[int] = None
