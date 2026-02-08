# Início Rápido - Sistema de Administração

## 1. Configurar Primeiro Admin

```bash
# 1. Certifique-se que o Docker está rodando
docker-compose up -d

# 2. Registre um usuário pela interface web
# Acesse: http://localhost:3000/register
# Crie uma conta com seu email

# 3. Promova o usuário a admin
cd backend
python make_admin.py seu-email@example.com

# Resultado esperado:
# ✅ Sucesso! O usuário 'Seu Nome' (seu-email@example.com) agora é administrador
```

## 2. Acessar Painel Admin

```
URL: http://localhost:3000/admin
```

**Requisitos:**
- Estar logado com uma conta admin
- Caso não apareça, faça logout e login novamente

## 3. Importar Palavras em Massa

### Opção A: Usar Template de Exemplo

```bash
# Um arquivo CSV de exemplo já está incluído no projeto:
# template_palavras_exemplo.csv (10 palavras prontas)

# Na interface admin:
# 1. Clique em "Gerenciar Palavras"
# 2. Clique em "📤 Importar CSV"
# 3. Selecione o arquivo template_palavras_exemplo.csv
# 4. Aguarde a importação
```

### Opção B: Criar Seu Próprio CSV

```bash
# 1. Baixe o template clicando em "📥 Baixar Template CSV"
# 2. Edite com Excel, Google Sheets ou editor de texto
# 3. Importe o arquivo
```

**Formato do CSV:**
```csv
english,ipa,portuguese,level,word_type,definition_en,definition_pt,example_en,example_pt,tags
hello,həˈloʊ,olá,A1,interjection,A greeting,Uma saudação,Hello!,Olá!,greetings
```

## 4. Gerenciar Conteúdo

### Palavras
- **Criar:** Clique em "➕ Nova Palavra"
- **Editar:** Clique em "Editar" na linha da palavra
- **Deletar:** Clique em "Deletar" (com confirmação)
- **Buscar:** Use o campo de busca no topo
- **Filtrar:** Selecione um nível (A1-C2)

### Sentenças
Similar às palavras, mas para frases completas.

### Vídeos
Adicione URLs do YouTube para conteúdo educacional.

### Usuários
- Ver todos os usuários
- Promover/despromover admins
- Ativar/desativar contas

## 5. Estatísticas

O dashboard principal mostra:
- Total de usuários (ativos/inativos)
- Total de palavras, sentenças, vídeos
- Total de reviews (interações)
- Distribuição de palavras por nível

## 6. API Endpoints (para desenvolvedores)

```bash
# Autenticação necessária em todas as rotas
# Header: Authorization: Bearer SEU_TOKEN

# Estatísticas
GET /api/admin/stats

# Palavras
GET    /api/admin/words?page=1&per_page=50&search=hello&level=A1
POST   /api/admin/words
PATCH  /api/admin/words/{id}
DELETE /api/admin/words/{id}
POST   /api/admin/words/bulk (importação CSV)

# Sentenças
GET    /api/admin/sentences?page=1&per_page=50
POST   /api/admin/sentences
PATCH  /api/admin/sentences/{id}
DELETE /api/admin/sentences/{id}
POST   /api/admin/sentences/bulk

# Vídeos
GET    /api/admin/videos?page=1&per_page=50
POST   /api/admin/videos
PATCH  /api/admin/videos/{id}
DELETE /api/admin/videos/{id}

# Usuários
GET    /api/admin/users?page=1&per_page=50&search=john
GET    /api/admin/users/{id}
PATCH  /api/admin/users/{id}
DELETE /api/admin/users/{id}
```

## 7. Comandos Úteis

```bash
# Listar todos os admins
python backend/make_admin.py --list

# Remover privilégios de admin
python backend/make_admin.py --revoke usuario@email.com

# Ver logs do backend
docker logs idiomasbr-backend --tail 50

# Reiniciar backend (após mudanças)
docker-compose restart backend

# Ver documentação completa da API
http://localhost:8000/docs
```

## 8. Troubleshooting

### Erro: "Acesso restrito a administradores"
- Certifique-se que rodou `make_admin.py`
- Faça logout e login novamente
- Verifique no banco: `SELECT is_admin FROM users WHERE email = 'seu@email.com'`

### Importação CSV com erros
- Verifique se os campos obrigatórios estão preenchidos (english, portuguese)
- Certifique-se que o arquivo está codificado em UTF-8
- Use vírgula (,) como separador

### Backend não inicia
```bash
docker-compose down
docker-compose up --build -d
docker logs idiomasbr-backend
```

## 9. Segurança

- **Nunca** compartilhe seu token de admin
- **Sempre** use senhas fortes para contas admin
- **Revise** regularmente quem tem acesso admin
- **Faça backup** do banco de dados antes de deletar em massa

## 10. Próximos Passos

1. Importe um vocabulário inicial (100-500 palavras)
2. Adicione sentenças de exemplo
3. Configure vídeos educacionais do YouTube
4. Convide usuários para testar
5. Monitore estatísticas de uso

---

Para documentação completa, veja: **ADMIN_GUIDE.md**

**Suporte**: http://localhost:8000/docs
