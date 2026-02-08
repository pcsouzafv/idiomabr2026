# 🎙️ Módulo de Conversação com ElevenLabs

## 📋 Visão Geral

Este módulo implementa um sistema completo de conversação full-time usando a API da ElevenLabs. Permite que os usuários pratiquem inglês através de conversas com IA, incluindo:

- **Text-to-Speech (TTS)**: Conversão de texto em áudio natural
- **Conversational AI**: Sistema de conversação inteligente
- **Multiple Voices**: Suporte a diferentes vozes do ElevenLabs
- **Real-time Chat**: Interface de chat em tempo real

## 🔧 Configuração

### 1. Obter API Key da ElevenLabs

1. Acesse [ElevenLabs](https://elevenlabs.io)
2. Crie uma conta ou faça login
3. Vá para [API Settings](https://elevenlabs.io/app/subscription)
4. Copie sua API key

### 2. Configurar Variáveis de Ambiente

Adicione as seguintes variáveis ao arquivo `.env`:

```bash
# ElevenLabs API
ELEVENLABS_API_KEY=sua_api_key_aqui
ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM  # Rachel (padrão) - opcional

# Conversational AI (Chat)
# Use DEEPSEEK_API_KEY (OpenAI-compatible) ou OPENAI_API_KEY
DEEPSEEK_API_KEY=sua_api_key_deepseek  # opcional
OPENAI_API_KEY=sua_api_key_openai      # opcional

# Opcional: ajustes para evitar resposta "cortada" e melhorar desempenho
CONVERSATION_AI_PROVIDER=auto          # auto|deepseek|openai (dica: openai costuma responder mais rápido)
CONVERSATION_MAX_TOKENS=700            # aumente se o Coach's Corner estiver cortando
CONVERSATION_HISTORY_MESSAGES=10
CONVERSATION_TIMEOUT_SECONDS=30
CONVERSATION_MAX_RETRIES=1
```

### 3. Instalar Dependências

O módulo utiliza `requests` que já deve estar instalado. Se necessário:

```bash
cd backend
pip install requests
```

## 📁 Estrutura de Arquivos

```
backend/
├── app/
│   ├── services/
│   │   └── elevenlabs_service.py      # Serviço de integração com ElevenLabs
│   ├── routes/
│   │   └── conversation.py            # Endpoints de API
│   ├── schemas/
│   │   └── conversation.py            # Schemas Pydantic
│   └── core/
│       └── config.py                  # Configurações (API keys)

frontend/
└── src/
    └── app/
        └── conversation/
            └── page.tsx               # Interface de conversação
```

## 🚀 Como Usar

### Backend - Endpoints Disponíveis

#### 1. Text-to-Speech

Converte texto em áudio:

```bash
POST /api/conversation/tts
{
  "text": "Hello, how are you?",
  "voice_id": "21m00Tcm4TlvDq8ikWAM",  # opcional
  "model_id": "eleven_multilingual_v2"
}
```

#### 2. Listar Vozes

Lista todas as vozes disponíveis:

```bash
GET /api/conversation/voices
```

#### 3. Iniciar Conversação

Cria uma nova sessão de conversação:

```bash
POST /api/conversation/start
{
  "system_prompt": "You are a friendly English teacher...",
  "initial_message": "Hello! Let's practice English."
}
```

Resposta:
```json
{
  "conversation_id": "uuid-aqui",
  "status": "active",
  "created_at": "2026-01-09T..."
}
```

#### 4. Enviar Mensagem

Envia mensagem na conversação:

```bash
POST /api/conversation/{conversation_id}/message
{
  "message": "I want to improve my vocabulary"
}
```

Resposta:
```json
{
  "message_id": "uuid",
  "conversation_id": "uuid",
  "user_message": "I want to improve my vocabulary",
  "ai_response": "That's great! Let's start with...",
  "timestamp": "2026-01-09T..."
}
```

#### 5. Histórico da Conversação

Obtém todo o histórico:

```bash
GET /api/conversation/{conversation_id}/history
```

#### 6. Encerrar Conversação

Finaliza a conversação:

```bash
POST /api/conversation/{conversation_id}/end
{
  "feedback": "Great session!"  # opcional
}
```

#### 7. Listar Conversações Ativas

Lista conversações ativas do usuário:

```bash
GET /api/conversation/active/list
```

### Frontend - Interface de Conversação

Acesse: `http://localhost:3000/conversation`

**Funcionalidades:**

1. **Configuração Inicial**
   - Escolher voz preferida
   - Configurar system prompt (personalidade da IA)
   - Ativar/desativar auto-play de áudio

2. **Conversação em Tempo Real**
   - Chat interface intuitiva
   - Mensagens com timestamp
   - Indicador de "digitando..."
   - Reprodução automática de áudio (opcional)

3. **Controles de Áudio**
   - Botão para reproduzir cada resposta
   - Controle de volume
   - Indicador de "falando..."

4. **Gerenciamento**
   - Visualizar histórico completo
   - Encerrar conversação
   - Feedback opcional

## 🎯 Casos de Uso

### 1. Prática de Conversação Básica

```python
# Exemplo de uso via API
import requests

# Iniciar conversação
response = requests.post(
    "http://localhost:8000/api/conversation/start",
    headers={"Authorization": "Bearer seu_token"},
    json={
        "system_prompt": "You are a friendly English teacher",
        "initial_message": "Hello!"
    }
)

conversation_id = response.json()["conversation_id"]

# Enviar mensagens
response = requests.post(
    f"http://localhost:8000/api/conversation/{conversation_id}/message",
    headers={"Authorization": "Bearer seu_token"},
    json={"message": "Can you help me practice present perfect?"}
)

print(response.json()["ai_response"])
```

### 2. Geração de Áudio para Palavras

```python
# Converter palavra em áudio
response = requests.post(
    "http://localhost:8000/api/conversation/tts",
    headers={"Authorization": "Bearer seu_token"},
    json={"text": "Beautiful"}
)

# Salvar áudio
with open("beautiful.mp3", "wb") as f:
    f.write(response.content)
```

### 3. Conversação Temática

```typescript
// Frontend - Iniciar conversa sobre viagens
const response = await conversationApi.startConversation({
  system_prompt: `You are an English teacher specializing in travel vocabulary. 
    Help students learn phrases and vocabulary useful for traveling. 
    Use real-life scenarios and examples.`,
  initial_message: "I'm planning a trip to New York. Can you help me?"
});
```

## 🎨 Personalização

### Configurar Diferentes Vozes

```python
# No backend - elevenlabs_service.py
# Você pode configurar vozes diferentes para diferentes contextos

# Voz masculina
male_voice = "pNInz6obpgDQGcFmaJgB"  # Adam

# Voz feminina
female_voice = "21m00Tcm4TlvDq8ikWAM"  # Rachel

# Usar na conversão
audio = elevenlabs_service.text_to_speech(
    text="Hello",
    voice_id=male_voice
)
```

### Ajustar Configurações de Voz

```python
voice_settings = {
    "stability": 0.7,        # 0-1 (maior = mais estável)
    "similarity_boost": 0.8, # 0-1 (maior = mais próximo da voz original)
    "style": 0.5,            # 0-1 (exageração de estilo)
    "use_speaker_boost": True
}

audio = elevenlabs_service.text_to_speech(
    text="Hello",
    voice_settings=voice_settings
)
```

## 📊 Limites e Quotas

A API da ElevenLabs tem limites baseados no seu plano:

- **Free Tier**: ~10,000 caracteres/mês
- **Starter**: ~30,000 caracteres/mês
- **Creator**: ~100,000 caracteres/mês
- **Pro**: ~500,000 caracteres/mês

Monitore seu uso em: https://elevenlabs.io/app/subscription

## 🔐 Segurança

1. **Nunca** exponha sua API key no frontend
2. Sempre use autenticação JWT nos endpoints
3. Implemente rate limiting para evitar abuso
4. Valide e sanitize inputs do usuário

## 🐛 Troubleshooting

### Erro: "API key não configurada"

**Solução**: Configure `ELEVENLABS_API_KEY` no `.env`

### Áudio não reproduz no frontend

**Possíveis causas**:
1. Verifique se o navegador suporta áudio MP3
2. Verifique se há bloqueio de autoplay
3. Verifique console do navegador para erros

### Erro 401 - Unauthorized

**Solução**: Verifique se sua API key é válida em https://elevenlabs.io

### Latência alta

**Soluções**:
1. Use vozes com modelos mais rápidos
2. Reduza `similarity_boost` nas configurações
3. Considere cachear áudios de frases comuns

## 🚀 Melhorias Futuras

- [ ] **Speech-to-Text**: Adicionar reconhecimento de voz para input
- [ ] **Persistência**: Salvar conversações no banco de dados
- [ ] **Analytics**: Rastrear métricas de uso e progresso
- [ ] **Voice Cloning**: Permitir usuários clonarem suas próprias vozes
- [ ] **Multilingual**: Suporte a múltiplos idiomas
- [ ] **Mobile App**: Interface mobile nativa

## 📚 Recursos Adicionais

- [ElevenLabs API Docs](https://elevenlabs.io/docs)
- [Voice Library](https://elevenlabs.io/voice-library)
- [Pricing](https://elevenlabs.io/pricing)

## 💡 Dicas de Uso

1. **Use system prompts específicos** para diferentes contextos de aprendizado
2. **Ajuste voice settings** para encontrar a configuração ideal para seus alunos
3. **Implemente cache** para frases/palavras comuns para economizar créditos
4. **Monitore uso da API** para evitar ultrapassar limites
5. **Colete feedback** dos usuários sobre qualidade da voz e conversação

## 📞 Suporte

Para problemas relacionados a:
- **ElevenLabs API**: https://elevenlabs.io/support
- **IdiomasBR**: Abra uma issue no repositório

---

**Desenvolvido com ❤️ para IdiomasBR**
