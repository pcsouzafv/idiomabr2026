# 🚀 Quick Start - Sistema de Estudo de Frases com IA

## ✅ O que foi criado

Criei um **sistema completo de estudo de frases com Professor de IA** integrado ao seu projeto IdiomasBR:

### Backend Completo
- ✅ **Modelos de dados** (Sentence, SentenceReview, UserSentenceProgress, AIConversation)
- ✅ **API REST** com 8 endpoints para frases e IA
- ✅ **Integração OpenAI** + fallback Ollama local
- ✅ **Sistema RAG** para contexto inteligente
- ✅ **Algoritmo SM-2** para repetição espaçada
- ✅ **Docker configurado** com Ollama

### Arquivos Criados
```
backend/
├── app/
│   ├── models/sentence.py           # Modelos do banco
│   ├── schemas/sentence.py          # Validação Pydantic
│   ├── routes/sentences.py          # Endpoints API
│   ├── services/
│   │   ├── ai_teacher.py           # Professor IA
│   │   └── rag_service.py          # Contexto inteligente
│   └── core/config.py              # Configurações atualizadas
├── import_sentences.py              # Popular banco com exemplos
└── requirements.txt                 # Dependências atualizadas

docker-compose.yml                   # Com Ollama configurado
.env                                 # Variáveis de ambiente
SENTENCE_STUDY_GUIDE.md             # Documentação completa
QUICK_START_SENTENCES.md            # Este arquivo
```

## 🎯 Como Usar

### Passo 1: Configurar API OpenAI (Opcional)

Edite o arquivo `.env`:

```bash
OPENAI_API_KEY=sk-sua-chave-aqui
```

**Nota**: Se não configurar, o sistema usa automaticamente Ollama (modelo local).

### Passo 2: Iniciar com Docker

```bash
# Limpar ambiente anterior (se necessário)
docker-compose down -v

# Iniciar todos os serviços (PostgreSQL + Ollama + Backend + Frontend)
docker-compose up -d

# Acompanhar logs
docker-compose logs -f
```

### Passo 3: Configurar Ollama (Primeira vez)

Baixe um modelo de IA local:

```bash
# Entrar no container Ollama
docker exec -it idiomasbr-ollama bash

# Baixar modelo (escolha um):
ollama pull llama3.2          # Recomendado (4.7GB)
ollama pull llama3.2:1b       # Modelo menor (1.3GB)
ollama pull mistral           # Alternativa (4.1GB)

# Sair do container
exit
```

### Passo 4: Popular Banco com Frases

```bash
# Entrar no container do backend
docker exec -it idiomasbr-backend bash

# Executar script de importação
python import_sentences.py

# Sair
exit
```

Isso adiciona 12 frases de exemplo (A1 a C2).

### Passo 5: Testar API

Acesse a documentação interativa:
- Swagger UI: **http://localhost:8000/docs**
- ReDoc: **http://localhost:8000/redoc**

## 📡 Endpoints Disponíveis

### Frases
```bash
GET  /api/sentences/                    # Listar frases
GET  /api/sentences/{id}                # Detalhes de uma frase
GET  /api/sentences/study/session       # Criar sessão de estudo
POST /api/sentences/study/review        # Registrar revisão
GET  /api/sentences/recommendations     # Recomendações personalizadas
```

### Professor IA
```bash
POST /api/sentences/ai/ask              # Perguntar ao professor
POST /api/sentences/ai/analyze/{id}     # Analisar frase específica
GET  /api/sentences/ai/history          # Histórico de conversas
```

## 🧪 Testando o Professor IA

### Exemplo 1: Pergunta Geral

```bash
curl -X POST "http://localhost:8000/api/sentences/ai/ask" \
  -H "Authorization: Bearer SEU_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_message": "Como usar o Present Perfect?",
    "include_context": false
  }'
```

### Exemplo 2: Analisar Frase Específica

```bash
curl -X POST "http://localhost:8000/api/sentences/ai/analyze/1" \
  -H "Authorization: Bearer SEU_TOKEN"
```

### Exemplo 3: Perguntar com Contexto

```bash
curl -X POST "http://localhost:8000/api/sentences/ai/ask" \
  -H "Authorization: Bearer SEU_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "sentence_id": 1,
    "user_message": "Explique a gramática desta frase",
    "include_context": true
  }'
```

## 🎓 Funcionalidades do Professor IA

O professor IA automaticamente:

1. **Explica em Português** - Todas as explicações são em português brasileiro
2. **Personaliza por Nível** - Adapta explicações ao nível do aluno (A1-C2)
3. **Usa RAG** - Busca contexto relevante no banco de dados
4. **Identifica Erros Comuns** - Alerta sobre erros típicos de brasileiros
5. **Fornece Exemplos** - Dá exemplos práticos de uso
6. **Sugere Exercícios** - Pode gerar exercícios personalizados

## 🔧 Variáveis de Ambiente

```bash
# OpenAI (opcional)
OPENAI_API_KEY=sk-your-key           # Deixe vazio para usar apenas Ollama

# Ollama (modelo local)
OLLAMA_URL=http://ollama:11434       # URL do Ollama no Docker
USE_OLLAMA_FALLBACK=true             # Usar Ollama se OpenAI falhar
```

## 📊 Como Funciona o RAG

O sistema RAG (Retrieval-Augmented Generation) enriquece as respostas da IA com:

1. **Vocabulário Relacionado** - Palavras do banco que aparecem na frase
2. **Progresso do Usuário** - Quantas palavras/frases já estudou
3. **Nível Estimado** - Baseado no progresso (A1-C2)
4. **Histórico de Revisões** - Como o usuário performou antes

Isso torna o ensino **personalizado e contextualizado**.

## 🎮 Repetição Espaçada (SM-2)

Sistema inteligente que agenda revisões:

| Dificuldade | Próxima Revisão | Quando usar |
|-------------|-----------------|-------------|
| **Hard** | 4 horas | Não lembrei |
| **Medium** | 1 dia | Lembrei com dificuldade |
| **Easy** | 3+ dias | Lembrei facilmente |

## 🐛 Troubleshooting

### Ollama não responde
```bash
# Verificar status
docker ps | grep ollama

# Ver logs
docker logs idiomasbr-ollama

# Reiniciar
docker restart idiomasbr-ollama
```

### OpenAI API Error
- Verifique se `OPENAI_API_KEY` está correto
- Sistema usa Ollama automaticamente como backup

### Banco de dados vazio
```bash
# Popular com frases de exemplo
docker exec -it idiomasbr-backend python import_sentences.py
```

### Erro nas migrations
```bash
# Recriar banco do zero
docker-compose down -v
docker-compose up -d
```

## 📝 Próximos Passos

### Frontend (Você pode implementar)
Crie em `frontend/src/app/sentences/page.tsx`:
- Interface de estudo de frases
- Chat com professor IA
- Visualização de progresso

### Adicionar Mais Frases
Edite `backend/import_sentences.py` e adicione mais exemplos.

### MCP Server (Opcional)
Para integração avançada com ferramentas externas.

## 📚 Documentação Completa

Consulte `SENTENCE_STUDY_GUIDE.md` para documentação detalhada.

## 🎉 Pronto!

Seu sistema de estudo de frases com IA está funcionando!

Endpoints disponíveis em: **http://localhost:8000/docs**
