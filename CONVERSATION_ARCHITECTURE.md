# Arquitetura do Módulo de Conversação

## 📋 Visão Geral

O módulo de conversação combina **ElevenLabs Text-to-Speech** com **IA (OpenAI ou DeepSeek)** para criar conversações inteligentes com resposta em áudio.

## 🏗️ Arquitetura

```
┌─────────────────┐
│   Frontend      │
│  (Next.js)      │
└────────┬────────┘
         │
         │ HTTP/REST
         │
┌────────▼────────────────────────────────┐
│       Backend FastAPI                   │
│                                         │
│  ┌──────────────────────────────────┐  │
│  │  conversation.py (Routes)        │  │
│  └──────────┬───────────────────────┘  │
│             │                           │
│  ┌──────────▼───────────────────────┐  │
│  │  conversation_ai_service.py      │  │
│  │  - Gerencia conversações         │  │
│  │  - Integra IA com TTS            │  │
│  └──────┬──────────────┬────────────┘  │
│         │              │                │
│  ┌──────▼─────┐  ┌────▼──────────────┐ │
│  │  OpenAI/   │  │  ElevenLabs       │ │
│  │  DeepSeek  │  │  TTS Service      │ │
│  │            │  │                   │ │
│  │  - GPT-3.5 │  │  - text_to_speech │ │
│  │  - DeepSeek│  │  - get_voices     │ │
│  └────────────┘  └───────────────────┘ │
└─────────────────────────────────────────┘
         │              │
         │              │
┌────────▼────────┐ ┌──▼────────────────┐
│   OpenAI API    │ │  ElevenLabs API   │
│                 │ │                   │
│  api.openai.com │ │  api.elevenlabs.io│
└─────────────────┘ └───────────────────┘
```

## 🔧 Componentes

### 1. **conversation_ai_service.py**
Serviço principal que orquestra a conversação:

- **Funcionalidades:**
  - Gerencia sessões de conversação em memória
  - Integra com OpenAI/DeepSeek para respostas inteligentes
  - Converte respostas da IA em áudio via ElevenLabs TTS
  - Mantém histórico de mensagens
  - Controla contexto e system prompts

- **Métodos principais:**
  - `create_conversation()`: Cria nova conversação
  - `send_message()`: Envia mensagem e retorna resposta com áudio
  - `get_conversation_history()`: Obtém histórico
  - `end_conversation()`: Encerra conversação
  - `list_active_conversations()`: Lista conversações ativas

### 2. **elevenlabs_service.py**
Integração direta com ElevenLabs API:

- **Funcionalidades:**
  - `text_to_speech()`: Converte texto em MP3
  - `get_voices()`: Lista vozes disponíveis
  - ~~`create_conversation_session()`~~: Retorna stub (modo TTS-only)
  - ~~`send_conversation_message()`~~: Retorna stub (modo TTS-only)

**Nota:** Os métodos de conversação foram modificados para retornar stubs porque a API Conversacional da ElevenLabs requer plano específico.

### 3. **routes/conversation.py**
Endpoints REST para o frontend:

- `POST /api/conversation/tts`: Text-to-speech direto
- `GET /api/conversation/voices`: Lista vozes
- `POST /api/conversation/start`: Inicia conversação
- `POST /api/conversation/{id}/message`: Envia mensagem
- `GET /api/conversation/{id}/history`: Histórico
- `POST /api/conversation/{id}/end`: Encerra conversação
- `GET /api/conversation/active/list`: Lista conversações ativas

## 🔄 Fluxo de Conversação

### 1. **Iniciar Conversação**
```
Frontend → POST /api/conversation/start
{
  "system_prompt": "You are a friendly English teacher...",
  "voice_id": "21m00Tcm4TlvDq8ikWAM"
}

Backend:
1. Cria UUID para conversação
2. Armazena em memória com system prompt
3. Retorna conversation_id

Frontend ← { "conversation_id": "uuid", "status": "active" }
```

### 2. **Enviar Mensagem**
```
Frontend → POST /api/conversation/{id}/message
{
  "message": "How do I say 'hello' in English?"
}

Backend:
1. Adiciona mensagem ao histórico
2. Monta contexto (system + últimas 10 mensagens)
3. Chama OpenAI/DeepSeek para resposta
4. Converte resposta em áudio (ElevenLabs TTS)
5. Retorna texto + áudio

Frontend ← {
  "ai_response": "You can say 'hello' or 'hi'...",
  "audio": <binary_data>
}
```

### 3. **Obter Histórico**
```
Frontend → GET /api/conversation/{id}/history

Backend:
1. Busca conversação em memória
2. Retorna lista de mensagens

Frontend ← {
  "messages": [
    { "role": "user", "content": "...", "timestamp": "..." },
    { "role": "assistant", "content": "...", "timestamp": "..." }
  ],
  "total_messages": 10
}
```

### 4. **Encerrar Conversação**
```
Frontend → POST /api/conversation/{id}/end

Backend:
1. Calcula duração e total de mensagens
2. Marca como "ended"
3. Remove da memória (ou mantém para histórico)
4. Retorna resumo

Frontend ← {
  "status": "ended",
  "total_messages": 15,
  "duration_seconds": 420
}
```

## 📦 Configuração Necessária

### Variáveis de Ambiente (.env)
```env
# ElevenLabs
ELEVENLABS_API_KEY=sk_...
ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM

# OpenAI (ou DeepSeek)
OPENAI_API_KEY=sk-...
# OU
DEEPSEEK_API_KEY=sk-...
```

### Dependências Python
```
openai>=0.27.0
requests>=2.31.0
pydantic>=2.0.0
pydantic-settings>=2.1.0
fastapi>=0.104.0
```

## 🎯 Modelo de IA

O serviço prioriza APIs na seguinte ordem:

1. **OpenAI** (`OPENAI_API_KEY` definida):
   - Modelo: `gpt-3.5-turbo`
   - API: `https://api.openai.com/v1`

2. **DeepSeek** (`DEEPSEEK_API_KEY` definida):
   - Modelo: `deepseek-chat`
   - API: `https://api.deepseek.com/v1`

**Configuração da Resposta:**
- `temperature`: 0.7 (balanço criatividade/consistência)
- `max_tokens`: 150 (respostas curtas para conversação)
- Histórico: Últimas 10 mensagens enviadas como contexto

## 🎤 Text-to-Speech

**Configuração Padrão:**
```python
{
  "stability": 0.5,        # Consistência da voz
  "similarity_boost": 0.75, # Similaridade com voz original
  "style": 0.0,            # Estilo de fala
  "use_speaker_boost": True # Melhora qualidade
}
```

**Modelo:** `eleven_multilingual_v2` (suporta múltiplos idiomas)

**Formato de Saída:** MP3 (áudio comprimido)

## 💾 Armazenamento

### Atual (Em Memória)
```python
active_conversations = {
  "uuid": {
    "user_id": 123,
    "created_at": "2026-01-09T...",
    "system_prompt": "...",
    "voice_id": "...",
    "messages": [...]
  }
}
```

### Futuro (Database)
TODO: Migrar para PostgreSQL
- Tabela `conversations`
- Tabela `conversation_messages`
- Relacionamento com `users`

## 🔐 Segurança

1. **Autenticação:** JWT via `get_current_user()`
2. **Autorização:** Verifica `user_id` nas conversações
3. **Validação:** Schemas Pydantic para requests/responses
4. **Rate Limiting:** TODO (implementar throttling)

## 🚀 Próximos Passos

1. **Persistência:** Migrar de memória para PostgreSQL
2. **Audio Storage:** Salvar áudios em cloud storage (S3/GCS)
3. **Speech-to-Text:** Adicionar Whisper para entrada por voz
4. **WebSockets:** Conversação em tempo real
5. **Analytics:** Tracking de métricas de uso
6. **Cache:** Redis para conversações recentes

## 📚 Referências

- [ElevenLabs API Docs](https://elevenlabs.io/docs)
- [OpenAI API Docs](https://platform.openai.com/docs)
- [DeepSeek API Docs](https://platform.deepseek.com/docs)
