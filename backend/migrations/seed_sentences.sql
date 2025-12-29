-- Seed: Initial sentences for study
-- Created: 2025-12-17
-- Description: Adds initial set of common sentences for English learning

INSERT INTO sentences (english, portuguese, level, category, difficulty_score, grammar_points, vocabulary_used) VALUES
-- A1 Level - Basic Greetings and Introductions
('Hello, how are you?', 'Olá, como você está?', 'A1', 'greetings', 1.0, '["present simple", "question formation"]', '["hello", "how", "are", "you"]'),
('My name is John.', 'Meu nome é John.', 'A1', 'introductions', 1.0, '["verb to be", "possessive pronouns"]', '["my", "name", "is"]'),
('Nice to meet you.', 'Prazer em conhecê-lo.', 'A1', 'greetings', 1.5, '["polite expressions"]', '["nice", "meet", "you"]'),
('Where are you from?', 'De onde você é?', 'A1', 'introductions', 2.0, '["question words", "present simple"]', '["where", "from", "you"]'),
('I am from Brazil.', 'Eu sou do Brasil.', 'A1', 'introductions', 1.5, '["verb to be", "countries"]', '["I", "am", "from", "Brazil"]'),

-- A1 Level - Daily Activities
('I wake up at 7 AM.', 'Eu acordo às 7 da manhã.', 'A1', 'daily_routine', 2.0, '["present simple", "time expressions"]', '["wake", "up", "at"]'),
('I have breakfast every day.', 'Eu tomo café da manhã todos os dias.', 'A1', 'daily_routine', 2.0, '["present simple", "frequency adverbs"]', '["have", "breakfast", "every", "day"]'),
('She goes to work by bus.', 'Ela vai para o trabalho de ônibus.', 'A1', 'transportation', 2.5, '["present simple", "prepositions"]', '["goes", "work", "by", "bus"]'),
('We eat lunch at noon.', 'Nós almoçamos ao meio-dia.', 'A1', 'daily_routine', 2.0, '["present simple", "time"]', '["eat", "lunch", "noon"]'),
('They study English at school.', 'Eles estudam inglês na escola.', 'A1', 'education', 2.0, '["present simple", "subjects"]', '["study", "English", "school"]'),

-- A2 Level - Past and Future
('I went to the store yesterday.', 'Eu fui à loja ontem.', 'A2', 'shopping', 3.0, '["past simple", "time expressions"]', '["went", "store", "yesterday"]'),
('She will travel next week.', 'Ela vai viajar na próxima semana.', 'A2', 'travel', 3.5, '["future simple", "time expressions"]', '["will", "travel", "next", "week"]'),
('We were watching TV when you called.', 'Estávamos assistindo TV quando você ligou.', 'A2', 'daily_life', 4.0, '["past continuous", "past simple", "time clauses"]', '["were", "watching", "TV", "called"]'),
('I have lived here for two years.', 'Eu moro aqui há dois anos.', 'A2', 'personal_life', 4.0, '["present perfect", "duration"]', '["have", "lived", "for", "years"]'),
('He is going to buy a car.', 'Ele vai comprar um carro.', 'A2', 'plans', 3.0, '["going to future", "objects"]', '["going", "buy", "car"]'),

-- B1 Level - More Complex Structures
('If I had more time, I would learn another language.', 'Se eu tivesse mais tempo, aprenderia outro idioma.', 'B1', 'hypothetical', 6.0, '["second conditional", "modal verbs"]', '["if", "had", "would", "learn", "language"]'),
('I have been studying English for three years.', 'Eu estudo inglês há três anos.', 'B1', 'education', 5.0, '["present perfect continuous", "duration"]', '["have", "been", "studying", "for"]'),
('The book that I read was very interesting.', 'O livro que eu li foi muito interessante.', 'B1', 'literature', 5.0, '["relative clauses", "past simple"]', '["book", "that", "read", "interesting"]'),
('She told me that she would come later.', 'Ela me disse que viria mais tarde.', 'B1', 'reported_speech', 6.0, '["reported speech", "modal verbs"]', '["told", "would", "come", "later"]'),
('I wish I could speak English fluently.', 'Eu queria poder falar inglês fluentemente.', 'B1', 'wishes', 6.5, '["wish + past simple", "modal verbs"]', '["wish", "could", "speak", "fluently"]'),

-- B2 Level - Advanced Topics
('Having finished my work, I went home.', 'Tendo terminado meu trabalho, fui para casa.', 'B2', 'work', 7.0, '["perfect participles", "time expressions"]', '["having", "finished", "work", "went"]'),
('No sooner had I arrived than the phone rang.', 'Mal eu cheguei e o telefone tocou.', 'B2', 'narrative', 8.0, '["inversion", "past perfect", "past simple"]', '["no", "sooner", "arrived", "rang"]'),
('I would rather you didn''t tell anyone.', 'Prefiro que você não conte para ninguém.', 'B2', 'preferences', 7.5, '["would rather", "subjunctive"]', '["would", "rather", "tell", "anyone"]'),
('The project, which took six months, was finally completed.', 'O projeto, que levou seis meses, finalmente foi concluído.', 'B2', 'work', 7.0, '["non-defining relative clauses", "passive voice"]', '["project", "took", "months", "completed"]'),
('Not only did she win the race, but she also broke the record.', 'Ela não só venceu a corrida, como também quebrou o recorde.', 'B2', 'sports', 8.0, '["inversion", "correlative conjunctions"]', '["not", "only", "win", "broke", "record"]')
ON CONFLICT DO NOTHING;

-- Update statistics
SELECT COUNT(*) as total_sentences FROM sentences;
