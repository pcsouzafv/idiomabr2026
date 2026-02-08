# Sistema de Estudo de Frases com Professor IA

## Visão Geral

Sistema avançado de aprendizado de inglês com frases completas, integrado com IA (OpenAI + Ollama como fallback) e RAG (Retrieval-Augmented Generation) para ensino personalizado.

## Arquitetura

### Backend

**Modelos (`backend/app/models/sentence.py`):**
- `Sentence` - Frases para estudo com metadados
- `SentenceReview` - Histórico de revisões
- `UserSentenceProgress` - Progresso do usuário (algoritmo SM-2)
- `AIConversation` - Histórico de conversas com IA

**Serviços:**
- `ai_teacher.py` - Professor de IA com OpenAI + fallback Ollama
- `rag_service.py` - Busca contexto inteligente do banco de dados
- `spaced_repetition.py` - Algoritmo SM-2 para repetição espaçada

**Endpoints (`/api/sentences`):**
- `GET /` - Listar frases
- `GET /{id}` - Detalhes da frase
- `GET /study/session` - Criar sessão de estudo
- `POST /study/review` - Registrar revisão
- `POST /ai/ask` - Perguntar ao professor IA
- `POST /ai/analyze/{id}` - Analisar frase específica
- `GET /ai/history` - Histórico de conversas
- `GET /recommendations` - Recomendações personalizadas

### Configuração

**Variáveis de Ambiente (`.env`):**
```bash
# OpenAI (opcional - fallback para Ollama se não disponível)
OPENAI_API_KEY=sk-your-key-here

# Ollama (modelo local)
OLLAMA_URL=http://ollama:11434
USE_OLLAMA_FALLBACK=true
```

**Instalar Dependências:**
```bash
cd backend
pip install -r requirements.txt
```

## Docker com Ollama

### docker-compose.yml

Adicione o serviço Ollama ao seu docker-compose.yml:

```yaml
services:
  ollama:
    image: ollama/ollama:latest
    container_name: idiomasbr-ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    networks:
      - idiomasbr_network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:11434/api/tags"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  ollama_data:
```

### Baixar Modelo Ollama

Após iniciar o Docker:

```bash
# Entrar no container
docker exec -it idiomasbr-ollama bash

# Baixar modelo (recomendado: llama3.2 ou mistral)
ollama pull llama3.2

# Ou modelo menor para testes
ollama pull llama3.2:1b
```

## MCP Server (Model Context Protocol)

### Estrutura

Crie um MCP Server para acesso ao banco de dados:

```
backend/
├── mcp_server/
│   ├── __init__.py
│   ├── server.py          # MCP Server principal
│   ├── tools.py           # Ferramentas disponíveis
│   └── config.json        # Configuração do servidor
```

### Ferramentas MCP

O MCP Server fornece:
- Busca de frases no banco
- Busca de vocabulário relacionado
- Estatísticas do usuário
- Histórico de progresso

## Uso

### 1. Iniciar Sistema

```bash
# Com Docker
docker-compose up -d

# Ou localmente
cd backend
uvicorn app.main:app --reload
```

### 2. Popular Banco com Frases

Crie um script `backend/import_sentences.py`:

```python
from app.core.database import SessionLocal
from app.models.sentence import Sentence

db = SessionLocal()

sentences = [
    {
        "english": "I love learning new languages every day.",
        "portuguese": "Eu amo aprender novos idiomas todos os dias.",
        "level": "A2",
        "category": "daily_life"
    },
    # ... mais frases
]

for s in sentences:
    sentence = Sentence(**s)
    db.add(sentence)

db.commit()
```

### 3. Acessar Interface

Frontend em desenvolvimento. Endpoints disponíveis via:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 4. Testar Professor IA

```bash
curl -X POST "http://localhost:8000/api/sentences/ai/ask" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_message": "Explique a diferença entre present simple e present continuous",
    "include_context": true
  }'
```

## Recursos

### Professor IA

O professor de IA:
- Explica gramática em português
- Fornece exemplos práticos
- Identifica erros comuns de brasileiros
- Dá dicas de uso contextual
- Gera exercícios personalizados

### RAG (Retrieval-Augmented Generation)

O sistema RAG:
- Busca vocabulário relacionado no banco
- Analisa progresso do usuário
- Recomenda próximos estudos
- Personaliza explicações baseado no nível

### Algoritmo SM-2

Repetição espaçada inteligente:
- **Hard**: Revisar em 4 horas
- **Medium**: Revisar em 1 dia
- **Easy**: Revisar em 3+ dias

## Próximos Passos

1. Concluir interface frontend
2. Implementar MCP Server completo
3. Adicionar embeddings para busca semântica
4. Criar exercícios interativos com IA
5. Implementar reconhecimento de voz

## Troubleshooting

### OpenAI API Error
Se a API OpenAI falhar, o sistema automaticamente usa Ollama local.

### Ollama Não Responde
```bash
# Verificar se está rodando
docker logs idiomasbr-ollama

# Reiniciar serviço
docker restart idiomasbr-ollama
```

### Banco de Dados
```bash
# Recriar tabelas
docker-compose down -v
docker-compose up -d
```
