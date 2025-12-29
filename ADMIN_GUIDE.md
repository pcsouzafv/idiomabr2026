# Guia do Sistema de Administração - IdiomasBR

## Visão Geral

O sistema de administração permite gerenciar completamente o banco de dados através de uma interface web intuitiva, incluindo:

- ✅ **Dashboard com estatísticas** em tempo real
- ✅ **CRUD completo** de palavras, sentenças, vídeos e usuários
- ✅ **Importação em massa** via CSV
- ✅ **Exportação de templates** para facilitar importação
- ✅ **Filtros e busca** avançada
- ✅ **Controle de permissões** (admin vs usuário comum)

---

## Configuração Inicial

### 1. Promover um Usuário a Admin

Primeiro, você precisa criar um usuário administrador:

```bash
# No diretório backend/
cd backend

# Ativar ambiente virtual (se necessário)
source venv/bin/activate  # Linux/Mac
.\venv\Scripts\activate   # Windows

# Promover usuário existente a admin
python make_admin.py usuario@email.com

# Listar todos os admins
python make_admin.py --list

# Revogar privilégios de admin
python make_admin.py --revoke usuario@email.com
```

**Importante**: O usuário precisa estar cadastrado primeiro no sistema antes de ser promovido a admin.

### 2. Criar Primeiro Usuário Admin

Se ainda não tem nenhum usuário, crie um pela interface web:

1. Acesse http://localhost:3000/register
2. Crie uma conta com seu email
3. Use o script `make_admin.py` para promover essa conta
4. Faça login novamente para atualizar as permissões

---

## Acessando o Painel Admin

### URL
```
http://localhost:3000/admin
```

### Requisitos
- Usuário deve estar logado
- Usuário deve ter `is_admin = true` no banco de dados

### Proteções
- Usuários não-admin são automaticamente redirecionados ao dashboard
- Todas as rotas da API verificam permissões de admin
- Tokens JWT são validados em cada requisição

---

## Funcionalidades

### 📊 Dashboard (Visão Geral)

**Estatísticas exibidas:**
- Total de usuários (ativos nos últimos 7 dias)
- Total de palavras, sentenças e vídeos
- Total de reviews (interações de estudo)
- Taxa de engajamento
- Distribuição de palavras por nível (A1-C2)

**Acesso:**
- URL: `/admin`
- Atualização em tempo real

---

### 📖 Gerenciamento de Palavras

#### Funcionalidades:
- ✅ Listar todas as palavras (paginado - 50 por página)
- ✅ Buscar por palavra (inglês ou português)
- ✅ Filtrar por nível (A1, A2, B1, B2, C1, C2)
- ✅ Criar nova palavra manualmente
- ✅ Editar palavra existente
- ✅ Deletar palavra (com confirmação)
- ✅ Importar em massa via CSV
- ✅ Baixar template CSV

#### Importação de Palavras (CSV)

**Formato do CSV:**
```csv
english,ipa,portuguese,level,word_type,definition_en,definition_pt,example_en,example_pt,tags
hello,həˈloʊ,olá,A1,interjection,A greeting,Uma saudação,Hello! How are you?,Olá! Como você está?,greetings;basic
house,haʊs,casa,A1,noun,A building for living,Um edifício para morar,This is my house,Esta é minha casa,places;home
beautiful,ˈbjuːtɪfəl,bonito,A2,adjective,Pleasing to the senses,Agradável aos sentidos,She is beautiful,Ela é bonita,appearance;descriptive
```

**Campos:**
- `english` **(obrigatório)** - Palavra em inglês
- `ipa` - Transcrição fonética IPA
- `portuguese` **(obrigatório)** - Tradução em português
- `level` - Nível CEFR (A1, A2, B1, B2, C1, C2)
- `word_type` - Tipo (noun, verb, adjective, adverb, etc.)
- `definition_en` - Definição em inglês
- `definition_pt` - Definição em português
- `example_en` - Frase de exemplo em inglês
- `example_pt` - Frase de exemplo em português
- `tags` - Tags separadas por ponto-e-vírgula

**Processo de Importação:**
1. Clique em "📤 Importar CSV"
2. Selecione o arquivo CSV
3. O sistema irá:
   - Criar palavras novas
   - Atualizar palavras existentes (baseado no campo `english`)
   - Reportar erros de validação

**Resultado:**
```json
{
  "created": 150,
  "updated": 25,
  "errors": ["Linha 42: campo 'english' vazio"],
  "total_processed": 175
}
```

#### Endpoints da API

```http
GET    /api/admin/words?page=1&per_page=50&search=hello&level=A1
POST   /api/admin/words
PATCH  /api/admin/words/{id}
DELETE /api/admin/words/{id}
POST   /api/admin/words/bulk (upload CSV)
```

---

### 💬 Gerenciamento de Sentenças

Similar ao gerenciamento de palavras, mas para frases completas.

#### Funcionalidades:
- ✅ Listar, criar, editar e deletar sentenças
- ✅ Importação em massa via CSV
- ✅ Filtros por nível e categoria

#### Formato CSV:
```csv
english,portuguese,level,category,grammar_points
I love learning English,Eu amo aprender inglês,A1,General,present simple
She has been studying for hours,Ela tem estudado por horas,B1,Time,present perfect continuous
```

#### Endpoints da API

```http
GET    /api/admin/sentences?page=1&per_page=50
POST   /api/admin/sentences
PATCH  /api/admin/sentences/{id}
DELETE /api/admin/sentences/{id}
POST   /api/admin/sentences/bulk
```

---

### 🎥 Gerenciamento de Vídeos

#### Funcionalidades:
- ✅ Adicionar vídeos do YouTube
- ✅ Editar metadados (título, nível, categoria)
- ✅ Deletar vídeos
- ✅ Thumbnail automática do YouTube

#### Campos:
- `title` - Título do vídeo
- `url` - URL do YouTube
- `thumbnail_url` - URL da thumbnail (preenchida automaticamente)
- `level` - Nível do conteúdo
- `category` - Categoria (Grammar, Vocabulary, Listening, etc.)
- `duration_seconds` - Duração em segundos

#### Endpoints da API

```http
GET    /api/admin/videos?page=1&per_page=50
POST   /api/admin/videos
PATCH  /api/admin/videos/{id}
DELETE /api/admin/videos/{id}
```

---

### 👥 Gerenciamento de Usuários

#### Funcionalidades:
- ✅ Listar todos os usuários
- ✅ Buscar por nome ou email
- ✅ Ver detalhes do usuário (streak, progresso, etc.)
- ✅ Editar dados do usuário
- ✅ Promover/despromover admin
- ✅ Ativar/desativar conta
- ✅ Deletar usuário (exceto você mesmo)

#### Campos Editáveis:
- `name` - Nome do usuário
- `email` - Email
- `is_active` - Conta ativa/inativa
- `is_admin` - Permissões de administrador
- `daily_goal` - Meta diária de palavras

#### Endpoints da API

```http
GET    /api/admin/users?page=1&per_page=50&search=john
GET    /api/admin/users/{id}
PATCH  /api/admin/users/{id}
DELETE /api/admin/users/{id}
```

---

## 🛠️ Ferramentas de Manutenção

### Limpeza de Dados Órfãos

Remove registros de progresso de palavras que não existem mais:

```http
DELETE /api/admin/cleanup/orphaned-progress
```

### Limpeza de Reviews Antigas

Remove reviews com mais de X dias (padrão: 365):

```http
DELETE /api/admin/cleanup/old-reviews?days=365
```

---

## 🔒 Segurança

### Autenticação
- Todas as rotas requerem token JWT válido
- Token deve pertencer a um usuário com `is_admin = true`

### Autorização
O middleware `require_admin` verifica:
```python
def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if not getattr(current_user, "is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito a administradores"
        )
    return current_user
```

### Validações
- Email único por usuário
- Palavras únicas (campo `english`)
- Validação de campos obrigatórios
- Proteção contra SQL injection (SQLAlchemy ORM)

---

## 📝 Exemplos de Uso

### Criar Palavra via API

```bash
curl -X POST http://localhost:8000/api/admin/words \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "english": "amazing",
    "ipa": "əˈmeɪzɪŋ",
    "portuguese": "incrível",
    "level": "A2",
    "word_type": "adjective",
    "example_en": "This is amazing!",
    "example_pt": "Isso é incrível!"
  }'
```

### Importar Palavras em Massa

```bash
curl -X POST http://localhost:8000/api/admin/words/bulk \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@palavras.csv"
```

### Obter Estatísticas

```bash
curl http://localhost:8000/api/admin/stats \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 🚀 Deploy

### Variáveis de Ambiente

Não há variáveis específicas para o sistema admin. Ele usa as mesmas configurações da API principal:

```env
DATABASE_URL=postgresql://user:pass@host:5432/db
SECRET_KEY=sua-chave-secreta
```

### Docker

O sistema admin já está incluído no build do backend. Nenhuma configuração adicional necessária.

```bash
docker-compose up --build
```

### Banco de Dados

O campo `is_admin` já existe no modelo `User`. Se precisar adicionar manualmente:

```sql
-- Adicionar coluna (se não existir)
ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT FALSE;

-- Promover usuário a admin
UPDATE users SET is_admin = TRUE WHERE email = 'admin@example.com';

-- Ver todos os admins
SELECT id, name, email, is_admin FROM users WHERE is_admin = TRUE;
```

---

## 📊 Monitoramento

### Logs

Todas as operações admin são logadas:

```python
# Exemplo de log
[INFO] Admin user_id=1 created word: 'amazing'
[INFO] Admin user_id=1 deleted word_id=542
[INFO] Admin user_id=1 imported 150 words from CSV
```

### Auditoria

Para auditoria completa, considere adicionar:
- Tabela `admin_logs` para registrar todas as ações
- Timestamp de criação/edição em todos os modelos
- IP do admin que fez a ação

---

## 🐛 Troubleshooting

### Erro: "Acesso restrito a administradores"
**Solução**: Verifique se o usuário foi promovido a admin com `make_admin.py`

### Erro: "Could not validate credentials"
**Solução**: Token expirado ou inválido. Faça login novamente.

### Erro na importação CSV: "Linha X: campo 'english' vazio"
**Solução**: Certifique-se que todas as linhas têm os campos obrigatórios preenchidos.

### Importação não atualiza palavras existentes
**Solução**: A comparação é feita pelo campo `english`. Certifique-se que a grafia está exata.

### Não consigo deletar minha própria conta de admin
**Solução**: Isso é proposital para evitar remover o último admin. Use outro admin ou acesse via SQL.

---

## 🎯 Próximas Melhorias

- [ ] **Logs de auditoria**: Tabela para registrar todas as ações admin
- [ ] **Exportação de dados**: Baixar palavras/sentenças como CSV
- [ ] **Backup/Restore**: Interface para backup e restauração do banco
- [ ] **Estatísticas avançadas**: Gráficos de crescimento, usuários ativos por período
- [ ] **Bulk edit**: Editar múltiplas palavras de uma vez
- [ ] **Categorização automática**: IA para sugerir tags e categorias
- [ ] **Preview de importação**: Mostrar preview antes de confirmar import CSV

---

## 📞 Suporte

Para dúvidas ou problemas:
1. Verifique os logs do backend (`docker logs idiomasbr-backend`)
2. Verifique a documentação da API: `http://localhost:8000/docs`
3. Consulte este guia

---

**Versão**: 1.0
**Última Atualização**: 2024-12-19
