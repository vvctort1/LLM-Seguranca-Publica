"""Funções compartilhadas: prompts, parser/validação de JSON, busca, LGPD e LLM."""
import json
import re
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, StrictBool, StrictStr, ValidationError

RAIZ = Path(__file__).resolve().parent.parent
MODELO_BASE = "Qwen/Qwen2.5-3B-Instruct"
ADAPTADOR = RAIZ / "modelo-lora-rag"          # saída do notebook 01 (treino QLoRA)
BASE_JSON = RAIZ / "base" / "base_conhecimento.json"

CAMPOS = ["local", "crime", "arma", "tipo_arma", "estado_vitima"]

TAREFA = ("Extraia as entidades do contexto em formato JSON e cite a fonte. "
          "Se o contexto disser 'Nenhum documento relevante', retorne {\"resultado\": \"não consta\"}.")

# IMPORTANTE: idêntico ao system prompt usado no TREINO (notebook 01). A diferença entre
# treino e avaliação fazia o LoRA falhar nas recusas (erro #1 do relatório).
SYS_LORA = "Você é um extrator de entidades JSON."

# Baseline "RAG simples": modelo base + contexto + schema e exemplo no prompt (comparação justa).
SYS_RAG = (
    "Você é um extrator de entidades JSON. Responda APENAS com um objeto JSON, sem texto extra.\n"
    "Se houver documento, use exatamente estas chaves: \"local\" (texto, ou \"desconhecido\"), "
    "\"crime\" (texto), \"arma\" (true, false ou null), \"tipo_arma\" (\"fogo\", \"branca\", "
    "\"desarmado\" ou \"desconhecido\"), \"estado_vitima\" (\"lesao\", \"fatalidade\", \"sem_lesao\" "
    "ou \"desconhecido\") e \"fonte\" (o ID do boletim informado em 'Fonte').\n"
    "Se o contexto disser 'Nenhum documento relevante', responda exatamente {\"resultado\": \"não consta\"}.\n"
    "Exemplo de contexto (Fonte: BO-9999): Aconteceu um furto na rua augusta. O bandido tava com uma faca. "
    "tá sangrando.\n"
    "Exemplo de resposta: {\"local\": \"rua augusta\", \"crime\": \"furto\", \"arma\": true, "
    "\"tipo_arma\": \"branca\", \"estado_vitima\": \"lesao\", \"fonte\": \"BO-9999\"}"
)

# Configuração A: modelo sem contexto (só a pergunta).
SYS_SEM_CONTEXTO = "Você é um extrator de entidades JSON. Responda APENAS com um objeto JSON."


def montar_prompt(sistema, usuario):
    return (f"<|im_start|>system\n{sistema}<|im_end|>\n"
            f"<|im_start|>user\n{usuario}<|im_end|>\n<|im_start|>assistant\n")


def tarefa_rag(contexto=None, fonte=None):
    """Mesmo formato do treino. contexto=None => a busca não achou nada (caso de recusa)."""
    if contexto is None:
        return f"### Contexto Recuperado:\nNenhum documento relevante encontrado.\n### Tarefa:\n{TAREFA}"
    return f"### Contexto Recuperado (Fonte: {fonte}):\n{contexto}\n### Tarefa:\n{TAREFA}"


def tarefa_sem_contexto(pergunta):
    return (f"### Pergunta:\n{pergunta}\n### Tarefa:\nResponda em JSON com as chaves local, crime, arma, "
            "tipo_arma, estado_vitima e fonte. Se não tiver informação, retorne {\"resultado\": \"não consta\"}.")


# ---------------------------------------------------------------- JSON
_DEC = json.JSONDecoder()


def extrair_json(texto):
    """Primeiro objeto JSON do texto (aceita aninhado, ignora markdown/tagarelice)."""
    i = texto.find("{")
    while i != -1:
        try:
            obj, _ = _DEC.raw_decode(texto[i:])
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            pass
        i = texto.find("{", i + 1)
    return None


class Entidades(BaseModel):
    model_config = ConfigDict(extra="forbid")
    local: StrictStr
    crime: StrictStr
    arma: Optional[StrictBool]
    tipo_arma: Literal["fogo", "branca", "desarmado", "desconhecido"]
    estado_vitima: Literal["lesao", "fatalidade", "sem_lesao", "desconhecido"]
    fonte: StrictStr


def eh_recusa(d):
    return isinstance(d, dict) and d.get("resultado") == "não consta"


def json_valido(d):
    """Recusa ou objeto que obedece ao schema (6 chaves, tipos e categorias corretos)."""
    if d is None:
        return False
    if eh_recusa(d):
        return True
    try:
        Entidades(**d)
        return True
    except (ValidationError, TypeError):
        return False


# ---------------------------------------------------------------- LGPD
_PII = [
    (re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b"), "[CPF]"),
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"), "[EMAIL]"),
    (re.compile(r"(?:\(?\d{2}\)?\s?)?9?\d{4}-?\d{4}\b"), "[TELEFONE]"),
]


def mascarar_pii(texto):
    for rx, rotulo in _PII:
        texto = rx.sub(rotulo, texto)
    return texto


# ---------------------------------------------------------------- Base e busca
def carregar_base():
    return json.load(open(BASE_JSON, encoding="utf-8"))


class Buscador:
    def __init__(self, nome_modelo, textos):
        from sentence_transformers import SentenceTransformer
        self.m = SentenceTransformer(nome_modelo)
        self.v = self.m.encode(textos, normalize_embeddings=True)

    def buscar(self, pergunta, k=3):
        import numpy as np
        q = self.m.encode([pergunta], normalize_embeddings=True)[0]
        s = self.v @ q
        idx = np.argsort(-s)[:k]
        return [(int(i), float(s[i])) for i in idx]


# ---------------------------------------------------------------- LLM
def carregar_llm(com_lora=False):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_use_double_quant=True,
                             bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.bfloat16)
    tok = AutoTokenizer.from_pretrained(MODELO_BASE)
    model = AutoModelForCausalLM.from_pretrained(MODELO_BASE, quantization_config=bnb, device_map="auto")
    if com_lora:
        from peft import PeftModel
        model = PeftModel.from_pretrained(model, str(ADAPTADOR))
    model.eval()
    return model, tok


def gerar(model, tok, prompt, max_new=150):
    """Geração determinística (greedy) -> resultados reproduzíveis."""
    import torch
    ent = tok(prompt, return_tensors="pt").to(model.device)
    with torch.no_grad():
        out = model.generate(**ent, max_new_tokens=max_new, do_sample=False, temperature=None,
                             top_p=None, top_k=None, pad_token_id=tok.eos_token_id)
    return tok.decode(out[0][ent["input_ids"].shape[1]:], skip_special_tokens=True).strip()
