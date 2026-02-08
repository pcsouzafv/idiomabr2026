# Integração com IAs - IdiomasBR

## Visão Geral

Seu sistema usa **múltiplas IAs** com sistema de **fallback automático** para garantir disponibilidade. A arquitetura é inteligente e prioriza custo vs. qualidade.

## Arquitetura de Fallback

```
┌─────────────────────────────────────────────────────────────┐
│                    Usuario faz pergunta                      │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────┐
│              AITeacherService (ai_teacher.py)                 │
│  Ordem de tentativa:                                          │
│  1️⃣ OpenAI (gpt-4o-mini) - Principal                          │
│  2️⃣ DeepSeek (deepseek-chat) - Fallback                       │
│  3️⃣ Ollama (llama3.2) - Fallback local (se habilitado)        │
└──────────────────────────────────────────────────────────────┘
```

## Detalhes de Cada IA

### 1️⃣ OpenAI (Principal)
**Modelo**: `gpt-4o-mini`
**Quando usa**: Sempre que disponível (primeira tentativa)
**Vantagens**:
- Melhor qualidade de resposta
- Suporte a Text-to-Speech (voz da professora Sarah)
- Respostas mais naturais e didáticas

**Configuração**:
```python
# backend/app/core/config.py
openai_api_key: str = ""  # Vem do Secret Manager no GCP

# backend/app/services/ai_teacher.py (linha 220-231)
model="gpt-4o-mini"       # Modelo econômico
temperature=0.7           # Criatividade moderada
max_tokens=800           # ~600 palavras por resposta
```

**Funcionalidades exclusivas**:
- **Chat**: Conversa com a professora Sarah
- **TTS (Text-to-Speech)**: Gera áudio das frases (voz "nova" - feminina calorosa)

### 2️⃣ DeepSeek (Fallback)
**Modelo**: `deepseek-chat`
**Quando usa**: Se OpenAI falhar ou não estiver configurada
**Vantagens**:
- Muito mais barato que OpenAI
- Boa qualidade (especialmente em português)
- Responde rápido

**Configuração**:
```python
# backend/app/services/ai_teacher.py (linha 181-192)
model="deepseek-chat"
temperature=0.7
max_tokens=1200  # Mais tokens que OpenAI (conversas longas)
```

**Base URL**: `https://api.deepseek.com`

### 3️⃣ Ollama (Fallback Local - Opcional)
**Modelo**: `llama3.2` (roda localmente)
**Quando usa**: Se OpenAI e DeepSeek falharem E `USE_OLLAMA_FALLBACK=true`
**Vantagens**:
- 100% gratuito (roda na sua máquina)
- Privacidade total (dados não saem do servidor)
- Sem limite de requisições

**Desvantagens**:
- Precisa de GPU/CPU potente
- Mais lento que as APIs
- Qualidade inferior

**Configuração**:
```python
ollama_url: str = "http://localhost:11434"  # Docker local
use_ollama_fallback: bool = False           # Desabilitado por padrão
```

## Fluxo de Decisão (Código)

```python
# backend/app/services/ai_teacher.py:107-179
async def get_ai_response(...):
    # 1️⃣ Tenta OpenAI
    if self.openai_client:
        try:
            return openai_response()
        except:
            pass  # Continua para próxima opção

    # 2️⃣ Tenta DeepSeek
    if self.deepseek_client:
        try:
            return deepseek_response()
        except:
            pass

    # 3️⃣ Tenta Ollama (se habilitado)
    if self.use_ollama_fallback:
        try:
            return ollama_response()
        except:
            raise Exception("Nenhum modelo disponível")

    raise Exception("Nenhum modelo configurado")
```

## Configuração no GCP (Atual)

### Secrets Criados ✅
```bash
# Criados durante o deploy
idiomasbr-openai-api-key     # OpenAI API Key
idiomasbr-deepseek-api-key   # DeepSeek API Key
```

### Injetados no Cloud Run
```bash
# deploy_gcp.sh:244
--set-secrets "
  DATABASE_URL=idiomasbr-database-url:latest,
  SECRET_KEY=idiomasbr-secret-key:latest,
  OPENAI_API_KEY=idiomasbr-openai-api-key:latest,
  DEEPSEEK_API_KEY=idiomasbr-deepseek-api-key:latest
"
```

### Configuração Atual
```bash
# Variáveis de ambiente no Cloud Run
OPENAI_API_KEY=sk-sua-chave-aqui          # ✅ Configurado
DEEPSEEK_API_KEY=sk-sua-chave-aqui        # ✅ Configurado
USE_OLLAMA_FALLBACK=false                  # ❌ Desabilitado (não há Ollama no Cloud Run)
OLLAMA_URL=http://ollama:11434            # ⚠️ Não usado (Ollama não disponível)
```

## Funcionalidades da IA

### 1. Chat com Professora Sarah
```python
# Endpoint: POST /api/sentences/{sentence_id}/chat
# Arquivo: backend/app/routes/sentences.py

# Exemplo de uso:
{
  "message": "Como uso 'have to' vs 'must'?",
  "conversation_history": [...]
}
```

**Resposta incluirá**:
- Explicação didática em português
- Exemplos práticos
- Encorajamento e dicas
- Modelo usado (openai/deepseek/ollama)

### 2. Text-to-Speech (TTS)
```python
# Endpoint: POST /api/sentences/{sentence_id}/speech
# Funcionalidade: Gera áudio da frase

# IMPORTANTE: Requer OpenAI (DeepSeek não tem TTS)
```

**Configuração de voz**:
```python
# backend/app/services/ai_teacher.py:194-218
voice="nova"      # Voz feminina calorosa (Professora Sarah)
model="tts-1"     # Modelo mais rápido e barato
speed=0.95        # Um pouco mais devagar (para aprendizes)
```

### 3. Análise de Frases
```python
async def analyze_sentence(
    sentence_en: str,
    sentence_pt: str,
    user_level: str = "A1"
) -> Dict[str, Any]:
    """
    Retorna:
    - Estrutura gramatical
    - Vocabulário-chave
    - Pontos de atenção
    - Exemplos similares
    - Dica de uso prático
    """
```

### 4. Correção de Frases
```python
async def correct_user_sentence(
    user_sentence: str,
    target_sentence: Optional[str] = None
) -> Dict[str, Any]:
    """
    Identifica erros e explica correções
    """
```

### 5. Geração de Exercícios
```python
async def generate_practice_exercises(
    sentence_en: str,
    user_level: str = "A1"
) -> Dict[str, Any]:
    """
    Cria 3 tipos de exercícios:
    - Completar lacunas
    - Tradução
    - Compreensão
    """
```

## Personalidade da IA (Prompt do Sistema)

A IA foi configurada como **Sarah**, uma professora entusiasta que:

```python
# backend/app/services/ai_teacher.py:39-75

Personalidade:
✅ Calorosa, paciente e genuinamente empolgada
✅ Celebra cada pequena vitória
✅ Cria ambiente seguro e sem julgamentos
✅ Usa exemplos do mundo real

Metodologia (Método Socrático):
1. Começa com encorajamento e contexto
2. FAZ perguntas ao invés de apenas explicar
3. Aguarda respostas do aluno e constrói em cima
4. Guia o aluno a descobrir as respostas
5. Sempre termina com motivação e próximos passos

Estrutura de Conversa:
- Início: "Ótima escolha! Essa frase é muito útil. Vamos explorar juntos?"
- Pergunta 1: Vocabulário ou contexto
- Pergunta 2: Gramática ou uso
- Pergunta 3: Uso em situação real
- Elogios: "Muito bem!", "Excelente!", "Você está progredindo!"
- Fim: Dica prática + Encorajamento + Sugestão de próximo passo
```

## Contexto RAG (Retrieval-Augmented Generation)

A IA não responde sozinha - ela recebe contexto do banco de dados:

```python
# backend/app/services/ai_teacher.py:77-105

Contexto enviado para a IA:
1. Frase em estudo:
   - Inglês + Português
   - Nível (A1/A2/B1/B2/C1/C2)
   - Pontos gramaticais

2. Vocabulário relacionado:
   - 5 palavras relacionadas à frase
   - Com tradução

3. Progresso do aluno:
   - Total de palavras aprendidas
   - Nível estimado
```

## Custos Estimados (APIs)

### OpenAI (gpt-4o-mini)
- **Input**: $0.150 / 1M tokens (~$0.00015 por conversa)
- **Output**: $0.600 / 1M tokens (~$0.0006 por conversa)
- **TTS**: $15.00 / 1M caracteres (~$0.015 por frase)

**Estimativa**: ~$0.001 por interação (muito barato!)

### DeepSeek
- **Input+Output**: ~$0.14 / 1M tokens
- **Estimativa**: ~$0.0002 por interação (70% mais barato que OpenAI)

### Ollama
- **Custo**: $0 (100% gratuito, roda localmente)
- **Infraestrutura**: Requer VM com GPU no GCP (~$200-500/mês)

## Monitoramento e Logs

O sistema faz logging detalhado:

```python
# Logs de inicialização
[INIT] DeepSeek API Key: SET/NOT SET
[INIT] OpenAI API Key: SET/NOT SET
[INIT] Ollama fallback: true/false

# Logs de requisição
[REQUEST] Sending request to DeepSeek...
[SUCCESS] DeepSeek responded: 1234 characters
[ERROR] DeepSeek error: Rate limit exceeded

# Logs de TTS
[TTS] Gerando áudio para 150 caracteres...
[TTS] Áudio gerado com sucesso!
[TTS ERROR] Quota exceeded
```

## Como Testar Localmente

### 1. Com Docker Compose (Todas as IAs)
```bash
# Configurar .env
OPENAI_API_KEY=sk-proj-...
DEEPSEEK_API_KEY=sk-...
USE_OLLAMA_FALLBACK=true

# Subir serviços
docker-compose up -d

# Testar endpoint
curl -X POST http://localhost:8000/api/sentences/1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Como usar esta frase?"}'
```

### 2. Apenas OpenAI/DeepSeek
```bash
# .env
USE_OLLAMA_FALLBACK=false

# Não precisa do serviço ollama no docker-compose
```

## Troubleshooting

### Erro: "Nenhum modelo de IA configurado"
**Causa**: Nenhuma API key configurada
**Solução**: Configure pelo menos OPENAI_API_KEY ou DEEPSEEK_API_KEY

### Erro: "TTS requer OpenAI API Key"
**Causa**: Tentou usar TTS sem OpenAI configurado
**Solução**: Configure OPENAI_API_KEY (DeepSeek não tem TTS)

### Erro: "Rate limit exceeded"
**Causa**: Muitas requisições (limite da API)
**Solução**: Aguarde ou upgrade do plano da API

### Ollama não responde
**Causa**: Serviço Ollama não está rodando
**Solução**:
```bash
# Docker
docker-compose up ollama

# Verificar
curl http://localhost:11434/api/tags
```

## Próximos Passos (Sugestões)

### 1. Adicionar Mais Modelos
```python
# Claude (Anthropic)
# Gemini (Google)
# Llama via Groq (mais rápido que Ollama)
```

### 2. Cache de Respostas
```python
# Redis para cachear perguntas frequentes
# Reduzir custos em ~70%
```

### 3. Monitoramento de Custos
```python
# Dashboard com gastos por modelo
# Alertas de budget
```

### 4. A/B Testing
```python
# Testar qual modelo os usuários preferem
# Otimizar custo vs. qualidade
```

## Referências

- **OpenAI Docs**: https://platform.openai.com/docs
- **DeepSeek Docs**: https://platform.deepseek.com/docs
- **Ollama Docs**: https://ollama.ai/docs
- **Código Principal**: `backend/app/services/ai_teacher.py`
- **Rotas**: `backend/app/routes/sentences.py`
