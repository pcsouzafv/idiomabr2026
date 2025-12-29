"""
Script para adicionar palavras faltantes ate completar 5000
Adiciona verbos, pronomes, adverbios e palavras essenciais
"""
import sys
sys.path.append('backend')

from app.core.database import SessionLocal
from app.models.word import Word
from sqlalchemy import func

# Novas palavras para adicionar (verbos, pronomes, adverbios, etc)
new_words = [
    # Pronomes
    ("I", "aɪ", "eu", "A1", "pronome"),
    ("you", "juː", "você, tu", "A1", "pronome"),
    ("he", "hiː", "ele", "A1", "pronome"),
    ("she", "ʃiː", "ela", "A1", "pronome"),
    ("it", "ɪt", "isto, isso", "A1", "pronome"),
    ("we", "wiː", "nós", "A1", "pronome"),
    ("they", "ðeɪ", "eles, elas", "A1", "pronome"),
    ("me", "miː", "me, mim", "A1", "pronome"),
    ("him", "hɪm", "o, ele (objeto)", "A1", "pronome"),
    ("her", "hɜːr", "a, ela (objeto)", "A1", "pronome"),
    ("us", "ʌs", "nos", "A1", "pronome"),
    ("them", "ðem", "os, as, eles (objeto)", "A1", "pronome"),
    ("my", "maɪ", "meu, minha", "A1", "pronome possessivo"),
    ("your", "jɔːr", "seu, sua, teu, tua", "A1", "pronome possessivo"),
    ("his", "hɪz", "dele", "A1", "pronome possessivo"),
    ("its", "ɪts", "seu, sua (neutro)", "A1", "pronome possessivo"),
    ("our", "aʊər", "nosso, nossa", "A1", "pronome possessivo"),
    ("their", "ðeər", "deles, delas", "A1", "pronome possessivo"),
    ("this", "ðɪs", "este, esta, isto", "A1", "pronome demonstrativo"),
    ("that", "ðæt", "aquele, aquela, aquilo", "A1", "pronome demonstrativo"),
    ("these", "ðiːz", "estes, estas", "A1", "pronome demonstrativo"),
    ("those", "ðoʊz", "aqueles, aquelas", "A1", "pronome demonstrativo"),

    # Verbos principais (to be, to have, to do)
    ("be", "biː", "ser, estar", "A1", "verbo"),
    ("am", "æm", "sou, estou", "A1", "verbo"),
    ("is", "ɪz", "é, está", "A1", "verbo"),
    ("are", "ɑːr", "são, estão, és", "A1", "verbo"),
    ("was", "wɒz", "era, estava, fui", "A1", "verbo"),
    ("were", "wɜːr", "eram, estavam, foram", "A1", "verbo"),
    ("been", "biːn", "sido, estado", "A1", "verbo"),
    ("have", "hæv", "ter", "A1", "verbo"),
    ("has", "hæz", "tem", "A1", "verbo"),
    ("had", "hæd", "tinha, teve", "A1", "verbo"),
    ("do", "duː", "fazer", "A1", "verbo"),
    ("does", "dʌz", "faz", "A1", "verbo"),
    ("did", "dɪd", "fez", "A1", "verbo"),
    ("done", "dʌn", "feito", "A1", "verbo"),

    # Verbos modais
    ("can", "kæn", "poder, conseguir", "A1", "verbo modal"),
    ("could", "kʊd", "poderia, conseguia", "A1", "verbo modal"),
    ("will", "wɪl", "irá, vai", "A1", "verbo modal"),
    ("would", "wʊd", "iria", "A1", "verbo modal"),
    ("shall", "ʃæl", "deverá", "A1", "verbo modal"),
    ("should", "ʃʊd", "deveria", "A1", "verbo modal"),
    ("may", "meɪ", "pode, talvez", "A1", "verbo modal"),
    ("might", "maɪt", "poderia, talvez", "A1", "verbo modal"),
    ("must", "mʌst", "deve, ter que", "A1", "verbo modal"),

    # Verbos comuns
    ("go", "goʊ", "ir", "A1", "verbo"),
    ("went", "went", "foi", "A1", "verbo"),
    ("gone", "gɒn", "ido", "A1", "verbo"),
    ("come", "kʌm", "vir", "A1", "verbo"),
    ("came", "keɪm", "veio", "A1", "verbo"),
    ("get", "get", "obter, conseguir", "A1", "verbo"),
    ("got", "gɒt", "obteve, conseguiu", "A1", "verbo"),
    ("make", "meɪk", "fazer, criar", "A1", "verbo"),
    ("made", "meɪd", "fez, criou", "A1", "verbo"),
    ("take", "teɪk", "pegar, levar", "A1", "verbo"),
    ("took", "tʊk", "pegou, levou", "A1", "verbo"),
    ("taken", "teɪkən", "pegado, levado", "A1", "verbo"),
    ("see", "siː", "ver", "A1", "verbo"),
    ("saw", "sɔː", "viu", "A1", "verbo"),
    ("seen", "siːn", "visto", "A1", "verbo"),
    ("know", "noʊ", "saber, conhecer", "A1", "verbo"),
    ("knew", "njuː", "sabia, conhecia", "A1", "verbo"),
    ("known", "noʊn", "sabido, conhecido", "A1", "verbo"),
    ("think", "θɪŋk", "pensar, achar", "A1", "verbo"),
    ("thought", "θɔːt", "pensou, achou", "A1", "verbo"),
    ("say", "seɪ", "dizer", "A1", "verbo"),
    ("said", "sed", "disse", "A1", "verbo"),
    ("tell", "tel", "contar, dizer", "A1", "verbo"),
    ("told", "toʊld", "contou, disse", "A1", "verbo"),
    ("give", "gɪv", "dar", "A1", "verbo"),
    ("gave", "geɪv", "deu", "A1", "verbo"),
    ("given", "gɪvən", "dado", "A1", "verbo"),
    ("find", "faɪnd", "encontrar, achar", "A1", "verbo"),
    ("found", "faʊnd", "encontrou, achou", "A1", "verbo"),
    ("want", "wɒnt", "querer", "A1", "verbo"),
    ("need", "niːd", "precisar", "A1", "verbo"),
    ("try", "traɪ", "tentar", "A1", "verbo"),
    ("tried", "traɪd", "tentou", "A1", "verbo"),
    ("use", "juːz", "usar", "A1", "verbo"),
    ("used", "juːzd", "usou", "A1", "verbo"),
    ("ask", "æsk", "perguntar", "A1", "verbo"),
    ("asked", "æskt", "perguntou", "A1", "verbo"),
    ("feel", "fiːl", "sentir", "A1", "verbo"),
    ("felt", "felt", "sentiu", "A1", "verbo"),
    ("become", "bɪkʌm", "tornar-se", "A2", "verbo"),
    ("became", "bɪkeɪm", "tornou-se", "A2", "verbo"),
    ("leave", "liːv", "sair, deixar", "A1", "verbo"),
    ("left", "left", "saiu, deixou", "A1", "verbo"),
    ("put", "pʊt", "colocar, pôr", "A1", "verbo"),
    ("bring", "brɪŋ", "trazer", "A1", "verbo"),
    ("brought", "brɔːt", "trouxe", "A1", "verbo"),
    ("begin", "bɪgɪn", "começar", "A1", "verbo"),
    ("began", "bɪgæn", "começou", "A1", "verbo"),
    ("begun", "bɪgʌn", "começado", "A1", "verbo"),
    ("keep", "kiːp", "manter, guardar", "A1", "verbo"),
    ("kept", "kept", "manteve, guardou", "A1", "verbo"),
    ("hold", "hoʊld", "segurar", "A1", "verbo"),
    ("held", "held", "segurou", "A1", "verbo"),
    ("write", "raɪt", "escrever", "A1", "verbo"),
    ("wrote", "roʊt", "escreveu", "A1", "verbo"),
    ("written", "rɪtən", "escrito", "A1", "verbo"),
    ("stand", "stænd", "ficar de pé", "A1", "verbo"),
    ("stood", "stʊd", "ficou de pé", "A1", "verbo"),
    ("hear", "hɪər", "ouvir", "A1", "verbo"),
    ("heard", "hɜːrd", "ouviu", "A1", "verbo"),
    ("let", "let", "deixar, permitir", "A1", "verbo"),
    ("mean", "miːn", "significar", "A1", "verbo"),
    ("meant", "ment", "significou", "A1", "verbo"),
    ("set", "set", "definir, ajustar", "A2", "verbo"),
    ("meet", "miːt", "encontrar, conhecer", "A1", "verbo"),
    ("met", "met", "encontrou, conheceu", "A1", "verbo"),
    ("run", "rʌn", "correr", "A1", "verbo"),
    ("ran", "ræn", "correu", "A1", "verbo"),
    ("pay", "peɪ", "pagar", "A1", "verbo"),
    ("paid", "peɪd", "pagou", "A1", "verbo"),
    ("sit", "sɪt", "sentar", "A1", "verbo"),
    ("sat", "sæt", "sentou", "A1", "verbo"),
    ("speak", "spiːk", "falar", "A1", "verbo"),
    ("spoke", "spoʊk", "falou", "A1", "verbo"),
    ("spoken", "spoʊkən", "falado", "A1", "verbo"),
    ("lie", "laɪ", "deitar, mentir", "A1", "verbo"),
    ("lay", "leɪ", "deitou", "A1", "verbo"),
    ("lain", "leɪn", "deitado", "A1", "verbo"),
    ("lead", "liːd", "liderar, guiar", "A2", "verbo"),
    ("led", "led", "liderou, guiou", "A2", "verbo"),
    ("read", "riːd", "ler", "A1", "verbo"),
    ("grow", "groʊ", "crescer", "A1", "verbo"),
    ("grew", "gruː", "cresceu", "A1", "verbo"),
    ("grown", "groʊn", "crescido", "A1", "verbo"),
    ("open", "oʊpən", "abrir", "A1", "verbo"),
    ("opened", "oʊpənd", "abriu", "A1", "verbo"),
    ("close", "kloʊz", "fechar", "A1", "verbo"),
    ("closed", "kloʊzd", "fechou", "A1", "verbo"),
    ("walk", "wɔːk", "caminhar", "A1", "verbo"),
    ("walked", "wɔːkt", "caminhou", "A1", "verbo"),
    ("turn", "tɜːrn", "virar, girar", "A1", "verbo"),
    ("turned", "tɜːrnd", "virou, girou", "A1", "verbo"),
    ("start", "stɑːrt", "começar, iniciar", "A1", "verbo"),
    ("started", "stɑːrtɪd", "começou, iniciou", "A1", "verbo"),
    ("show", "ʃoʊ", "mostrar", "A1", "verbo"),
    ("showed", "ʃoʊd", "mostrou", "A1", "verbo"),
    ("play", "pleɪ", "jogar, tocar", "A1", "verbo"),
    ("played", "pleɪd", "jogou, tocou", "A1", "verbo"),
    ("move", "muːv", "mover, mudar", "A1", "verbo"),
    ("moved", "muːvd", "moveu, mudou", "A1", "verbo"),
    ("live", "lɪv", "viver, morar", "A1", "verbo"),
    ("lived", "lɪvd", "viveu, morou", "A1", "verbo"),
    ("believe", "bɪliːv", "acreditar", "A1", "verbo"),
    ("believed", "bɪliːvd", "acreditou", "A1", "verbo"),
    ("happen", "hæpən", "acontecer", "A1", "verbo"),
    ("happened", "hæpənd", "aconteceu", "A1", "verbo"),
    ("appear", "əpɪər", "aparecer", "A2", "verbo"),
    ("appeared", "əpɪərd", "apareceu", "A2", "verbo"),
    ("produce", "prədjuːs", "produzir", "A2", "verbo"),
    ("produced", "prədjuːst", "produziu", "A2", "verbo"),
    ("provide", "prəvaɪd", "fornecer, prover", "B1", "verbo"),
    ("provided", "prəvaɪdɪd", "forneceu, proveu", "B1", "verbo"),
    ("continue", "kəntɪnjuː", "continuar", "A2", "verbo"),
    ("continued", "kəntɪnjuːd", "continuou", "A2", "verbo"),
    ("follow", "fɒloʊ", "seguir", "A1", "verbo"),
    ("followed", "fɒloʊd", "seguiu", "A1", "verbo"),
    ("learn", "lɜːrn", "aprender", "A1", "verbo"),
    ("learned", "lɜːrnd", "aprendeu", "A1", "verbo"),
    ("change", "tʃeɪndʒ", "mudar, trocar", "A1", "verbo"),
    ("changed", "tʃeɪndʒd", "mudou, trocou", "A1", "verbo"),
    ("add", "æd", "adicionar", "A2", "verbo"),
    ("added", "ædɪd", "adicionou", "A2", "verbo"),

    # Advérbios
    ("here", "hɪər", "aqui", "A1", "advérbio"),
    ("there", "ðeər", "lá, ali", "A1", "advérbio"),
    ("now", "naʊ", "agora", "A1", "advérbio"),
    ("then", "ðen", "então", "A1", "advérbio"),
    ("when", "wen", "quando", "A1", "advérbio"),
    ("where", "weər", "onde", "A1", "advérbio"),
    ("why", "waɪ", "por que", "A1", "advérbio"),
    ("how", "haʊ", "como", "A1", "advérbio"),
    ("very", "veri", "muito", "A1", "advérbio"),
    ("too", "tuː", "também, demais", "A1", "advérbio"),
    ("so", "soʊ", "tão, então", "A1", "advérbio"),
    ("more", "mɔːr", "mais", "A1", "advérbio"),
    ("most", "moʊst", "mais (superlativo)", "A1", "advérbio"),
    ("much", "mʌtʃ", "muito", "A1", "advérbio"),
    ("many", "meni", "muitos", "A1", "advérbio"),
    ("well", "wel", "bem", "A1", "advérbio"),
    ("better", "betər", "melhor", "A1", "advérbio"),
    ("best", "best", "o melhor", "A1", "advérbio"),
    ("only", "oʊnli", "só, apenas", "A1", "advérbio"),
    ("also", "ɔːlsoʊ", "também", "A1", "advérbio"),
    ("just", "dʒʌst", "apenas, justo", "A1", "advérbio"),
    ("still", "stɪl", "ainda", "A1", "advérbio"),
    ("never", "nevər", "nunca", "A1", "advérbio"),
    ("always", "ɔːlweɪz", "sempre", "A1", "advérbio"),
    ("sometimes", "sʌmtaɪmz", "às vezes", "A1", "advérbio"),
    ("often", "ɒfən", "frequentemente", "A1", "advérbio"),
    ("usually", "juːʒuəli", "geralmente", "A1", "advérbio"),
    ("really", "riːəli", "realmente", "A1", "advérbio"),
    ("quite", "kwaɪt", "bastante", "A2", "advérbio"),
    ("perhaps", "pərhæps", "talvez", "A2", "advérbio"),
    ("maybe", "meɪbi", "talvez", "A1", "advérbio"),
    ("again", "əgen", "novamente", "A1", "advérbio"),
    ("together", "təgeðər", "juntos", "A1", "advérbio"),
    ("away", "əweɪ", "longe, fora", "A1", "advérbio"),
    ("back", "bæk", "de volta", "A1", "advérbio"),
    ("yet", "jet", "ainda, já", "A1", "advérbio"),
    ("already", "ɔːlredi", "já", "A1", "advérbio"),
    ("enough", "ɪnʌf", "suficiente", "A1", "advérbio"),
    ("almost", "ɔːlmoʊst", "quase", "A2", "advérbio"),
    ("later", "leɪtər", "mais tarde", "A1", "advérbio"),
    ("soon", "suːn", "em breve", "A1", "advérbio"),
    ("today", "tədeɪ", "hoje", "A1", "advérbio"),
    ("tonight", "tənaɪt", "hoje à noite", "A1", "advérbio"),

    # Preposições
    ("in", "ɪn", "em, dentro", "A1", "preposição"),
    ("on", "ɒn", "em, sobre", "A1", "preposição"),
    ("at", "æt", "em, a", "A1", "preposição"),
    ("to", "tuː", "para, a", "A1", "preposição"),
    ("for", "fɔːr", "para, por", "A1", "preposição"),
    ("of", "əv", "de", "A1", "preposição"),
    ("with", "wɪð", "com", "A1", "preposição"),
    ("from", "frɒm", "de, desde", "A1", "preposição"),
    ("by", "baɪ", "por, de", "A1", "preposição"),
    ("about", "əbaʊt", "sobre", "A1", "preposição"),
    ("as", "æz", "como", "A1", "preposição"),
    ("into", "ɪntuː", "em, dentro de", "A1", "preposição"),
    ("through", "θruː", "através", "A1", "preposição"),
    ("during", "djʊərɪŋ", "durante", "A2", "preposição"),
    ("before", "bɪfɔːr", "antes", "A1", "preposição"),
    ("after", "æftər", "depois", "A1", "preposição"),
    ("above", "əbʌv", "acima", "A1", "preposição"),
    ("below", "bɪloʊ", "abaixo", "A2", "preposição"),
    ("between", "bɪtwiːn", "entre", "A1", "preposição"),
    ("under", "ʌndər", "sob, embaixo", "A1", "preposição"),
    ("over", "oʊvər", "sobre, acima", "A1", "preposição"),
    ("up", "ʌp", "para cima", "A1", "preposição"),
    ("down", "daʊn", "para baixo", "A1", "preposição"),
    ("out", "aʊt", "fora", "A1", "preposição"),
    ("off", "ɒf", "fora, desligado", "A1", "preposição"),
    ("around", "əraʊnd", "ao redor", "A1", "preposição"),
    ("near", "nɪər", "perto", "A1", "preposição"),
    ("behind", "bɪhaɪnd", "atrás", "A1", "preposição"),
    ("across", "əkrɒs", "através", "A2", "preposição"),
    ("against", "əgenst", "contra", "A2", "preposição"),
    ("among", "əmʌŋ", "entre", "A2", "preposição"),
    ("within", "wɪðɪn", "dentro de", "B1", "preposição"),
    ("without", "wɪðaʊt", "sem", "A1", "preposição"),
    ("towards", "tɔːrdz", "em direção a", "A2", "preposição"),

    # Conjunções
    ("and", "ænd", "e", "A1", "conjunção"),
    ("but", "bʌt", "mas", "A1", "conjunção"),
    ("or", "ɔːr", "ou", "A1", "conjunção"),
    ("if", "ɪf", "se", "A1", "conjunção"),
    ("because", "bɪkɒz", "porque", "A1", "conjunção"),
    ("when", "wen", "quando", "A1", "conjunção"),
    ("while", "waɪl", "enquanto", "A2", "conjunção"),
    ("although", "ɔːlðoʊ", "embora", "B1", "conjunção"),
    ("however", "haʊevər", "no entanto", "A2", "conjunção"),
    ("therefore", "ðeərfɔːr", "portanto", "B1", "conjunção"),
    ("unless", "ənles", "a menos que", "B1", "conjunção"),
    ("until", "əntɪl", "até", "A1", "conjunção"),
    ("since", "sɪns", "desde", "A1", "conjunção"),

    # Artigos e determinantes
    ("the", "ðə", "o, a, os, as", "A1", "artigo"),
    ("a", "eɪ", "um, uma", "A1", "artigo"),
    ("an", "æn", "um, uma", "A1", "artigo"),
    ("some", "sʌm", "algum, alguns", "A1", "determinante"),
    ("any", "eni", "qualquer, algum", "A1", "determinante"),
    ("all", "ɔːl", "todo, todos", "A1", "determinante"),
    ("each", "iːtʃ", "cada", "A1", "determinante"),
    ("every", "evri", "cada, todo", "A1", "determinante"),
    ("other", "ʌðər", "outro", "A1", "determinante"),
    ("another", "ənʌðər", "outro", "A1", "determinante"),
    ("such", "sʌtʃ", "tal", "A2", "determinante"),
    ("both", "boʊθ", "ambos", "A2", "determinante"),
    ("few", "fjuː", "poucos", "A1", "determinante"),
    ("little", "lɪtəl", "pouco", "A1", "determinante"),
    ("less", "les", "menos", "A1", "determinante"),
    ("several", "sevrəl", "vários", "A2", "determinante"),
]

db = SessionLocal()

try:
    print("=" * 60)
    print("  ADICIONANDO PALAVRAS FALTANTES")
    print("=" * 60)

    # Contar palavras existentes
    current_count = db.query(func.count(Word.id)).scalar()
    print(f"\nPalavras atuais no banco: {current_count}")
    print(f"Palavras a adicionar: {len(new_words)}")
    print(f"Total após importação: {current_count + len(new_words)}")

    added = 0
    skipped = 0

    for english, ipa, portuguese, level, tags in new_words:
        # Verificar se já existe
        existing = db.query(Word).filter(func.lower(Word.english) == english.lower()).first()
        if existing:
            skipped += 1
            continue

        # Criar palavra
        word = Word(
            english=english.lower(),
            ipa=ipa,
            portuguese=portuguese,
            level=level,
            tags=tags
        )
        db.add(word)
        added += 1

        # Commit a cada 50 palavras
        if added % 50 == 0:
            db.commit()
            print(f"  Adicionadas {added} palavras...")

    db.commit()

    # Contagem final
    final_count = db.query(func.count(Word.id)).scalar()

    print("\n" + "=" * 60)
    print("  IMPORTACAO CONCLUIDA")
    print("=" * 60)
    print(f"Palavras adicionadas: {added}")
    print(f"Palavras ignoradas (já existentes): {skipped}")
    print(f"Total de palavras no banco: {final_count}")
    print("=" * 60)

except Exception as e:
    db.rollback()
    print(f"\nERRO: {e}")
    raise
finally:
    db.close()
