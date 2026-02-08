"""
Script para enriquecer palavras com informações detalhadas.
Adiciona definições, exemplos, sinônimos, e contexto de uso.
"""

import json
import os
from sqlalchemy.orm import Session
from app.core.database import SessionLocal, engine
from app.models.word import Word


# Dados enriquecidos de exemplo para palavras comuns
ENRICHED_DATA = {
    # Verbos básicos
    "be": {
        "word_type": "verb",
        "definition_en": "to exist, to have a specified quality or nature",
        "definition_pt": "existir, ter uma qualidade ou natureza especificada",
        "synonyms": "exist, remain, live",
        "example_sentences": json.dumps([
            {"en": "I am a student.", "pt": "Eu sou um estudante."},
            {"en": "She is happy today.", "pt": "Ela está feliz hoje."},
            {"en": "They are from Brazil.", "pt": "Eles são do Brasil."}
        ]),
        "usage_notes": "O verbo 'be' é irregular e fundamental. Use 'am/is/are' no presente, 'was/were' no passado. É usado para estados, identificação e características.",
        "collocations": json.dumps(["be careful", "be ready", "be sure", "be able to"])
    },
    "have": {
        "word_type": "verb",
        "definition_en": "to possess, own, or hold",
        "definition_pt": "possuir, ter ou segurar",
        "synonyms": "possess, own, hold",
        "example_sentences": json.dumps([
            {"en": "I have a car.", "pt": "Eu tenho um carro."},
            {"en": "She has two brothers.", "pt": "Ela tem dois irmãos."},
            {"en": "We have dinner at 7 PM.", "pt": "Nós jantamos às 19h."}
        ]),
        "usage_notes": "Usado para posse, características e ações (have breakfast, have fun). No presente: have/has, passado: had.",
        "collocations": json.dumps(["have fun", "have a good time", "have breakfast", "have a look"])
    },
    "do": {
        "word_type": "verb",
        "definition_en": "to perform, execute, or carry out an action",
        "definition_pt": "realizar, executar ou levar a cabo uma ação",
        "synonyms": "perform, execute, accomplish",
        "example_sentences": json.dumps([
            {"en": "I do my homework every day.", "pt": "Eu faço minha lição de casa todos os dias."},
            {"en": "What do you do?", "pt": "O que você faz?"},
            {"en": "She does yoga in the morning.", "pt": "Ela faz yoga de manhã."}
        ]),
        "usage_notes": "Verbo auxiliar em perguntas e negativas. Também significa 'fazer'. Presente: do/does, passado: did.",
        "collocations": json.dumps(["do homework", "do business", "do your best", "do the dishes"])
    },

    # Substantivos comuns
    "time": {
        "word_type": "noun",
        "definition_en": "the indefinite continued progress of existence and events",
        "definition_pt": "o progresso contínuo indefinido da existência e eventos",
        "synonyms": "moment, period, era, duration",
        "antonyms": "eternity, timelessness",
        "example_sentences": json.dumps([
            {"en": "What time is it?", "pt": "Que horas são?"},
            {"en": "I don't have time now.", "pt": "Não tenho tempo agora."},
            {"en": "Time flies when you're having fun.", "pt": "O tempo voa quando você está se divertindo."}
        ]),
        "usage_notes": "Pode ser contável (times = vezes) ou incontável (time = tempo). Muito usado em expressões idiomáticas.",
        "collocations": json.dumps(["save time", "waste time", "on time", "in time", "have a good time"])
    },
    "person": {
        "word_type": "noun",
        "definition_en": "a human being regarded as an individual",
        "definition_pt": "um ser humano considerado como indivíduo",
        "synonyms": "individual, human, being",
        "example_sentences": json.dumps([
            {"en": "She is a kind person.", "pt": "Ela é uma pessoa gentil."},
            {"en": "Every person is unique.", "pt": "Cada pessoa é única."},
            {"en": "Three persons are waiting outside.", "pt": "Três pessoas estão esperando lá fora."}
        ]),
        "usage_notes": "Plural: 'people' (informal) ou 'persons' (formal/legal). 'People' é mais comum no dia a dia.",
        "collocations": json.dumps(["nice person", "important person", "in person"])
    },

    # Adjetivos
    "good": {
        "word_type": "adjective",
        "definition_en": "to be desired or approved of; having the right qualities",
        "definition_pt": "desejável ou aprovado; tendo as qualidades certas",
        "synonyms": "excellent, great, fine, wonderful",
        "antonyms": "bad, poor, terrible, awful",
        "example_sentences": json.dumps([
            {"en": "This is a good book.", "pt": "Este é um bom livro."},
            {"en": "She is good at math.", "pt": "Ela é boa em matemática."},
            {"en": "Have a good day!", "pt": "Tenha um bom dia!"}
        ]),
        "usage_notes": "Comparativo: better, superlativo: best. Muito usado em expressões e saudações.",
        "collocations": json.dumps(["good morning", "good luck", "good idea", "feel good", "be good at"])
    },
    "new": {
        "word_type": "adjective",
        "definition_en": "not existing before; made, introduced, or discovered recently",
        "definition_pt": "que não existia antes; feito, introduzido ou descoberto recentemente",
        "synonyms": "fresh, recent, modern, novel",
        "antonyms": "old, ancient, used, worn",
        "example_sentences": json.dumps([
            {"en": "I bought a new car.", "pt": "Comprei um carro novo."},
            {"en": "What's new?", "pt": "O que há de novo?"},
            {"en": "She has a new job.", "pt": "Ela tem um novo emprego."}
        ]),
        "usage_notes": "Oposto de 'old'. Comparativo: newer, superlativo: newest.",
        "collocations": json.dumps(["brand new", "new year", "new idea", "something new"])
    },
    "happy": {
        "word_type": "adjective",
        "definition_en": "feeling or showing pleasure or contentment",
        "definition_pt": "sentindo ou mostrando prazer ou contentamento",
        "synonyms": "joyful, cheerful, delighted, pleased",
        "antonyms": "sad, unhappy, miserable, depressed",
        "example_sentences": json.dumps([
            {"en": "I'm happy to see you.", "pt": "Estou feliz em te ver."},
            {"en": "She looks happy today.", "pt": "Ela parece feliz hoje."},
            {"en": "Happy birthday!", "pt": "Feliz aniversário!"}
        ]),
        "usage_notes": "Comparativo: happier, superlativo: happiest. Muda 'y' para 'i' antes de adicionar -er/-est.",
        "collocations": json.dumps(["happy birthday", "happy ending", "happy hour", "make someone happy"])
    },

    # Advérbios
    "very": {
        "word_type": "adverb",
        "definition_en": "used to emphasize an adjective or adverb",
        "definition_pt": "usado para enfatizar um adjetivo ou advérbio",
        "synonyms": "extremely, really, quite, highly",
        "example_sentences": json.dumps([
            {"en": "It's very hot today.", "pt": "Está muito quente hoje."},
            {"en": "She is very intelligent.", "pt": "Ela é muito inteligente."},
            {"en": "Thank you very much.", "pt": "Muito obrigado."}
        ]),
        "usage_notes": "Intensificador comum. Não use com adjetivos comparativos (errado: very better).",
        "collocations": json.dumps(["very much", "very well", "very good", "very important"])
    },
    "well": {
        "word_type": "adverb",
        "definition_en": "in a good or satisfactory way",
        "definition_pt": "de maneira boa ou satisfatória",
        "synonyms": "properly, correctly, satisfactorily",
        "antonyms": "badly, poorly",
        "example_sentences": json.dumps([
            {"en": "She speaks English well.", "pt": "Ela fala inglês bem."},
            {"en": "I slept well last night.", "pt": "Dormi bem ontem à noite."},
            {"en": "Well done!", "pt": "Muito bem!"}
        ]),
        "usage_notes": "Advérbio de 'good'. Também usado como interjeição no início de frases.",
        "collocations": json.dumps(["very well", "well done", "as well", "well known"])
    },

    # Preposições e palavras de função
    "in": {
        "word_type": "preposition",
        "definition_en": "expressing the situation of being enclosed or surrounded",
        "definition_pt": "expressando a situação de estar cercado ou contido",
        "example_sentences": json.dumps([
            {"en": "I live in Brazil.", "pt": "Eu moro no Brasil."},
            {"en": "She's in the kitchen.", "pt": "Ela está na cozinha."},
            {"en": "I'll see you in an hour.", "pt": "Te vejo em uma hora."}
        ]),
        "usage_notes": "Usado para: locais (países, cidades), tempo futuro (in 2 hours), meses/anos (in January, in 2024).",
        "collocations": json.dumps(["in time", "in love", "in fact", "in general", "believe in"])
    },
    "on": {
        "word_type": "preposition",
        "definition_en": "physically in contact with and supported by a surface",
        "definition_pt": "fisicamente em contato e suportado por uma superfície",
        "example_sentences": json.dumps([
            {"en": "The book is on the table.", "pt": "O livro está na mesa."},
            {"en": "I'll call you on Monday.", "pt": "Vou te ligar na segunda-feira."},
            {"en": "Turn on the TV.", "pt": "Ligue a TV."}
        ]),
        "usage_notes": "Usado para: superfícies, dias da semana, datas, transporte público.",
        "collocations": json.dumps(["on time", "on purpose", "on sale", "focus on", "depend on"])
    },
    "at": {
        "word_type": "preposition",
        "definition_en": "expressing location or arrival in a particular place",
        "definition_pt": "expressando localização ou chegada em um lugar específico",
        "example_sentences": json.dumps([
            {"en": "I'm at home.", "pt": "Estou em casa."},
            {"en": "The meeting is at 3 PM.", "pt": "A reunião é às 15h."},
            {"en": "She's good at English.", "pt": "Ela é boa em inglês."}
        ]),
        "usage_notes": "Usado para: pontos específicos (at home, at the door), horas (at 5 o'clock), habilidades (good at).",
        "collocations": json.dumps(["at least", "at last", "at home", "good at", "look at"])
    }
}


def detect_word_type(word: str) -> str:
    """Detecta o tipo da palavra baseado em padrões morfológicos."""
    word_lower = word.lower()

    # Verbos
    if word_lower.endswith(('ing', 'ed', 'ate', 'ize', 'ify', 'en')):
        return "verb"

    # Advérbios
    if word_lower.endswith('ly'):
        return "adverb"

    # Substantivos
    if word_lower.endswith(('tion', 'sion', 'ness', 'ment', 'ity', 'er', 'or', 'ism', 'ist', 'ance', 'ence')):
        return "noun"

    # Adjetivos
    if word_lower.endswith(('ful', 'less', 'ous', 'ious', 'ive', 'able', 'ible', 'al', 'ic', 'ical')):
        return "adjective"

    return "other"


def generate_basic_examples(word_obj: Word) -> list:
    """Gera exemplos básicos baseados no tipo de palavra."""
    word_type = word_obj.word_type or detect_word_type(word_obj.english)
    english = word_obj.english
    portuguese = word_obj.portuguese

    examples = []

    if word_type == "verb":
        examples = [
            {"en": f"I {english} every day.", "pt": f"Eu {portuguese} todos os dias."},
            {"en": f"She {english}s on weekends.", "pt": f"Ela {portuguese} aos fins de semana."},
            {"en": f"We should {english} more often.", "pt": f"Devemos {portuguese} com mais frequência."}
        ]
    elif word_type == "noun":
        examples = [
            {"en": f"The {english} is very important.", "pt": f"O/A {portuguese} é muito importante."},
            {"en": f"I need a {english}.", "pt": f"Preciso de um/uma {portuguese}."},
            {"en": f"This {english} looks great!", "pt": f"Este/Esta {portuguese} parece ótimo/ótima!"}
        ]
    elif word_type == "adjective":
        examples = [
            {"en": f"She is very {english}.", "pt": f"Ela é muito {portuguese}."},
            {"en": f"The weather is {english} today.", "pt": f"O tempo está {portuguese} hoje."},
            {"en": f"It looks {english}.", "pt": f"Parece {portuguese}."}
        ]
    elif word_type == "adverb":
        examples = [
            {"en": f"He speaks {english}.", "pt": f"Ele fala {portuguese}."},
            {"en": f"She smiled {english}.", "pt": f"Ela sorriu {portuguese}."},
            {"en": f"They work {english}.", "pt": f"Eles trabalham {portuguese}."}
        ]
    else:
        examples = [
            {"en": f"This is {english}.", "pt": f"Isto é {portuguese}."},
            {"en": f"Look {english} that.", "pt": f"Olhe {portuguese} aquilo."}
        ]

    return examples


def enrich_word(word: Word) -> bool:
    """Enriquece uma palavra com informações detalhadas."""
    english_lower = word.english.lower()

    # Se temos dados pré-definidos, use-os
    if english_lower in ENRICHED_DATA:
        data = ENRICHED_DATA[english_lower]
        word.word_type = data.get("word_type")
        word.definition_en = data.get("definition_en")
        word.definition_pt = data.get("definition_pt")
        word.synonyms = data.get("synonyms")
        word.antonyms = data.get("antonyms")
        word.example_sentences = data.get("example_sentences")
        word.usage_notes = data.get("usage_notes")
        word.collocations = data.get("collocations")
        return True

    # Caso contrário, gere informações básicas
    if not word.word_type:
        word.word_type = detect_word_type(word.english)

    # Gere exemplos se não existirem
    if not word.example_sentences:
        examples = generate_basic_examples(word)
        word.example_sentences = json.dumps(examples)

    return False


def main():
    """Função principal para enriquecer todas as palavras."""
    db = SessionLocal()

    try:
        print("🚀 Iniciando enriquecimento de palavras...")

        # Buscar todas as palavras
        words = db.query(Word).all()
        total = len(words)
        enriched_count = 0
        generated_count = 0

        print(f"📊 Total de palavras: {total}")

        for i, word in enumerate(words, 1):
            was_enriched = enrich_word(word)

            if was_enriched:
                enriched_count += 1
            else:
                generated_count += 1

            if i % 100 == 0:
                print(f"⏳ Processadas: {i}/{total}")
                db.commit()

        db.commit()

        print("\n✅ Enriquecimento concluído!")
        print(f"📚 Palavras com dados completos: {enriched_count}")
        print(f"🤖 Palavras com dados gerados: {generated_count}")
        print(f"📊 Total processado: {total}")

    except Exception as e:
        print(f"❌ Erro: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()
