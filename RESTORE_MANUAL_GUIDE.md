# Guia Manual de Restauração do Banco de Produção

## Problema Identificado

O `gsutil` está com problema de permissões no Windows. Aqui estão **3 alternativas** para restaurar o banco:

## Opção 1: Via Console Web do GCP (MAIS FÁCIL ✅)

### Passo a Passo:

1. **Fazer Upload do Dump**
   - Acesse: https://console.cloud.google.com/storage/browser?project=idiomasbr
   - Crie um bucket (se não existir): `idiomasbr-db-imports`
   - Faça upload do arquivo `dump_final.sql`

2. **Importar no Cloud SQL**
   - Acesse: https://console.cloud.google.com/sql/instances/idiomasbr-db?project=idiomasbr
   - Clique em "IMPORT"
   - Selecione o arquivo `gs://idiomasbr-db-imports/dump_final.sql`
   - Database: `idiomasbr`
   - Clique em "IMPORT"

3. **Aguardar Conclusão**
   - A importação leva ~2-5 minutos
   - Você verá o progresso na aba "Operations"

## Opção 2: Via Cloud Shell (NO NAVEGADOR ✅)

1. **Abrir Cloud Shell**
   - Acesse: https://console.cloud.google.com/?cloudshell=true
   - Aguarde o terminal carregar

2. **Fazer Upload do Dump**
   ```bash
   # Fazer upload via interface do Cloud Shell
   # Clique no menu (⋮) → Upload File
   # Selecione dump_final.sql
   ```

3. **Executar Importação**
   ```bash
   # Criar bucket
   gsutil mb -l us-central1 gs://idiomasbr-db-imports

   # Upload do dump
   gsutil cp dump_final.sql gs://idiomasbr-db-imports/

   # Importar
   gcloud sql import sql idiomasbr-db \
       gs://idiomasbr-db-imports/dump_final.sql \
       --database=idiomasbr \
       --quiet
   ```

## Opção 3: Fixar Permissões do gsutil (Windows)

### Execute como Administrador:

```powershell
# PowerShell como Administrador

# 1. Encontrar diretório do gcloud
$gcloudPath = (Get-Command gcloud).Source
$sdkPath = Split-Path (Split-Path $gcloudPath)

# 2. Dar permissões
icacls "$sdkPath\platform\gsutil" /grant ${env:USERNAME}:F /T

# 3. Testar
gsutil --version
```

Depois tente novamente:
```bash
bash restore_production.sh
```

## Opção 4: Restauração Via Python (Programática)

Se preferir automatizar, aqui está um script Python:

```python
# restore_db.py
from google.cloud import storage, sql_v1
import os

PROJECT_ID = "idiomasbr"
BUCKET_NAME = "idiomasbr-db-imports"
DUMP_FILE = "dump_final.sql"
INSTANCE_NAME = "idiomasbr-db"
DATABASE_NAME = "idiomasbr"

# 1. Upload para Cloud Storage
storage_client = storage.Client(project=PROJECT_ID)
bucket = storage_client.bucket(BUCKET_NAME)

# Criar bucket se não existir
if not bucket.exists():
    bucket = storage_client.create_bucket(BUCKET_NAME, location="us-central1")

# Upload do dump
blob = bucket.blob(DUMP_FILE)
blob.upload_from_filename(DUMP_FILE)
print(f"✅ Upload concluído: gs://{BUCKET_NAME}/{DUMP_FILE}")

# 2. Importar no Cloud SQL
sql_client = sql_v1.SqlInstancesServiceClient()
import_request = sql_v1.InstancesImportRequest(
    instance=INSTANCE_NAME,
    project=PROJECT_ID,
    instances_import_request_body=sql_v1.ImportContext(
        uri=f"gs://{BUCKET_NAME}/{DUMP_FILE}",
        database=DATABASE_NAME,
        file_type=sql_v1.ImportContext.SqlFileType.SQL,
    ),
)

operation = sql_client.import_(request=import_request)
print(f"✅ Importação iniciada: {operation.name}")
print("⏳ Aguarde ~2-5 minutos para concluir")
```

Executar:
```bash
pip install google-cloud-storage google-cloud-sql
python restore_db.py
```

## Verificação Pós-Restauração

Após restaurar por qualquer método, verifique:

### 1. Via gcloud:
```bash
# Conectar no banco
gcloud sql connect idiomasbr-db --user=postgres --database=idiomasbr

# No psql, executar:
SELECT COUNT(*) FROM words;
SELECT COUNT(*) FROM users;
\dt  # Listar tabelas
```

### 2. Via Aplicação:
```bash
# Testar endpoint
curl https://idiomasbr-backend-7rpgvb7uga-uc.a.run.app/health

# Acessar frontend
# https://idiomasbr-frontend-7rpgvb7uga-uc.a.run.app
```

## Troubleshooting

### Erro: "Import operation failed"
**Causa**: Erro no SQL (incompatibilidade de versão)
**Solução**:
- Verifique se o dump é PostgreSQL 15
- Veja os logs da operação no console

### Erro: "Access denied to bucket"
**Causa**: Service account do Cloud SQL sem permissão
**Solução**:
```bash
# Dar permissão ao Cloud SQL
gsutil iam ch \
    serviceAccount:YOUR-SA@gcp-sa-cloud-sql.iam.gserviceaccount.com:objectViewer \
    gs://idiomasbr-db-imports
```

### Erro: "Database not found"
**Causa**: Database `idiomasbr` não existe
**Solução**:
```bash
# Criar database
gcloud sql databases create idiomasbr --instance=idiomasbr-db
```

## Recomendação

Para você, **recomendo a Opção 1 (Console Web)** por ser:
- Mais visual e fácil
- Não depende de permissões locais
- Funciona 100% no navegador
- Interface amigável

Link direto: https://console.cloud.google.com/storage/create-bucket?project=idiomasbr
