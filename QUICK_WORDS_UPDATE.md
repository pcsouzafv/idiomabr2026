# 🚀 Guia Rápido - Atualização de Palavras

## 📋 Resumo do Problema

O arquivo `words_export.csv` tem **10.067 palavras**, mas muitas estão **incompletas**:

- ❌ **29.5%** sem definição em inglês
- ❌ **45.8%** sem definição em português  
- ❌ **67.1%** sem exemplo em inglês
- ❌ **76.3%** sem exemplo em português

**Isso prejudica:**
- Jogos de aprendizado
- Sistema de revisão
- Experiência do usuário

---

## ⚡ Solução Rápida (3 comandos)

```bash
# 1. Analisar situação
docker exec idiomasbr-backend python scripts/update_words_from_csv.py --analyze

# 2. Importar CSV e marcar para enriquecimento
docker exec idiomasbr-backend python scripts/update_words_from_csv.py --import --mark-for-enrichment --apply

# 3. Enriquecer automaticamente
docker exec idiomasbr-backend python scripts/enrich_words_api.py --tags needs_enrichment --batch 50
```

---

## 📊 Gerar Relatório Visual

```bash
# Gerar relatório HTML
docker exec idiomasbr-backend python scripts/generate_words_report.py

# Abrir no navegador
start words_report.html  # Windows
open words_report.html   # Mac
xdg-open words_report.html  # Linux
```

---

## 📚 Documentação Completa

Para mais detalhes, consulte:

- **[WORDS_UPDATE_GUIDE.md](WORDS_UPDATE_GUIDE.md)** - Guia completo com todas as opções
- **[WORD_ENRICHMENT_GUIDE.md](WORD_ENRICHMENT_GUIDE.md)** - Sistema de enriquecimento
- **Script:** `backend/scripts/update_words_from_csv.py`
- **Script:** `backend/scripts/generate_words_report.py`

---

## 🔧 Scripts Criados

### 1. `update_words_from_csv.py`
Atualiza banco de dados a partir do CSV

**Funcionalidades:**
- ✅ Análise de dados (CSV e banco)
- ✅ Importação inteligente (só preenche campos vazios)
- ✅ Marcação de palavras incompletas
- ✅ DRY-RUN mode (testar sem aplicar)

### 2. `generate_words_report.py`
Gera relatório HTML visual

**Inclui:**
- ✅ Estatísticas gerais
- ✅ Gráficos de progresso
- ✅ Distribuição por nível
- ✅ Lista de palavras prioritárias
- ✅ Recomendações de ação

---

## 💡 Workflow Recomendado

```bash
# 1. BACKUP
docker exec -it idiomasbr-postgres pg_dump -U idiomasbr -d idiomasbr > backup.sql

# 2. ANALISAR
docker exec idiomasbr-backend python scripts/update_words_from_csv.py --analyze

# 3. TESTAR (DRY-RUN)
docker exec idiomasbr-backend python scripts/update_words_from_csv.py --import --mark-for-enrichment

# 4. APLICAR
docker exec idiomasbr-backend python scripts/update_words_from_csv.py --import --mark-for-enrichment --apply

# 5. ENRIQUECER
docker exec idiomasbr-backend python scripts/enrich_words_api.py --tags needs_enrichment

# 6. VERIFICAR
docker exec idiomasbr-backend python scripts/generate_words_report.py
```

---

## 📈 Meta de Qualidade

| Campo | Antes | Meta |
|-------|-------|------|
| Definição EN | 70.5% | **95%+** |
| Definição PT | 54.2% | **95%+** |
| Exemplo EN | 32.9% | **85%+** |
| Exemplo PT | 23.7% | **85%+** |
| Word Type | 85.5% | **90%+** |
| IPA | 97.7% | **100%** |

---

## ❓ Dúvidas Frequentes

### Como funciona a importação?
- Compara palavras por `english` (case-insensitive)
- Atualiza **apenas campos vazios** (não sobrescreve)
- Cria novas palavras se não existirem

### O que é DRY-RUN?
- Modo de teste que **não modifica o banco**
- Mostra o que será feito sem aplicar
- Use para verificar antes de aplicar mudanças

### Como funciona o enriquecimento?
- Usa APIs externas (Free Dictionary, Datamuse)
- Preenche campos vazios automaticamente
- Processa palavras marcadas com `needs_enrichment`

### Posso reverter mudanças?
- Sim, se fez backup antes
- Restaure com: `docker exec -i idiomasbr-postgres psql -U idiomasbr -d idiomasbr < backup.sql`

---

## 🆘 Troubleshooting

### Erro: "CSV não encontrado"
```bash
# Verificar caminho
docker exec idiomasbr-backend ls -la /app/words_export.csv

# Copiar para container se necessário
docker cp words_export.csv idiomasbr-backend:/app/
```

### Erro de conexão com banco
```bash
# Verificar se está rodando
docker-compose ps postgres

# Reiniciar se necessário
docker-compose restart postgres
```

---

## 📞 Suporte

- Documentação completa: [WORDS_UPDATE_GUIDE.md](WORDS_UPDATE_GUIDE.md)
- Sistema de enriquecimento: [WORD_ENRICHMENT_GUIDE.md](WORD_ENRICHMENT_GUIDE.md)
- Integração APIs: [API_INTEGRATION_GUIDE.md](API_INTEGRATION_GUIDE.md)

---

**Criado em:** Janeiro 2026  
**Versão:** 1.0
