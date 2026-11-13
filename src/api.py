"""API do produto: pergunta -> busca -> LLM (Qwen + LoRA) -> JSON validado com fonte.

Rodar (na raiz do repositório):  uvicorn src.api:app --port 8000
Docs interativas: http://localhost:8000/docs

Segurança:   a pergunta do usuário NUNCA entra no prompt do LLM (só o boletim recuperado entra),
             o que elimina prompt injection pela pergunta; entrada limitada; rate limit; saída validada
             por schema (pydantic) e fonte conferida; qualquer falha vira "não consta".
Explicabilidade: a resposta traz fonte, trecho original, score e o limiar usado.
LGPD:        PII (CPF, e-mail, telefone) mascarada antes de qualquer processamento; perguntas NÃO são
             gravadas nem logadas; a base é sintética (sem dados pessoais); minimização de dados.
"""
import json
import sys
from contextlib import asynccontextmanager
import threading
import time
from collections import defaultdict, deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi import FastAPI, HTTPException, Request  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

from comum import (RAIZ, SYS_LORA, Buscador, carregar_base, carregar_llm, eh_recusa,  # noqa: E402
                   extrair_json, gerar, json_valido, mascarar_pii, montar_prompt, tarefa_rag)

E = {}                                   # estado carregado no startup
TRAVA = threading.Lock()                 # uma geração por vez (GPU única)
JANELA, LIMITE = 60, 30                  # rate limit: 30 requisições / 60 s por IP
HIST = defaultdict(deque)


class Consulta(BaseModel):
    pergunta: str = Field(min_length=3, max_length=300, examples=["Houve roubo na rua augusta com uma faca?"])


@asynccontextmanager
async def ciclo(_app):
    cfg = json.load(open(RAIZ / "avaliacao" / "limiar.json"))
    E["cfg"], E["base"] = cfg, carregar_base()
    E["busca"] = Buscador(cfg["modelo"], [b["texto"] for b in E["base"]])
    E["model"], E["tok"] = carregar_llm(com_lora=True)
    yield


app = FastAPI(title="Consulta de Boletins de Ocorrência (LLM local)", version="1.0", lifespan=ciclo)


@app.get("/saude")
def saude():
    return {"status": "ok", "trechos_na_base": len(E.get("base", [])), "limiar": E.get("cfg", {}).get("limiar")}


@app.post("/consulta")
def consulta(c: Consulta, req: Request):
    ip, agora = req.client.host if req.client else "?", time.time()
    h = HIST[ip]
    while h and agora - h[0] > JANELA:
        h.popleft()
    if len(h) >= LIMITE:
        raise HTTPException(429, "Muitas requisições. Tente novamente em instantes.")
    h.append(agora)

    pergunta = mascarar_pii("".join(ch for ch in c.pergunta if ch.isprintable()).strip())
    i, score = E["busca"].buscar(pergunta, 1)[0]
    limiar = E["cfg"]["limiar"]
    base = {"score": round(score, 3), "limiar": limiar, "pii_mascarada": pergunta != c.pergunta.strip()}

    if score < limiar:                    # recusa determinística: nenhum documento relevante
        return {**base, "resposta": {"resultado": "não consta"}, "fonte": None, "trecho": None,
                "explicacao": "Nenhum boletim da base atingiu o limiar de similaridade."}

    doc = E["base"][i]
    prompt = montar_prompt(SYS_LORA, tarefa_rag(doc["texto"], doc["id_bo"]))
    with TRAVA:
        saida = gerar(E["model"], E["tok"], prompt, 150)
    d = extrair_json(saida)
    if not json_valido(d) or (not eh_recusa(d) and d.get("fonte") != doc["id_bo"]):
        return {**base, "resposta": {"resultado": "não consta"}, "fonte": None, "trecho": None,
                "explicacao": "A saída do modelo foi rejeitada na validação (schema/fonte); resposta bloqueada."}
    return {**base, "resposta": d, "fonte": doc["id_bo"], "trecho": doc["texto"],
            "explicacao": f"Entidades extraídas do boletim {doc['id_bo']} (similaridade {score:.2f} >= {limiar})."}
