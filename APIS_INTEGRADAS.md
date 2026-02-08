# APIs e Integrações Externas do Sistema IdiomasBR

## Resumo Executivo

O sistema IdiomasBR integra **3 APIs externas principais** para funcionalidades de IA e conteúdo:

1. **OpenAI API** (Principal - Paga)
2. **DeepSeek API** (Fallback - Paga)
3. **YouTube Data API** (Conteúdo de vídeos - Gratuita com limites)
4. **Ollama** (Opcional - Gratuita/Local)

---

## 1. OpenAI API (Prioridade 1)

### Funcionalidade
Fornece o "Professor de IA" (Sarah) que interage com os alunos através de chat.

### Endpoints Utilizados
- **Chat Completions** (`/v1/chat/completions`)
  - Modelo: `gpt-4o-mini`
  - Uso: Conversas com o professor de IA
  - Temperatura: 0.7
  - Max tokens: 800

- **Text-to-Speech** (`/v1/audio/speech`)
  - Modelo: `tts-1`
  - Voz: `nova` (feminina, calorosa)
  - Uso: Geração de áudio para pronúncia
  - Velocidade: 0.95 (mais devagar para aprendizes)
  - Limite: 4096 caracteres por request

### Configuração
```env
OPENAI_API_KEY=sk-...
```

### Custo Estimado
- **Chat**: ~$0.001 por interação (gpt-4o-mini)
  - Input: $0.150 / 1M tokens
  - Output: $0.600 / 1M tokens
- **TTS**: ~$0.015 por 1000 caracteres
  - $15.00 / 1M caracteres

### Uso no Sistema
- `backend/app/services/ai_teacher.py:220-231` - Chat responses
- `backend/app/services/ai_teacher.py:194-218` - Text-to-Speech
- `backend/app/routes/sentences.py:340-557` - Endpoints de IA

### Documentação Oficial
https://platform.openai.com/docs/api-reference

---

## 2. DeepSeek API (Fallback)

### Funcionalidade
Sistema de fallback quando OpenAI falha ou não está disponível.

### Endpoints Utilizados
- **Chat Completions** (`/chat/completions`)
  - Modelo: `deepseek-chat`
  - Temperatura: 0.7
  - Max tokens: 1200

### Configuração
```env
DEEPSEEK_API_KEY=sk-...
```

### Base URL
```
https://api.deepseek.com
```

### Custo Estimado
- **Chat**: ~$0.0002 por interação
  - Input: $0.14 / 1M tokens (Cache hits: $0.014 / 1M)
  - Output: $0.28 / 1M tokens
- **5-10x mais barato** que OpenAI

### Uso no Sistema
- `backend/app/services/ai_teacher.py:181-192` - DeepSeek responses
- Ativado automaticamente se OpenAI falhar

### Documentação Oficial
https://api-docs.deepseek.com/

---

## 3. YouTube Data API v3

### Funcionalidade
Extração de metadados e thumbnails de vídeos educacionais.

### Recursos Utilizados
- **Thumbnails**: URLs públicas (`https://img.youtube.com/vi/{VIDEO_ID}/maxresdefault.jpg`)
- **Embed Player**: Player iframe do YouTube
- **Metadados**: Extraídos manualmente via URL parsing

### Padrões de URL Suportados
1. `youtube.com/watch?v={ID}`
2. `youtu.be/{ID}`
3. `youtube.com/embed/{ID}`

### Configuração
Não requer API key - usa URLs públicas do YouTube.

### Custo
Gratuito (não usa quota da API oficial)

### Uso no Sistema
- `backend/app/routes/videos.py:26-43` - Extração de YouTube ID
- `backend/app/routes/videos.py:41-43` - Geração de thumbnail URL
- Armazenamento de vídeos educacionais no banco

### Limitações
- Sem acesso a estatísticas oficiais (views, likes)
- Sem validação automática se vídeo existe
- Dependente de thumbnails públicas do YouTube

---

## 4. Ollama (Opcional - Local)

### Funcionalidade
Sistema de IA local/self-hosted como fallback final (desabilitado por padrão).

### Endpoints Utilizados
- **Generate** (`/api/generate`)
  - Modelo: `llama3.2`
  - Temperatura: 0.7
  - Max tokens: 800

### Configuração
```env
OLLAMA_URL=http://localhost:11434
USE_OLLAMA_FALLBACK=false  # Desabilitado por padrão
```

### Custo
Gratuito - roda localmente

### Uso no Sistema
- `backend/app/services/ai_teacher.py:233-283` - Ollama integration
- Apenas ativo se `USE_OLLAMA_FALLBACK=true`

### Requisitos
- Ollama instalado localmente
- Modelo `llama3.2` baixado
- Hardware com GPU/CPU adequado

### Documentação Oficial
https://ollama.ai/

---

## Fluxo de Fallback da IA

O sistema implementa um fallback em cascata:

```
1. OpenAI (gpt-4o-mini)
   ↓ [falha]
2. DeepSeek (deepseek-chat)
   ↓ [falha]
3. Ollama (llama3.2) - se habilitado
   ↓ [falha]
4. Erro: "Nenhum modelo de IA disponível"
```

**Código**: `backend/app/services/ai_teacher.py:107-179`

---

## APIs do Google Cloud Platform (Infraestrutura)

Além das APIs externas, o sistema usa serviços GCP:

### Cloud SQL
- **Banco PostgreSQL** gerenciado
- Instância: `idiomasbr-db`
- Região: `us-central1`

### Cloud Run
- **Backend**: `idiomasbr-backend`
- **Frontend**: `idiomasbr-frontend`
- Auto-scaling baseado em requisições

### Secret Manager
- Armazena credenciais sensíveis:
  - `idiomasbr-openai-api-key`
  - `idiomasbr-deepseek-api-key`
  - `idiomasbr-database-url`

### Cloud Storage
- Bucket: `idiomasbr_cloudbuild`
- Uso: Build artifacts, dumps de banco

### Artifact Registry
- Registry: `idiomasbr-docker`
- Armazena imagens Docker do backend e frontend

---

## Monitoramento de Custos

### Estimativa Mensal (100 usuários ativos)

**OpenAI**:
- Chat (10 interações/usuário/dia): ~$30/mês
- TTS (5 áudios/usuário/dia): ~$22.50/mês
- **Total OpenAI**: ~$52.50/mês

**DeepSeek** (apenas fallback):
- ~$2-5/mês (uso esporádico)

**YouTube**:
- $0/mês (sem API key)

**Ollama**:
- $0/mês (se self-hosted)

**GCP Infraestrutura**:
- Cloud Run: ~$20/mês
- Cloud SQL: ~$25/mês
- Storage/Registry: ~$2/mês
- **Total GCP**: ~$47/mês

**CUSTO TOTAL ESTIMADO**: ~$100-105/mês (100 usuários)

---

## Variáveis de Ambiente Necessárias

### Obrigatórias
```env
DATABASE_URL=postgresql://user:pass@host:5432/db
SECRET_KEY=your-jwt-secret-key
```

### APIs de IA (pelo menos uma)
```env
OPENAI_API_KEY=sk-...        # Recomendado
DEEPSEEK_API_KEY=sk-...      # Fallback
```

### Opcionais
```env
OLLAMA_URL=http://localhost:11434
USE_OLLAMA_FALLBACK=false
DEBUG=false
```

---

## Segurança

### API Keys
- Armazenadas em **Secret Manager** (GCP)
- Nunca commitadas no código
- Acessadas via variáveis de ambiente

### Rate Limiting
- Implementado no nível do FastAPI
- Proteção contra abuso de APIs pagas

### CORS
- Configurado para aceitar apenas domínios autorizados
- Frontend e Backend em domínios separados

---

## Como Adicionar Nova API

1. **Adicionar dependência** em `requirements.txt`
2. **Criar service** em `backend/app/services/`
3. **Adicionar configuração** em `backend/app/core/config.py`
4. **Criar secret** no GCP Secret Manager
5. **Atualizar cloudbuild.yaml** para injetar secrets
6. **Documentar** neste arquivo

---

## Troubleshooting

### OpenAI retorna erro 429 (Rate Limit)
- Aguardar alguns segundos
- Sistema automaticamente faz fallback para DeepSeek

### DeepSeek não responde
- Verificar se API key está configurada
- Checar se base_url está correta: `https://api.deepseek.com`

### TTS não funciona
- TTS requer OpenAI API Key
- Verificar se key tem permissões para TTS
- Limite de 4096 caracteres por request

### YouTube vídeo não carrega
- Verificar se URL é válida
- Checar se vídeo não foi removido/privatizado
- Validar formato da URL

---

## Documentação das APIs

- **OpenAI**: https://platform.openai.com/docs
- **DeepSeek**: https://api-docs.deepseek.com/
- **YouTube**: https://developers.google.com/youtube/v3
- **Ollama**: https://ollama.ai/
- **GCP**: https://cloud.google.com/docs

---

**Última Atualização**: 2025-12-17
**Versão do Sistema**: 1.0
