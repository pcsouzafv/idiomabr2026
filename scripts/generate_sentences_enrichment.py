import csv
import itertools
import random
import re
from pathlib import Path
from typing import Dict, List, Tuple

random.seed(42)

Slot = Tuple[str, str]

SLOTS: Dict[str, List[Slot]] = {
    "name": [("Mike", "Mike"), ("Anna", "Anna"), ("Luis", "Luís"), ("Sarah", "Sarah"), ("Tom", "Tom"), ("Julia", "Julia"), ("Kevin", "Kevin"), ("Emily", "Emily")],
    "day": [("Monday", "segunda-feira"), ("Tuesday", "terça-feira"), ("Wednesday", "quarta-feira"), ("Thursday", "quinta-feira"), ("Friday", "sexta-feira"), ("Saturday", "sábado"), ("Sunday", "domingo")],
    "time": [("6:00 a.m.", "6:00"), ("7:00 a.m.", "7:00"), ("8:00 a.m.", "8:00"), ("9:00 a.m.", "9:00"), ("10:00 a.m.", "10:00"), ("noon", "meio-dia"), ("1:00 p.m.", "13:00"), ("3:00 p.m.", "15:00"), ("5:00 p.m.", "17:00"), ("7:00 p.m.", "19:00"), ("8:00 p.m.", "20:00")],
    "frequency": [("every day", "todos os dias"), ("on weekdays", "nos dias úteis"), ("on weekends", "nos fins de semana"), ("twice a week", "duas vezes por semana"), ("three times a week", "três vezes por semana"), ("once a month", "uma vez por mês"), ("every other day", "dia sim, dia não")],
    "meal": [("breakfast", "café da manhã"), ("lunch", "almoço"), ("dinner", "jantar"), ("a late snack", "um lanche tarde")],
    "drink": [("coffee", "café"), ("tea", "chá"), ("water", "água"), ("orange juice", "suco de laranja"), ("soda", "refrigerante")],
    "food": [("pizza", "pizza"), ("sandwich", "sanduíche"), ("salad", "salada"), ("tacos", "tacos"), ("pasta", "macarrão"), ("soup", "sopa"), ("rice and beans", "arroz e feijão"), ("grilled chicken", "frango grelhado"), ("burgers", "hambúrgueres"), ("sushi", "sushi")],
    "place": [("the supermarket", "o supermercado"), ("the gym", "a academia"), ("the bank", "o banco"), ("the pharmacy", "a farmácia"), ("the mall", "o shopping"), ("the park", "o parque"), ("the office", "o escritório"), ("downtown", "o centro"), ("the library", "a biblioteca"), ("the post office", "os correios")],
    "transport": [("bus", "ônibus"), ("subway", "metrô"), ("car", "carro"), ("bike", "bicicleta"), ("ride-share", "carro por aplicativo"), ("train", "trem"), ("walk", "a pé")],
    "chore": [("do the laundry", "lavar roupa"), ("wash the dishes", "lavar a louça"), ("clean the kitchen", "limpar a cozinha"), ("take out the trash", "tirar o lixo"), ("mop the floor", "passar pano no chão")],
    "store": [("grocery store", "mercado"), ("gas station", "posto de gasolina"), ("drugstore", "farmácia"), ("bakery", "padaria"), ("coffee shop", "cafeteria"), ("hardware store", "loja de ferragens"), ("bookstore", "livraria"), ("clothing store", "loja de roupas")],
    "activity": [("watch a movie", "assistir a um filme"), ("go for a walk", "fazer uma caminhada"), ("study English", "estudar inglês"), ("cook at home", "cozinhar em casa"), ("work out", "treinar"), ("meet friends", "encontrar amigos"), ("go grocery shopping", "fazer compras"), ("pay bills", "pagar contas"), ("read a book", "ler um livro"), ("visit family", "visitar a família")],
    "weather": [("sunny", "ensolarado"), ("rainy", "chuvoso"), ("cold", "frio"), ("hot", "quente"), ("windy", "ventoso"), ("cloudy", "nublado")],
    "reason": [("because it is cheaper", "porque é mais barato"), ("because it saves time", "porque economiza tempo"), ("because it is healthier", "porque é mais saudável"), ("because it is convenient", "porque é prático")],
    "problem": [("my phone battery is low", "a bateria do meu celular está baixa"), ("the internet is down", "a internet caiu"), ("the traffic is heavy", "o trânsito está pesado"), ("my card was declined", "meu cartão foi recusado")],
    "appointment": [("a dentist appointment", "uma consulta no dentista"), ("a doctor appointment", "uma consulta médica"), ("a haircut", "um corte de cabelo"), ("a meeting", "uma reunião")],
    "payment": [("cash", "dinheiro"), ("credit card", "cartão de crédito"), ("debit card", "cartão de débito"), ("mobile payment", "pagamento por celular")],
    "device": [("phone", "celular"), ("laptop", "notebook"), ("tablet", "tablet")],
    "item": [("bread", "pão"), ("milk", "leite"), ("eggs", "ovos"), ("toothpaste", "pasta de dente"), ("shampoo", "shampoo"), ("batteries", "pilhas"), ("tickets", "ingressos"), ("medicine", "remédio"), ("soap", "sabão"), ("paper towels", "papel toalha")],
    "direction": [("left", "esquerda"), ("right", "direita"), ("straight", "em frente")],
    "daypart": [("this morning", "hoje de manhã"), ("this afternoon", "hoje à tarde"), ("tonight", "hoje à noite")],
    "backup_plan": [("take a taxi", "pegar um táxi"), ("call a ride", "chamar um carro"), ("walk home", "ir a pé para casa")],
    "city": [("New York", "Nova York"), ("Los Angeles", "Los Angeles"), ("Chicago", "Chicago"), ("Miami", "Miami"), ("Seattle", "Seattle"), ("Boston", "Boston"), ("Dallas", "Dallas")],
    "duration": [("for 30 minutes", "por 30 minutos"), ("for an hour", "por uma hora"), ("for two hours", "por duas horas")],
    "quantity": [("a few", "alguns"), ("some", "alguns"), ("a couple of", "um casal de")],
    "price": [("$5", "$5"), ("$10", "$10"), ("$20", "$20")],
    "family": [("my brother", "meu irmão"), ("my sister", "minha irmã"), ("my parents", "meus pais"), ("my friend", "meu amigo")],
    "event": [("game", "jogo"), ("concert", "show"), ("birthday party", "festa de aniversário")],
    "holiday": [("Thanksgiving", "Dia de Ação de Graças"), ("Christmas", "Natal"), ("New Year's Eve", "Ano Novo")],
    "task": [("send an email", "enviar um e-mail"), ("finish the report", "terminar o relatório"), ("call the bank", "ligar para o banco")],
    "issue": [("the billing issue", "o problema de cobrança"), ("the delivery delay", "o atraso na entrega"), ("the scheduling conflict", "o conflito de agenda")],
    "project": [("the marketing project", "o projeto de marketing"), ("the app update", "a atualização do app"), ("the onboarding plan", "o plano de integração")],
    "adjective": [("busy", "movimentado"), ("quiet", "tranquilo"), ("cheap", "barato"), ("expensive", "caro"), ("clean", "limpo"), ("crowded", "cheio")],
    "quality": [("great", "ótima"), ("poor", "ruim"), ("average", "mediana")],
}

TEMPLATES = [
    # A1
    {"level": "A1", "category": "daily_routine", "grammar_points": ["present simple", "time expressions"], "en": "What time do you wake up on {day}?", "pt": "Que horas você acorda na {day}?"},
    {"level": "A1", "category": "daily_routine", "grammar_points": ["present simple"], "en": "I wake up at {time}.", "pt": "Eu acordo às {time}."},
    {"level": "A1", "category": "daily_routine", "grammar_points": ["present simple"], "en": "I eat {meal} at {time}.", "pt": "Eu faço {meal} às {time}."},
    {"level": "A1", "category": "food", "grammar_points": ["present simple"], "en": "I drink {drink} in the morning.", "pt": "Eu bebo {drink} de manhã."},
    {"level": "A1", "category": "transport", "grammar_points": ["present simple", "by + transport"], "en": "I go to work by {transport}.", "pt": "Eu vou para o trabalho de {transport}."},
    {"level": "A1", "category": "leisure", "grammar_points": ["like + to-infinitive"], "en": "I like to {activity}.", "pt": "Eu gosto de {activity}."},
    {"level": "A1", "category": "weather", "grammar_points": ["verb to be"], "en": "It is {weather} today.", "pt": "Hoje está {weather}."},
    {"level": "A1", "category": "conversation", "grammar_points": ["present simple questions"], "en": "Where do you live?", "pt": "Onde você mora?"},
    {"level": "A1", "category": "conversation", "grammar_points": ["present simple questions"], "en": "Do you like {food}?", "pt": "Você gosta de {food}?"},
    {"level": "A1", "category": "shopping", "grammar_points": ["present simple"], "en": "I buy {item} at the {store}.", "pt": "Eu compro {item} na {store}."},
    {"level": "A1", "category": "daily_routine", "grammar_points": ["present simple", "frequency adverbs"], "en": "I {activity} {frequency}.", "pt": "Eu {activity} {frequency}."},
    {"level": "A1", "category": "transport", "grammar_points": ["present simple"], "en": "I go to {place} on {day}.", "pt": "Eu vou ao {place} na {day}."},
    {"level": "A1", "category": "home", "grammar_points": ["present simple"], "en": "I {chore} after {meal}.", "pt": "Eu {chore} depois do {meal}."},
    {"level": "A1", "category": "conversation", "grammar_points": ["present simple questions"], "en": "Do you go to {place} by {transport}?", "pt": "Você vai ao {place} de {transport}?"},
    {"level": "A1", "category": "shopping", "grammar_points": ["present simple"], "en": "I pay with {payment} at the {store}.", "pt": "Eu pago com {payment} na {store}."},
    {"level": "A1", "category": "daily_routine", "grammar_points": ["present simple"], "en": "I drink {drink} {daypart}.", "pt": "Eu bebo {drink} {daypart}."},
    {"level": "A1", "category": "personal_info", "grammar_points": ["verb to be"], "en": "I live in {city}.", "pt": "Eu moro em {city}."},
    {"level": "A1", "category": "food", "grammar_points": ["present simple"], "en": "I want a {drink} and a {food}.", "pt": "Eu quero um {drink} e {food}."},
    {"level": "A1", "category": "leisure", "grammar_points": ["present simple"], "en": "I go to the {place} with {family}.", "pt": "Eu vou ao {place} com {family}."},
    {"level": "A1", "category": "conversation", "grammar_points": ["present simple questions"], "en": "Is the {store} open today?", "pt": "A {store} está aberta hoje?"},
    {"level": "A1", "category": "shopping", "grammar_points": ["present simple"], "en": "I go to the {store} at {time} on {day}.", "pt": "Eu vou à {store} às {time} na {day}."},
    {"level": "A1", "category": "shopping", "grammar_points": ["verb to be"], "en": "The {store} is {adjective} {daypart}.", "pt": "A {store} está {adjective} {daypart}."},
    {"level": "A1", "category": "daily_routine", "grammar_points": ["present simple"], "en": "I need {item} for {meal}.", "pt": "Eu preciso de {item} para o {meal}."},
    {"level": "A1", "category": "weather", "grammar_points": ["verb to be"], "en": "Is it {weather} {daypart}?", "pt": "Está {weather} {daypart}?"},
    # A2
    {"level": "A2", "category": "shopping", "grammar_points": ["present continuous"], "en": "I am shopping at {place}.", "pt": "Eu estou comprando no {place}."},
    {"level": "A2", "category": "home", "grammar_points": ["have to"], "en": "I have to {chore} today.", "pt": "Eu tenho que {chore} hoje."},
    {"level": "A2", "category": "food", "grammar_points": ["present continuous"], "en": "I am cooking {food} right now.", "pt": "Eu estou cozinhando {food} agora."},
    {"level": "A2", "category": "conversation", "grammar_points": ["polite requests"], "en": "Could you help me with the bags?", "pt": "Você poderia me ajudar com as sacolas?"},
    {"level": "A2", "category": "plans", "grammar_points": ["going to"], "en": "I am going to {activity} after work.", "pt": "Eu vou {activity} depois do trabalho."},
    {"level": "A2", "category": "shopping", "grammar_points": ["need to"], "en": "I need to buy {food} at the {store}.", "pt": "Eu preciso comprar {food} na {store}."},
    {"level": "A2", "category": "transport", "grammar_points": ["present simple"], "en": "I usually take the {transport} to {place}.", "pt": "Eu normalmente pego o {transport} para {place}."},
    {"level": "A2", "category": "home", "grammar_points": ["imperatives"], "en": "Please turn off the lights.", "pt": "Por favor, apague as luzes."},
    {"level": "A2", "category": "shopping", "grammar_points": ["polite requests"], "en": "Can I have the receipt, please?", "pt": "Posso ficar com o recibo, por favor?"},
    {"level": "A2", "category": "technology", "grammar_points": ["need to"], "en": "I need to charge my {device}.", "pt": "Eu preciso carregar meu {device}."},
    {"level": "A2", "category": "shopping", "grammar_points": ["countable/uncountable"], "en": "I need some {item} and {food}.", "pt": "Eu preciso de {item} e {food}."},
    {"level": "A2", "category": "transport", "grammar_points": ["directions"], "en": "Turn {direction} at the {place}.", "pt": "Vire à {direction} no {place}."},
    {"level": "A2", "category": "conversation", "grammar_points": ["present continuous"], "en": "I am waiting for {name} at {place}.", "pt": "Eu estou esperando {name} no {place}."},
    {"level": "A2", "category": "work", "grammar_points": ["present simple"], "en": "I have {appointment} on {day}.", "pt": "Eu tenho {appointment} na {day}."},
    {"level": "A2", "category": "shopping", "grammar_points": ["present simple"], "en": "The {store} is closed on {day}.", "pt": "A {store} fecha na {day}."},
    {"level": "A2", "category": "home", "grammar_points": ["present continuous"], "en": "I am {chore} right now.", "pt": "Eu estou {chore} agora."},
    {"level": "A2", "category": "plans", "grammar_points": ["going to"], "en": "I am going to {place} to {activity}.", "pt": "Eu vou ao {place} para {activity}."},
    {"level": "A2", "category": "conversation", "grammar_points": ["present simple questions"], "en": "How much is this {item}?", "pt": "Quanto custa este {item}?"},
    {"level": "A2", "category": "shopping", "grammar_points": ["present simple"], "en": "I picked up {item} at the {store}.", "pt": "Eu peguei {item} na {store}."},
    {"level": "A2", "category": "leisure", "grammar_points": ["present continuous"], "en": "We are going to a {event} {daypart}.", "pt": "Nós vamos a um {event} {daypart}."},
    {"level": "A2", "category": "travel", "grammar_points": ["future plans"], "en": "We are visiting {city} on {day}.", "pt": "Nós vamos visitar {city} na {day}."},
    {"level": "A2", "category": "plans", "grammar_points": ["going to"], "en": "I am going to {place} at {time} to {activity}.", "pt": "Eu vou ao {place} às {time} para {activity}."},
    {"level": "A2", "category": "shopping", "grammar_points": ["present continuous"], "en": "I am paying {price} for {item}.", "pt": "Eu estou pagando {price} por {item}."},
    {"level": "A2", "category": "daily_routine", "grammar_points": ["present simple"], "en": "I meet {family} at {place} on {day}.", "pt": "Eu encontro {family} no {place} na {day}."},
    # B1
    {"level": "B1", "category": "health", "grammar_points": ["present perfect continuous"], "en": "I have been feeling tired lately.", "pt": "Eu tenho me sentido cansado ultimamente."},
    {"level": "B1", "category": "shopping", "grammar_points": ["present perfect", "already"], "en": "I have already paid the bill at the {store}.", "pt": "Eu já paguei a conta na {store}."},
    {"level": "B1", "category": "transport", "grammar_points": ["first conditional"], "en": "If it rains, I will take the {transport}.", "pt": "Se chover, eu vou de {transport}."},
    {"level": "B1", "category": "technology", "grammar_points": ["linking words"], "en": "{problem}, so I will call support.", "pt": "{problem}, então vou ligar para o suporte."},
    {"level": "B1", "category": "work", "grammar_points": ["comparatives"], "en": "The traffic is heavier during rush hour.", "pt": "O trânsito é mais pesado no horário de pico."},
    {"level": "B1", "category": "plans", "grammar_points": ["future with will"], "en": "I will call you when I get home.", "pt": "Eu vou te ligar quando chegar em casa."},
    {"level": "B1", "category": "health", "grammar_points": ["need to"], "en": "I need to schedule {appointment}.", "pt": "Eu preciso marcar {appointment}."},
    {"level": "B1", "category": "shopping", "grammar_points": ["adverbs of frequency"], "en": "I shop online {frequency}.", "pt": "Eu compro online {frequency}."},
    {"level": "B1", "category": "home", "grammar_points": ["present perfect"], "en": "I have just finished {chore}.", "pt": "Eu acabei de {chore}."},
    {"level": "B1", "category": "shopping", "grammar_points": ["modal could"], "en": "Could you check if you have {item} in stock?", "pt": "Você poderia verificar se tem {item} em estoque?"},
    {"level": "B1", "category": "transport", "grammar_points": ["past simple"], "en": "I missed the {transport}, so I took a taxi.", "pt": "Eu perdi o {transport}, então peguei um táxi."},
    {"level": "B1", "category": "health", "grammar_points": ["present perfect continuous"], "en": "I have been {activity} {frequency} to stay healthy.", "pt": "Eu tenho {activity} {frequency} para ficar saudável."},
    {"level": "B1", "category": "transport", "grammar_points": ["zero conditional"], "en": "If I miss the {transport}, I usually {backup_plan}.", "pt": "Se eu perco o {transport}, eu normalmente {backup_plan}."},
    {"level": "B1", "category": "work", "grammar_points": ["present perfect"], "en": "I have already {task} today.", "pt": "Eu já {task} hoje."},
    {"level": "B1", "category": "home", "grammar_points": ["past simple"], "en": "I forgot to {task} yesterday.", "pt": "Eu esqueci de {task} ontem."},
    {"level": "B1", "category": "shopping", "grammar_points": ["quantifiers"], "en": "I bought {quantity} {item} at the {store}.", "pt": "Eu comprei {quantity} {item} na {store}."},
    {"level": "B1", "category": "work", "grammar_points": ["past simple"], "en": "I was going to {place}, but {problem}.", "pt": "Eu ia ao {place}, mas {problem}."},
    {"level": "B1", "category": "shopping", "grammar_points": ["present perfect"], "en": "I have been saving money to buy a {device}.", "pt": "Eu tenho economizado dinheiro para comprar um {device}."},
    {"level": "B1", "category": "shopping", "grammar_points": ["past simple"], "en": "I called the {store} to check if they had {item}.", "pt": "Eu liguei para a {store} para ver se tinham {item}."},
    # B2
    {"level": "B2", "category": "opinions", "grammar_points": ["modal should"], "en": "We should cook at home more often {reason}.", "pt": "Nós deveríamos cozinhar em casa com mais frequência {reason}."},
    {"level": "B2", "category": "work", "grammar_points": ["past perfect"], "en": "By the time I got to the office, the meeting had already started.", "pt": "Quando cheguei ao escritório, a reunião já tinha começado."},
    {"level": "B2", "category": "home", "grammar_points": ["relative clauses"], "en": "The neighbor who lives upstairs plays music late.", "pt": "O vizinho que mora em cima toca música tarde."},
    {"level": "B2", "category": "shopping", "grammar_points": ["used to"], "en": "I used to shop in person, but now I buy online.", "pt": "Eu costumava comprar pessoalmente, mas agora compro online."},
    {"level": "B2", "category": "work", "grammar_points": ["reported speech"], "en": "My manager said that the deadline was moved.", "pt": "Meu gerente disse que o prazo foi adiado."},
    {"level": "B2", "category": "conversation", "grammar_points": ["mixed conditionals"], "en": "If I had known about the delay, I would be at {place} by now.", "pt": "Se eu soubesse do atraso, eu já estaria no {place}."},
    {"level": "B2", "category": "shopping", "grammar_points": ["too/enough"], "en": "The line is too long, so I will come back later.", "pt": "A fila está longa demais, então vou voltar depois."},
    {"level": "B2", "category": "opinions", "grammar_points": ["wish"], "en": "I wish I had more time to {activity}.", "pt": "Eu gostaria de ter mais tempo para {activity}."},
    {"level": "B2", "category": "work", "grammar_points": ["passive voice"], "en": "The deadline was moved to {day}.", "pt": "O prazo foi adiado para {day}."},
    {"level": "B2", "category": "opinions", "grammar_points": ["second conditional"], "en": "If I had more time, I would {activity}.", "pt": "Se eu tivesse mais tempo, eu iria {activity}."},
    {"level": "B2", "category": "shopping", "grammar_points": ["contrast"], "en": "The service was {quality}, but the {item} was {adjective}.", "pt": "O atendimento foi {quality}, mas o {item} estava {adjective}."},
    # C1
    {"level": "C1", "category": "work", "grammar_points": ["inversion", "emphasis"], "en": "Not only did I finish early, but I also helped my team.", "pt": "Não só terminei cedo, como também ajudei minha equipe."},
    {"level": "C1", "category": "life_events", "grammar_points": ["third conditional"], "en": "Had I left earlier, I would have avoided the traffic.", "pt": "Se eu tivesse saído mais cedo, teria evitado o trânsito."},
    {"level": "C1", "category": "formal", "grammar_points": ["complex clauses"], "en": "Were it not for the delay, the schedule would be on track.", "pt": "Se não fosse o atraso, o cronograma estaria em dia."},
    {"level": "C1", "category": "work", "grammar_points": ["advanced linking"], "en": "Given the circumstances, we opted to reschedule the appointment.", "pt": "Dadas as circunstâncias, optamos por remarcar a consulta."},
    {"level": "C1", "category": "formal", "grammar_points": ["advanced clauses"], "en": "Should any issue arise, please contact customer support.", "pt": "Caso surja qualquer problema, entre em contato com o suporte."},
    {"level": "C1", "category": "formal", "grammar_points": ["subordination"], "en": "While the {project} progressed, the team addressed {issue}.", "pt": "Enquanto o {project} avançava, a equipe tratou de {issue}."},
    # C2
    {"level": "C2", "category": "formal", "grammar_points": ["formal connectors"], "en": "Notwithstanding the delay, the service was impeccable.", "pt": "Apesar do atraso, o serviço foi impecável."},
    {"level": "C2", "category": "formal", "grammar_points": ["complex sentence structure"], "en": "It is imperative that we address the issue before it escalates.", "pt": "É imperativo que tratemos do problema antes que ele se agrave."},
    {"level": "C2", "category": "formal", "grammar_points": ["advanced discourse"], "en": "In light of recent events, policy adjustments are unavoidable.", "pt": "À luz dos eventos recentes, ajustes na política são inevitáveis."},
    {"level": "C2", "category": "formal", "grammar_points": ["formal register"], "en": "We are committed to resolving {issue} promptly.", "pt": "Estamos comprometidos em resolver {issue} prontamente."},
    {"level": "C2", "category": "formal", "grammar_points": ["advanced discourse"], "en": "Notwithstanding the constraints, the {project} was delivered on time.", "pt": "Apesar das restrições, o {project} foi entregue no prazo."},
]

LEVEL_TARGETS = {
    "A1": 850,
    "A2": 850,
    "B1": 500,
    "B2": 400,
    "C1": 300,
    "C2": 300,
}

PLACEHOLDER_RE = re.compile(r"{(\w+)}")


def render_template(template: Dict[str, object]) -> Tuple[str, str]:
    en = template["en"]
    pt = template["pt"]
    slots_in_template = set(PLACEHOLDER_RE.findall(en + " " + pt))
    chosen: Dict[str, Slot] = {}
    for slot_key in slots_in_template:
        chosen[slot_key] = random.choice(SLOTS[slot_key])
    for slot_key, slot_value in chosen.items():
        en = en.replace(f"{{{slot_key}}}", slot_value[0])
        pt = pt.replace(f"{{{slot_key}}}", slot_value[1])
    return en, pt


def build_candidates(template: Dict[str, object], max_candidates: int = 1200) -> List[Tuple[str, str]]:
    en = template["en"]
    pt = template["pt"]
    slots = sorted(set(PLACEHOLDER_RE.findall(en + " " + pt)))
    if not slots:
        return [(en, pt)]

    slot_lists = [SLOTS[s] for s in slots]
    total = 1
    for slot_list in slot_lists:
        total *= len(slot_list)

    candidates: List[Tuple[str, str]] = []
    if total <= max_candidates:
        for combo in itertools.product(*slot_lists):
            en_text = en
            pt_text = pt
            for slot_key, slot_value in zip(slots, combo):
                en_text = en_text.replace(f"{{{slot_key}}}", slot_value[0])
                pt_text = pt_text.replace(f"{{{slot_key}}}", slot_value[1])
            candidates.append((en_text, pt_text))
    else:
        seen = set()
        attempts = 0
        while len(seen) < max_candidates and attempts < max_candidates * 10:
            en_text, pt_text = render_template(template)
            if (en_text, pt_text) not in seen:
                seen.add((en_text, pt_text))
            attempts += 1
        candidates = list(seen)

    random.shuffle(candidates)
    return candidates


def generate_sentences() -> List[Dict[str, str]]:
    sentences: List[Dict[str, str]] = []
    seen = set()

    templates_by_level = {}
    for template in TEMPLATES:
        templates_by_level.setdefault(template["level"], []).append(template)

    for level, target in LEVEL_TARGETS.items():
        templates = templates_by_level[level]
        pool: List[Tuple[str, str, Dict[str, object]]] = []
        for template in templates:
            for en, pt in build_candidates(template):
                pool.append((en, pt, template))

        random.shuffle(pool)
        for en, pt, template in pool:
            if len([s for s in sentences if s["level"] == level]) >= target:
                break
            key = (en, pt)
            if key in seen:
                continue
            seen.add(key)
            sentences.append({
                "english": en,
                "portuguese": pt,
                "level": template["level"],
                "category": template["category"],
                "grammar_points": json_dumps(template["grammar_points"]),
            })

    return sentences


def json_dumps(value: List[str]) -> str:
    return "[" + ", ".join([f'"{v}"' for v in value]) + "]"


def write_csv(rows: List[Dict[str, str]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["english", "portuguese", "level", "category", "grammar_points"],
        )
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    out_path = Path("sentences_enrichment_us_daily_2000.csv")
    rows = generate_sentences()
    write_csv(rows, out_path)
    print(f"✅ Geradas {len(rows)} sentenças em {out_path}")
