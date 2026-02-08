"""
Serviço para integração com ElevenLabs API
Fornece funcionalidades de conversação com IA e text-to-speech
"""
import requests
import json
from typing import Optional, Dict, Any, List
from app.core.config import get_settings


class ElevenLabsService:
    """Serviço para integração com ElevenLabs API"""
    
    BASE_URL = "https://api.elevenlabs.io/v1"
    
    def __init__(self):
        settings = get_settings()
        self.api_key = settings.elevenlabs_api_key
        self.voice_id = settings.elevenlabs_voice_id
        self.headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json"
        }
    
    def _check_api_key(self):
        """Verifica se a API key está configurada"""
        if not self.api_key:
            raise ValueError(
                "ElevenLabs API key não configurada. "
                "Configure ELEVENLABS_API_KEY no arquivo .env"
            )
    
    def text_to_speech(
        self,
        text: str,
        voice_id: Optional[str] = None,
        model_id: str = "eleven_multilingual_v2",
        voice_settings: Optional[Dict[str, Any]] = None
    ) -> bytes:
        """
        Converte texto em áudio usando ElevenLabs
        
        Args:
            text: Texto a ser convertido
            voice_id: ID da voz (opcional, usa default se não fornecido)
            model_id: ID do modelo de voz
            voice_settings: Configurações personalizadas da voz
        
        Returns:
            bytes: Dados de áudio em formato MP3
        """
        self._check_api_key()

        if not text or not text.strip():
            raise ValueError("Texto vazio para TTS")
        
        voice_id = (voice_id or self.voice_id or "").strip()
        if not voice_id:
            raise ValueError(
                "ElevenLabs VOICE_ID não configurado. "
                "Configure ELEVENLABS_VOICE_ID no arquivo .env"
            )
        url = f"{self.BASE_URL}/text-to-speech/{voice_id}"
        
        # Configurações padrão da voz
        default_voice_settings = {
            "stability": 0.5,
            "similarity_boost": 0.75,
            "style": 0.0,
            "use_speaker_boost": True
        }
        
        payload = {
            "text": text,
            "model_id": model_id,
            "voice_settings": voice_settings or default_voice_settings
        }
        
        response = requests.post(url, json=payload, headers=self.headers, timeout=30)
        response.raise_for_status()
        
        return response.content
    
    def get_voices(self) -> List[Dict[str, Any]]:
        """
        Lista todas as vozes disponíveis
        
        Returns:
            Lista de vozes com seus metadados
        """
        self._check_api_key()
        
        url = f"{self.BASE_URL}/voices"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        
        return response.json().get("voices", [])
    
    def create_conversation_session(
        self,
        agent_id: Optional[str] = None,
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Cria uma nova sessão de conversação com IA
        
        NOTA: ElevenLabs Conversational AI requer plano específico.
        Esta implementação usa apenas TTS. A lógica de conversação
        é gerenciada pelo backend com OpenAI/DeepSeek.
        
        Args:
            agent_id: ID do agente de IA (não usado nesta versão)
            system_prompt: Prompt do sistema (não usado nesta versão)
        
        Returns:
            Dados da sessão simulada (TTS apenas)
        """
        self._check_api_key()
        
        # Para conversação completa, usamos apenas TTS da ElevenLabs
        # e combinamos com IA (OpenAI/DeepSeek) no backend
        return {
            "conversation_id": f"tts_session_{id(self)}",
            "status": "active",
            "voice_id": self.voice_id,
            "note": "Using TTS-only mode. AI logic handled by backend."
        }
    
    def send_conversation_message(
        self,
        conversation_id: str,
        message: str,
        audio_input: Optional[bytes] = None
    ) -> Dict[str, Any]:
        """
        Envia uma mensagem para uma conversa ativa
        
        NOTA: Esta versão não usa a API de conversação da ElevenLabs.
        Retorna apenas confirmação. A resposta de IA deve ser gerada
        pelo backend usando OpenAI/DeepSeek, e o áudio gerado via TTS.
        
        Args:
            conversation_id: ID da conversação
            message: Mensagem de texto do usuário
            audio_input: Áudio de entrada (não usado nesta versão)
        
        Returns:
            Confirmação de recebimento
        """
        self._check_api_key()
        
        # Retorna confirmação simples
        # A lógica de IA será implementada no backend
        return {
            "conversation_id": conversation_id,
            "user_message": message,
            "status": "received",
            "note": "AI response should be generated by backend and converted to speech via TTS"
        }
    
    def get_conversation_history(
        self,
        conversation_id: str
    ) -> List[Dict[str, Any]]:
        """
        Obtém o histórico de uma conversação
        
        NOTA: Histórico deve ser gerenciado pelo backend/database,
        não pela API da ElevenLabs.
        
        Args:
            conversation_id: ID da conversação
        
        Returns:
            Lista vazia (histórico gerenciado pelo backend)
        """
        self._check_api_key()
        
        # Histórico será gerenciado pelo database do backend
        return []
    
    def end_conversation(self, conversation_id: str) -> Dict[str, Any]:
        """
        Encerra uma conversação
        
        NOTA: Apenas retorna confirmação. O encerramento real
        deve ser gerenciado pelo backend.
        
        Args:
            conversation_id: ID da conversação
        
        Returns:
            Confirmação do encerramento
        """
        self._check_api_key()
        
        return {
            "conversation_id": conversation_id,
            "status": "ended",
            "note": "Conversation ended successfully"
        }
    
    def speech_to_text(self, audio_data: bytes) -> str:
        """
        Converte áudio em texto (transcrição)
        Nota: ElevenLabs pode não ter endpoint direto para STT,
        neste caso, pode-se integrar com Whisper da OpenAI
        
        Args:
            audio_data: Dados de áudio
        
        Returns:
            Texto transcrito
        """
        # Implementação futura se necessário
        # Por enquanto, retorna placeholder
        raise NotImplementedError(
            "Speech-to-text direto não implementado. "
            "Use Whisper da OpenAI para transcrição."
        )


# Instância global do serviço
elevenlabs_service = ElevenLabsService()
