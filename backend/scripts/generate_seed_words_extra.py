import argparse
import csv
import os
import re
from pathlib import Path

from sqlalchemy import create_engine, text


# Mantém propositalmente apenas palavras de 1 termo e letras A-Z
# para funcionar bem em forca/ditado.
# Candidatos: podem conter palavras já existentes no banco.
# O script filtra e exporta apenas as que ainda não existem.
CANDIDATES = [
    # A1 - pessoas / família / pronomes simples
    ("name", "nome", "A1", "general"),
    ("age", "idade", "A1", "general"),
    ("job", "trabalho, emprego", "A1", "work"),
    ("boss", "chefe", "A1", "work"),
    ("neighbor", "vizinho", "A1", "people"),
    ("guest", "convidado", "A1", "people"),
    ("couple", "casal", "A1", "people"),
    ("parents", "pais", "A1", "people"),
    ("kid", "criança", "A1", "people"),
    ("husband", "marido", "A1", "people"),
    ("wife", "esposa", "A1", "people"),
    ("uncle", "tio", "A1", "people"),
    ("aunt", "tia", "A1", "people"),
    ("cousin", "primo(a)", "A1", "people"),
    ("grandma", "avó", "A1", "people"),
    ("grandpa", "avô", "A1", "people"),

    # A1 - verbos comuns (1 palavra)
    ("meet", "conhecer, encontrar", "A1", "verb"),
    ("kiss", "beijar", "A1", "verb"),
    ("hug", "abraçar", "A1", "verb"),
    ("smile", "sorrir", "A1", "verb"),
    ("laugh", "rir", "A1", "verb"),
    ("cry", "chorar", "A1", "verb"),
    ("jump", "pular", "A1", "verb"),
    ("swim", "nadar", "A1", "verb"),
    ("drive", "dirigir", "A1", "verb"),
    ("ride", "andar (de bicicleta/cavalo)", "A1", "verb"),
    ("dance", "dançar", "A1", "verb"),
    ("sing", "cantar", "A1", "verb"),
    ("touch", "tocar", "A1", "verb"),
    ("push", "empurrar", "A1", "verb"),
    ("pull", "puxar", "A1", "verb"),
    ("hold", "segurar", "A1", "verb"),
    ("turn", "virar", "A1", "verb"),
    ("move", "mover", "A1", "verb"),

    # A1 - corpo
    ("head", "cabeça", "A1", "body"),
    ("hair", "cabelo", "A1", "body"),
    ("face", "rosto", "A1", "body"),
    ("eye", "olho", "A1", "body"),
    ("ear", "orelha", "A1", "body"),
    ("nose", "nariz", "A1", "body"),
    ("mouth", "boca", "A1", "body"),
    ("tooth", "dente", "A1", "body"),
    ("neck", "pescoço", "A1", "body"),
    ("shoulder", "ombro", "A1", "body"),
    ("arm", "braço", "A1", "body"),
    ("elbow", "cotovelo", "A1", "body"),
    ("hand", "mão", "A1", "body"),
    ("finger", "dedo", "A1", "body"),
    ("leg", "perna", "A1", "body"),
    ("knee", "joelho", "A1", "body"),
    ("foot", "pé", "A1", "body"),
    ("toe", "dedo do pé", "A1", "body"),
    ("back", "costas", "A1", "body"),
    ("heart", "coração", "A1", "body"),
    ("skin", "pele", "A1", "body"),

    # A1 - roupas
    ("shirt", "camisa", "A1", "clothes"),
    ("pants", "calça", "A1", "clothes"),
    ("shorts", "bermuda", "A1", "clothes"),
    ("dress", "vestido", "A1", "clothes"),
    ("skirt", "saia", "A1", "clothes"),
    ("jacket", "jaqueta", "A1", "clothes"),
    ("coat", "casaco", "A1", "clothes"),
    ("shoes", "sapatos", "A1", "clothes"),
    ("socks", "meias", "A1", "clothes"),
    ("hat", "chapéu", "A1", "clothes"),
    ("belt", "cinto", "A1", "clothes"),

    # A1 - objetos casa
    ("cup", "copo", "A1", "object"),
    ("glass", "copo de vidro", "A1", "object"),
    ("plate", "prato", "A1", "object"),
    ("bowl", "tigela", "A1", "object"),
    ("spoon", "colher", "A1", "object"),
    ("fork", "garfo", "A1", "object"),
    ("knife", "faca", "A1", "object"),
    ("bottle", "garrafa", "A1", "object"),
    ("box", "caixa", "A1", "object"),
    ("bag", "bolsa, saco", "A1", "object"),
    ("soap", "sabão", "A1", "object"),
    ("towel", "toalha", "A1", "object"),
    ("mirror", "espelho", "A1", "object"),
    ("lamp", "lâmpada", "A1", "object"),

    # A1 - natureza / clima
    ("sun", "sol", "A1", "nature"),
    ("moon", "lua", "A1", "nature"),
    ("star", "estrela", "A1", "nature"),
    ("sky", "céu", "A1", "nature"),
    ("cloud", "nuvem", "A1", "weather"),
    ("rain", "chuva", "A1", "weather"),
    ("snow", "neve", "A1", "weather"),
    ("wind", "vento", "A1", "weather"),
    ("storm", "tempestade", "A1", "weather"),
    ("tree", "árvore", "A1", "nature"),
    ("flower", "flor", "A1", "nature"),
    ("grass", "grama", "A1", "nature"),
    ("river", "rio", "A1", "nature"),
    ("lake", "lago", "A1", "nature"),
    ("sea", "mar", "A1", "nature"),

    # A1 - animais
    ("dog", "cachorro", "A1", "animal"),
    ("cat", "gato", "A1", "animal"),
    ("bird", "pássaro", "A1", "animal"),
    ("rabbit", "coelho", "A1", "animal"),
    ("mouse", "rato", "A1", "animal"),
    ("horse", "cavalo", "A1", "animal"),
    ("cow", "vaca", "A1", "animal"),
    ("pig", "porco", "A1", "animal"),
    ("sheep", "ovelha", "A1", "animal"),
    ("goat", "cabra", "A1", "animal"),

    # A1 - adjetivos simples
    ("tall", "alto", "A1", "adjective"),
    ("short", "baixo", "A1", "adjective"),
    ("thin", "magro", "A1", "adjective"),
    ("fat", "gordo", "A1", "adjective"),
    ("loud", "barulhento", "A1", "adjective"),
    ("soft", "macio", "A1", "adjective"),
    ("warm", "morno, quente", "A1", "adjective"),
    ("cool", "fresco", "A1", "adjective"),
    ("sweet", "doce", "A1", "adjective"),
    ("sour", "azedo", "A1", "adjective"),

    # A2 - saúde
    ("pain", "dor", "A2", "health"),
    ("fever", "febre", "A2", "health"),
    ("cough", "tosse", "A2", "health"),
    ("cold", "resfriado", "A2", "health"),
    ("flu", "gripe", "A2", "health"),
    ("medicine", "remédio", "A2", "health"),
    ("pill", "pílula", "A2", "health"),
    ("clinic", "clínica", "A2", "health"),
    ("dentist", "dentista", "A2", "health"),

    # A2 - casa/cidade
    ("apartment", "apartamento", "A2", "place"),
    ("building", "prédio", "A2", "place"),
    ("elevator", "elevador", "A2", "place"),
    ("stairs", "escadas", "A2", "place"),
    ("corner", "esquina", "A2", "place"),
    ("square", "praça", "A2", "place"),
    ("traffic", "trânsito", "A2", "travel"),
    ("accident", "acidente", "A2", "travel"),

    # A2 - verbos úteis
    ("borrow", "pegar emprestado", "A2", "verb"),
    ("lend", "emprestar", "A2", "verb"),
    ("miss", "sentir falta, perder", "A2", "verb"),
    ("join", "juntar-se, entrar", "A2", "verb"),
    ("repair", "consertar", "A2", "verb"),
    ("deliver", "entregar", "A2", "verb"),
    ("order", "pedir, encomendar", "A2", "verb"),
    ("reserve", "reservar", "A2", "verb"),
    ("cancel", "cancelar", "A2", "verb"),
    ("return", "devolver, retornar", "A2", "verb"),

    # A2 - sentimentos
    ("excited", "animado", "A2", "emotion"),
    ("bored", "entediado", "A2", "emotion"),
    ("worried", "preocupado", "A2", "emotion"),
    ("relaxed", "relaxado", "A2", "emotion"),
    ("curious", "curioso", "A2", "emotion"),
    ("proud", "orgulhoso", "A2", "emotion"),
    ("surprised", "surpreso", "A2", "emotion"),

    # B1 - trabalho/estudo
    ("interview", "entrevista", "B1", "work"),
    ("salary", "salário", "B1", "work"),
    ("contract", "contrato", "B1", "work"),
    ("invoice", "fatura", "B1", "work"),
    ("receipt", "recibo", "B1", "money"),
    ("refund", "reembolso", "B1", "money"),
    ("warranty", "garantia", "B1", "general"),
    ("complaint", "reclamação", "B1", "general"),
    ("training", "treinamento", "B1", "work"),
    ("skill", "habilidade", "B1", "work"),
    ("degree", "diploma", "B1", "education"),
    ("exam", "prova", "B1", "education"),
    ("lesson", "lição, aula", "B1", "education"),
    ("topic", "tópico", "B1", "education"),

    # B1 - tecnologia (simples)
    ("password", "senha", "B1", "tech"),
    ("account", "conta", "B1", "tech"),
    ("profile", "perfil", "B1", "tech"),
    ("download", "baixar", "B1", "tech"),
    ("upload", "enviar (arquivo)", "B1", "tech"),
    ("website", "site", "B1", "tech"),

    # B1 - verbos de comunicação
    ("reply", "responder", "B1", "verb"),
    ("report", "relatar, reportar", "B1", "verb"),
    ("discuss", "discutir", "B1", "verb"),
    ("propose", "propor", "B1", "verb"),
    ("approve", "aprovar", "B1", "verb"),
    ("reject", "rejeitar", "B1", "verb"),
    ("update", "atualizar", "B1", "verb"),
    ("organize", "organizar", "B1", "verb"),
    ("manage", "gerenciar", "B1", "verb"),

    # B2 - abstratas
    ("benefit", "benefício", "B2", "general"),
    ("risk", "risco", "B2", "general"),
    ("trend", "tendência", "B2", "general"),
    ("insight", "insight, percepção", "B2", "general"),
    ("factor", "fator", "B2", "general"),
    ("variable", "variável", "B2", "general"),
    ("approach", "abordagem", "B2", "general"),
    ("principle", "princípio", "B2", "general"),
    ("tradeoff", "compensação", "B2", "general"),

    # C1/C2 - avançadas (seleção curta)
    ("diligence", "diligência", "C1", "general"),
    ("feasibility", "viabilidade", "C1", "work"),
    ("granular", "granular, detalhado", "C1", "adjective"),
    ("holistic", "holístico", "C1", "adjective"),
    ("verbosity", "verbosidade", "C2", "general"),
    ("convergence", "convergência", "C2", "general"),
    # A1 - casa (extra)
    ("floor", "chão, andar", "A1", "place"),
    ("wall", "parede", "A1", "place"),
    ("roof", "telhado", "A1", "place"),
    ("yard", "quintal", "A1", "place"),
    ("garden", "jardim", "A1", "place"),
    ("sink", "pia", "A1", "object"),
    ("shower", "chuveiro", "A1", "object"),
    ("toilet", "vaso sanitário", "A1", "object"),
    ("fridge", "geladeira", "A1", "object"),
    ("oven", "forno", "A1", "object"),
    ("stove", "fogão", "A1", "object"),
    ("knife", "faca", "A1", "object"),
    ("spice", "tempero", "A1", "food"),

    # A1 - escola (extra)
    ("class", "aula, turma", "A1", "education"),
    ("desk", "carteira, mesa", "A1", "education"),
    ("board", "quadro", "A1", "education"),
    ("chalk", "giz", "A1", "education"),
    ("eraser", "apagador", "A1", "education"),
    ("pencil", "lápis", "A1", "education"),
    ("notebook", "caderno", "A1", "education"),
    ("homework", "lição de casa", "A1", "education"),

    # A1 - verbos adicionais
    ("teach", "ensinar", "A1", "verb"),
    ("practice", "praticar", "A1", "verb"),
    ("share", "compartilhar", "A1", "verb"),
    ("save", "salvar, economizar", "A1", "verb"),
    ("spend", "gastar", "A1", "verb"),
    ("send", "enviar", "A1", "verb"),
    ("receive", "receber", "A1", "verb"),
    ("break", "quebrar", "A1", "verb"),
    ("fix", "consertar", "A1", "verb"),
    ("build", "construir", "A1", "verb"),
    ("draw", "desenhar", "A1", "verb"),
    ("paint", "pintar", "A1", "verb"),

    # A2 - compras/serviços
    ("price", "preço", "A2", "money"),
    ("discount", "desconto", "A2", "money"),
    ("change", "troco, mudança", "A2", "money"),
    ("cash", "dinheiro", "A2", "money"),
    ("credit", "crédito", "A2", "money"),
    ("debit", "débito", "A2", "money"),
    ("store", "loja", "A2", "place"),
    ("clerk", "atendente", "A2", "work"),
    ("queue", "fila", "A2", "general"),
    ("service", "serviço", "A2", "general"),

    # A2 - transporte
    ("bus", "ônibus", "A2", "travel"),
    ("train", "trem", "A2", "travel"),
    ("taxi", "táxi", "A2", "travel"),
    ("subway", "metrô", "A2", "travel"),
    ("road", "estrada", "A2", "travel"),
    ("highway", "rodovia", "A2", "travel"),
    ("helmet", "capacete", "A2", "travel"),
    ("engine", "motor", "A2", "travel"),
    ("wheel", "roda", "A2", "travel"),

    # B1 - tecnologia (mais)
    ("device", "dispositivo", "B1", "tech"),
    ("screen", "tela", "B1", "tech"),
    ("keyboard", "teclado", "B1", "tech"),
    ("mouse", "mouse", "B1", "tech"),
    ("printer", "impressora", "B1", "tech"),
    ("network", "rede", "B1", "tech"),
    ("signal", "sinal", "B1", "tech"),
    ("battery", "bateria", "B1", "tech"),
    ("charger", "carregador", "B1", "tech"),
    ("storage", "armazenamento", "B1", "tech"),
    ("privacy", "privacidade", "B1", "general"),
    ("security", "segurança", "B1", "general"),

    # B1 - saúde/rotina
    ("diet", "dieta", "B1", "health"),
    ("exercise", "exercício", "B1", "health"),
    ("injury", "lesão", "B1", "health"),
    ("symptom", "sintoma", "B1", "health"),
    ("allergy", "alergia", "B1", "health"),
    ("appointment", "consulta, compromisso", "B1", "health"),

    # B2 - trabalho (mais)
    ("proposal", "proposta", "B2", "work"),
    ("approval", "aprovação", "B2", "work"),
    ("rejection", "rejeição", "B2", "work"),
    ("timeline", "cronograma", "B2", "work"),
    ("deliverable", "entregável", "B2", "work"),
    ("alignment", "alinhamento", "B2", "work"),
    ("ownership", "responsabilidade", "B2", "work"),
    ("governance", "governança", "B2", "work"),

    # C1/C2 - avançadas (mais)
    ("prerequisite", "pré-requisito", "C1", "work"),
    ("benchmark", "referência, parâmetro", "C1", "work"),
    ("interoperability", "interoperabilidade", "C2", "tech"),
    ("scalability", "escalabilidade", "C2", "tech"),

    # B2 - tecnologia/engenharia de software (1 palavra)
    ("algorithm", "algoritmo", "B2", "tech"),
    ("architecture", "arquitetura", "B2", "tech"),
    ("pipeline", "pipeline", "B2", "tech"),
    ("deployment", "implantação, deploy", "B2", "tech"),
    ("rollback", "reversão", "B2", "tech"),
    ("downtime", "indisponibilidade", "B2", "tech"),
    ("outage", "queda, indisponibilidade", "B2", "tech"),
    ("incident", "incidente", "B2", "tech"),
    ("monitoring", "monitoramento", "B2", "tech"),
    ("telemetry", "telemetria", "B2", "tech"),
    ("latency", "latência", "B2", "tech"),
    ("throughput", "vazão", "B2", "tech"),
    ("bandwidth", "largura de banda", "B2", "tech"),
    ("encryption", "criptografia", "B2", "tech"),
    ("decryption", "descriptografia", "B2", "tech"),
    ("credential", "credencial", "B2", "tech"),
    ("token", "token", "B2", "tech"),
    ("session", "sessão", "B2", "tech"),
    ("cookie", "cookie", "B2", "tech"),
    ("database", "banco de dados", "B2", "tech"),
    ("schema", "esquema", "B2", "tech"),
    ("index", "índice", "B2", "tech"),
    ("query", "consulta", "B2", "tech"),
    ("cache", "cache", "B2", "tech"),
    ("backup", "backup", "B2", "tech"),
    ("restore", "restauração", "B2", "tech"),
    ("migrate", "migrar", "B2", "tech"),
    ("integrate", "integrar", "B2", "tech"),
    ("debug", "depurar", "B2", "tech"),

    # B2 - negócios/finanças
    ("revenue", "receita", "B2", "money"),
    ("expense", "despesa", "B2", "money"),
    ("profit", "lucro", "B2", "money"),
    ("loss", "prejuízo", "B2", "money"),
    ("pricing", "precificação", "B2", "money"),
    ("invoice", "fatura", "B2", "money"),
    ("tax", "imposto", "B2", "money"),
    ("fee", "taxa", "B2", "money"),
    ("interest", "juros, interesse", "B2", "money"),
    ("inflation", "inflação", "B2", "money"),
    ("equity", "patrimônio líquido", "B2", "money"),
    ("asset", "ativo", "B2", "money"),
    ("liability", "passivo, responsabilidade", "B2", "money"),
    ("budget", "orçamento", "B2", "money"),
    ("forecast", "previsão", "B2", "money"),

    # B2 - comunicação
    ("clarify", "esclarecer", "B2", "verb"),
    ("summarize", "resumir", "B2", "verb"),
    ("prioritize", "priorizar", "B2", "verb"),
    ("coordinate", "coordenar", "B2", "verb"),
    ("escalate", "escalar (um problema)", "B2", "verb"),
    ("delegate", "delegar", "B2", "verb"),
    ("document", "documentar", "B2", "verb"),
    ("validate", "validar", "B2", "verb"),
    ("verify", "verificar", "B2", "verb"),
    ("resolve", "resolver", "B2", "verb"),

    # C1 - jurídico/ética/gestão
    ("consent", "consentimento", "C1", "general"),
    ("breach", "violação", "C1", "general"),
    ("audit", "auditoria", "C1", "work"),
    ("regulation", "regulamentação", "C1", "work"),
    ("litigation", "litígio", "C1", "work"),
    ("penalty", "penalidade", "C1", "work"),
    ("governance", "governança", "C1", "work"),
    ("oversight", "supervisão", "C1", "work"),
    ("ethics", "ética", "C1", "general"),
    ("integrity", "integridade", "C1", "general"),

    # C1 - ciência/saúde
    ("molecule", "molécula", "C1", "academic"),
    ("gravity", "gravidade", "C1", "academic"),
    ("oxygen", "oxigênio", "C1", "academic"),
    ("carbon", "carbono", "C1", "academic"),
    ("protein", "proteína", "C1", "health"),
    ("vitamin", "vitamina", "C1", "health"),
    ("fiber", "fibra", "C1", "health"),
    ("cholesterol", "colesterol", "C1", "health"),
]


def _get_db_url(db_url: str | None) -> str:
    url = db_url or os.getenv("DATABASE_URL")
    if not url:
        raise SystemExit(
            "DATABASE_URL não definido. Rode dentro do container do backend ou passe --db-url."
        )
    return url


def _missing_from_db(engine, english_words: list[str]) -> set[str]:
    missing: set[str] = set()

    # Faz batches para evitar SQL gigante
    batch_size = 300
    for i in range(0, len(english_words), batch_size):
        batch = english_words[i : i + batch_size]
        values_sql = ",".join(["(:w" + str(j) + ")" for j in range(len(batch))])
        params = {"w" + str(j): batch[j] for j in range(len(batch))}

        sql = f"""
            WITH candidates(english) AS (VALUES {values_sql})
            SELECT c.english
            FROM candidates c
            LEFT JOIN words w ON lower(w.english) = lower(c.english)
            WHERE w.id IS NULL
        """

        rows = engine.connect().execute(text(sql), params).fetchall()
        for (word,) in rows:
            missing.add(str(word))

    return missing


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Gera CSV de palavras extras sem repetição, filtrando as já existentes no banco"
    )
    parser.add_argument("--db-url", help="Sobrescreve DATABASE_URL")
    parser.add_argument(
        "--target",
        type=int,
        default=300,
        help="Quantidade alvo de novas palavras (após filtrar as existentes)",
    )
    parser.add_argument(
        "--out",
        default="seed_words_extra_unique_v2.csv",
        help="Nome do arquivo CSV de saída dentro de backend/data",
    )
    args = parser.parse_args()

    out_path = Path(__file__).resolve().parents[1] / "data" / args.out

    valid_re = re.compile(r"^[A-Za-z]+$")
    unique_candidates: dict[str, tuple[str, str, str, str]] = {}
    for english, portuguese, level, tags in CANDIDATES:
        e = english.strip()
        if not valid_re.match(e):
            raise SystemExit(f"english inválido (use apenas A-Z): {english!r}")
        unique_candidates.setdefault(e.lower(), (e, portuguese.strip(), level, tags))

    engine = create_engine(_get_db_url(args.db_url), pool_pre_ping=True)
    candidate_english = [v[0] for v in unique_candidates.values()]
    missing = _missing_from_db(engine, candidate_english)

    rows = []
    for key, (e, pt, level, tags) in unique_candidates.items():
        if e in missing:
            rows.append({"english": e, "ipa": "", "portuguese": pt, "level": level, "tags": tags})
            if len(rows) >= args.target:
                break

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["english", "ipa", "portuguese", "level", "tags"],
            delimiter=";",
        )
        writer.writeheader()
        writer.writerows(rows)

    print(
        f"Gerado: {out_path} (candidates={len(unique_candidates)}, missing={len(missing)}, exported={len(rows)})"
    )


if __name__ == "__main__":
    main()
