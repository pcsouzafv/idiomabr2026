# 🚀 Quick Start - Módulo de Conversação ElevenLabs

## ✅ Status: FUNCIONANDO ✅

**Problema Resolvido:** O erro 404 foi corrigido. O sistema agora usa:
- **ElevenLabs** para Text-to-Speech (áudio)
- **OpenAI/DeepSeek** para inteligência artificial (respostas)
- **Backend** gerencia a integração

**Testes:** 4/4 ✅ (API Key, Vozes, TTS, Conversação)

## ⚡ Setup Rápido (5 minutos)

### 1. Configure a API Key

```bash
# Edite o arquivo .env na raiz do projeto
cd e:\Projeto_Idiomas\idiomasbr2026

# Adicione (já configurado):
ELEVENLABS_API_KEY=sk_b02c22ac329da0be5814c207bbe6a1b76d3b0f827da68aad
OPENAI_API_KEY=sk-proj-...  # Já configurado
# OU
DEEPSEEK_API_KEY=sk-...      # Já configurado
```

**Obter API Key ElevenLabs**: https://elevenlabs.io/app/subscription

### 2. Inicie os Servidores

```bash
# Backend
cd backend
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

uvicorn app.main:app --reload

# Frontend (em outro terminal)
cd frontend
npm run dev
```

### 3. Acesse a Interface

Abra: http://localhost:3000/conversation

## 🎯 Primeiros Passos

1. **Clique em "Iniciar Conversação"**
2. **Digite uma mensagem em inglês**
3. **Pressione Enter ou clique em 📤**
4. **Ouça a resposta da IA** (áudio automático)

## ⚙️ Configurações Opcionais

### Escolher Outra Voz

1. Clique em **⚙️ Config**
2. Selecione uma voz da lista (20+ disponíveis)
3. Teste falando algo

### Customizar Comportamento da IA

No campo "System Prompt", experimente:

```
"You are a friendly tutor helping with TOEFL preparation"
"You are a native speaker teaching informal English"
"You are teaching business English vocabulary"
```

## 📊 Testar via API

```bash
# Obter token primeiro
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=seu_email&password=sua_senha"

# Usar o token retornado
export TOKEN="seu_token_jwt"

# Listar vozes disponíveis
curl http://localhost:8000/api/conversation/voices \
  -H "Authorization: Bearer $TOKEN"

# Text-to-Speech
curl -X POST http://localhost:8000/api/conversation/tts \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello, how are you?"}' \
  --output hello.mp3
```

## 🎓 Casos de Uso Sugeridos

### Para Alunos
- ✅ Praticar conversação livre
- ✅ Tirar dúvidas sobre gramática
- ✅ Simular situações do dia-a-dia
- ✅ Treinar pronúncia (ouvindo a IA)

### Para Professores
- ✅ Criar exercícios de conversação
- ✅ Gerar áudios de vocabulário
- ✅ Demonstrar pronúncia correta
- ✅ Preparar material de listening

## ⚠️ Importante

- A API gratuita tem limite de ~10,000 caracteres/mês
- Monitore seu uso em: https://elevenlabs.io/app/subscription
- Cada mensagem consome caracteres baseado no tamanho do texto

## 🐛 Problemas Comuns

### "API key não configurada"
➡️ Verifique se `ELEVENLABS_API_KEY` está no `.env`

### "401 Unauthorized"  
➡️ Verifique se sua chave da ElevenLabs é válida

### Áudio não toca
➡️ Verifique permissões de áudio no navegador

## 📚 Documentação Completa

Para detalhes técnicos, veja: [CONVERSATION_MODULE_GUIDE.md](./CONVERSATION_MODULE_GUIDE.md)

## 💬 Exemplo de Conversa

```
Você: "Hello! Can you help me practice job interview questions?"

IA: "Of course! I'd be happy to help you practice for your job interview. 
     Let's start with a common question: Can you tell me about yourself?"

Você: "I am a software developer with 5 years of experience..."

IA: "That's a great start! Let me give you some feedback..."
```

## 🎉 Pronto!

Agora você está pronto para praticar inglês com conversação full-time! 🚀

---

**Precisa de ajuda?** Consulte [CONVERSATION_MODULE_GUIDE.md](./CONVERSATION_MODULE_GUIDE.md)
