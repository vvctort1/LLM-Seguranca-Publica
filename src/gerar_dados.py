"""Gera (com seed fixa) a base de conhecimento, o gabarito e as perguntas de avaliação.

Saídas:
  base/base_conhecimento.json     100 boletins sintéticos com fonte, formato e licença
  avaliacao/gabarito_base.json    campos corretos de cada boletim (gabarito da extração)
  avaliacao/perguntas.jsonl       50 perguntas: 30 válidas (com gold_ids) + 20 fora de escopo ("não consta")
"""
import json
import random
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
random.seed(42)

LOCAIS = ["praça da sé", "metro consolação", "rua augusta", "ponto de ônibus", "avenida paulista",
          "estacionamento do shopping", "rua de trás", "centro da cidade"]
CRIMES = ["roubo", "assalto", "furto", "homicídio", "latrocínio", "ameaça", "sequestro",
          "vandalismo", "agressão"]
ARMAS = {"um 38": "fogo", "uma pistola": "fogo", "um revólver": "fogo",
         "uma faca": "branca", "um facão": "branca", "uma peixeira": "branca",
         "um pedaço de pau": "branca", "na mão grande": "desarmado", "só no grito": "desarmado"}
VITIMAS = {"tomei um soco": "lesao", "me cortou": "lesao", "tá sangrando": "lesao",
           "foi esfaqueado": "lesao", "mataram ele": "fatalidade", "tá morto": "fatalidade",
           "só o susto mesmo": "sem_lesao", "tá todo mundo bem": "sem_lesao"}

FONTE = "Boletim de ocorrência sintético (gerado por src/gerar_dados.py, seed 42)"
FORMATO = "JSON (id_bo, texto)"
LICENCA = "MIT — dados sintéticos criados pelo projeto, sem dados pessoais"

# ------------------------------------------------------------------ base
ids = random.sample(range(1, 10000), 100)          # IDs únicos (a versão antiga tinha duplicado)
base, gabarito, meta = [], {}, {}
for n in ids:
    local, crime = random.choice(LOCAIS), random.choice(CRIMES)
    arma, vitima = random.choice(list(ARMAS)), random.choice(list(VITIMAS))
    id_bo = f"BO-{n:04d}"
    base.append({
        "id_bo": id_bo,
        "texto": f"Aconteceu um {crime} na {local}. O bandido tava com {arma}. {vitima}.",
        "fonte": FONTE, "formato": FORMATO, "licenca": LICENCA,
    })
    cat = ARMAS[arma]
    gabarito[id_bo] = {
        "local": local, "crime": crime,
        "arma": True if cat in ("fogo", "branca") else False,
        "tipo_arma": cat, "estado_vitima": VITIMAS[vitima], "fonte": id_bo,
    }
    meta[id_bo] = (crime, local, arma)

# ------------------------------------------------------------------ perguntas
TEMPLATES = [
    "Houve algum caso de {c} em {l} em que o criminoso estava com {a}?",
    "Tem relato de {c} em {l}? Eles usaram {a}.",
    "{C} em {l}, o bandido tava com {a}.",
    "Preciso do boletim de {c} ocorrido em {l} envolvendo {a}.",
]
perguntas = []
for k, id_bo in enumerate(random.sample(list(meta), 30), 1):
    c, l, a = meta[id_bo]
    # gold = todos os boletins com mesmo crime + local + arma (a pergunta não menciona a vítima)
    gold = [i for i, m in meta.items() if m == (c, l, a)]
    q = random.choice(TEMPLATES).format(c=c, C=c.capitalize(), l=l, a=a)
    perguntas.append({"id": f"Q{k:02d}", "categoria": "valida", "pergunta": q, "gold_ids": gold})

FORA = [
    "Como consertar o pneu de uma bicicleta ergométrica?",
    "Receita de strogonoff de frango rápida na panela de pressão.",
    "Extravio de mala no aeroporto de congonhas, voo da gol.",
    "Onde comprar ingresso para o show de rock no Allianz Parque?",
    "Briga de dinossauros T-Rex no museu de história natural.",
    "Qual a cotação do dólar comercial hoje no banco central?",
    "Invasão alienígena no beco escuro com armas laser.",
    # perto do domínio (segurança), mas sem boletim correspondente na base:
    "Houve golpe do pix na praça da sé?",
    "Teve incêndio criminoso na avenida paulista?",
    "Acidente de trânsito com vítima fatal na marginal tietê.",
    "Tem registro de crime cibernético contra um banco?",
    "Alguém foi preso por tráfico de drogas na rua augusta?",
    "Ocorreu violência doméstica no prédio da esquina?",
    "Houve falha de energia elétrica no centro da cidade ontem?",
    "Qual o horário do metrô na estação da luz?",
    "Tem câmeras de segurança quebradas no ponto de ônibus?",
    "Como registrar um boletim de ocorrência online?",
    "Quantos policiais trabalham na região da avenida paulista?",
    "Houve rebelião em presídio de segurança máxima?",
    "Qual a previsão do tempo para amanhã em São Paulo?",
]
for k, q in enumerate(FORA, 31):
    perguntas.append({"id": f"Q{k:02d}", "categoria": "fora_de_escopo", "pergunta": q, "gold_ids": []})

# ------------------------------------------------------------------ salvar
(RAIZ / "base").mkdir(exist_ok=True)
(RAIZ / "avaliacao").mkdir(exist_ok=True)
json.dump(base, open(RAIZ / "base" / "base_conhecimento.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
json.dump(gabarito, open(RAIZ / "avaliacao" / "gabarito_base.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
with open(RAIZ / "avaliacao" / "perguntas.jsonl", "w", encoding="utf-8") as f:
    for p in perguntas:
        f.write(json.dumps(p, ensure_ascii=False) + "\n")

print(f"Base: {len(base)} boletins (IDs únicos: {len({b['id_bo'] for b in base})})")
print(f"Perguntas: {sum(p['categoria']=='valida' for p in perguntas)} válidas + "
      f"{sum(p['categoria']=='fora_de_escopo' for p in perguntas)} fora de escopo")
print("Exemplo:", base[0]["texto"], "|", perguntas[0]["pergunta"], "-> gold", perguntas[0]["gold_ids"])
