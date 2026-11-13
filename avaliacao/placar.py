"""Critérios 04, 05 e 06: placar das 3 configurações (+ teste de extração com 30 casos).

  A  Qwen base SEM contexto (só a pergunta)
  B  Qwen base + RAG simples (contexto recuperado + schema/exemplo no prompt)
  C  Qwen + LoRA + RAG (prompt idêntico ao do treino)

Requer: avaliacao/limiar.json (rode avaliacao/busca.py antes) e o adaptador em modelo-lora-rag/.
Saídas: avaliacao/placar.md, placar.json, respostas_*.jsonl, erros_candidatos.md
"""
import json
import sys
import time
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
AV = RAIZ / "avaliacao"
sys.path.insert(0, str(RAIZ / "src"))
from comum import (ADAPTADOR, CAMPOS, SYS_LORA, SYS_RAG, SYS_SEM_CONTEXTO, Buscador,  # noqa: E402
                   carregar_base, carregar_llm, eh_recusa, extrair_json, gerar, json_valido,
                   montar_prompt, tarefa_rag, tarefa_sem_contexto)

cfg = json.load(open(AV / "limiar.json"))
base = carregar_base()
ids_base = {b["id_bo"] for b in base}
gab = json.load(open(AV / "gabarito_base.json", encoding="utf-8"))
perguntas = [json.loads(l) for l in open(AV / "perguntas.jsonl", encoding="utf-8")]
extracao = [json.loads(l) for l in open(AV / "teste_extracao.jsonl", encoding="utf-8")]
buscador = Buscador(cfg["modelo"], [b["texto"] for b in base])
print(f"Buscador: {cfg['modelo']} | limiar {cfg['limiar']}")

# recuperação feita uma vez (igual para B e C)
for p in perguntas:
    i, s = buscador.buscar(p["pergunta"], 1)[0]
    ok = s >= cfg["limiar"]
    p["_ctx"] = (base[i]["id_bo"], base[i]["texto"]) if ok else (None, None)
    p["_score"] = s


def avaliar_item(texto, p):
    d = extrair_json(texto)
    r = {"id": p["id"], "categoria": p["categoria"], "pergunta": p["pergunta"], "resposta": texto,
         "json_valido": json_valido(d), "recusou": eh_recusa(d)}
    if p["categoria"] == "fora_de_escopo":
        r["correto"] = r["recusou"]
        r["alucinou"] = d is not None and not r["recusou"]
        r["motivo"] = "" if r["correto"] else ("não recusou fora de escopo" if d else "JSON inválido")
        return r
    fonte = d.get("fonte") if d else None
    if not isinstance(fonte, str):
        fonte = None
    r["fonte_correta"] = (not r["recusou"]) and fonte in p["gold_ids"]
    campos_ok = r["fonte_correta"] and all(d.get(k) == gab[fonte][k] for k in CAMPOS)
    r["correto"] = bool(campos_ok)
    cita_inexistente = d is not None and not r["recusou"] and fonte not in ids_base
    campo_errado = (d is not None and not r["recusou"] and fonte in gab
                    and any(d.get(k) != gab[fonte][k] for k in CAMPOS))
    r["alucinou"] = bool(cita_inexistente or campo_errado)
    if r["correto"]:
        r["motivo"] = ""
    elif d is None:
        r["motivo"] = "JSON inválido"
    elif r["recusou"]:
        r["motivo"] = "recusa indevida (pergunta válida)"
    elif cita_inexistente:
        r["motivo"] = "fonte inexistente (alucinação)"
    elif not r["fonte_correta"]:
        r["motivo"] = "fonte errada (busca trouxe outro boletim)"
    else:
        r["motivo"] = "campo errado: " + ",".join(k for k in CAMPOS if d.get(k) != gab[fonte][k])
    return r


def avaliar_extracao(texto, esperado_str):
    d, g = extrair_json(texto), json.loads(esperado_str)
    if eh_recusa(g):
        return {"ok": eh_recusa(d), "json_valido": json_valido(d), "motivo": "" if eh_recusa(d) else "não recusou"}
    erros = [k for k in CAMPOS + ["fonte"] if d is None or d.get(k) != g.get(k)]
    return {"ok": not erros and json_valido(d), "json_valido": json_valido(d),
            "motivo": ("JSON inválido" if d is None else "campos: " + ",".join(erros)) if erros else ""}


def rodar(nome, model, tok, fazer_prompt):
    t0, saida = time.time(), []
    for p in perguntas:
        saida.append(avaliar_item(gerar(model, tok, fazer_prompt(p), 150), p))
    ext = []
    if nome in ("B", "C"):
        sys_ = SYS_RAG if nome == "B" else SYS_LORA
        for ex in extracao:
            r = avaliar_extracao(gerar(model, tok, montar_prompt(sys_, ex["tarefa"]), 150), ex["codigo"])
            ext.append({**r, "tipo": ex["tipo"], "esperado_recusa": eh_recusa(json.loads(ex["codigo"]))})
    with open(AV / f"respostas_{nome}.jsonl", "w", encoding="utf-8") as f:
        for r in saida:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"Config {nome} pronta em {time.time()-t0:.0f}s")
    return saida, ext


# ---------------------------------------------------------------- execução
model, tok = carregar_llm(com_lora=False)
res = {}
res["A"] = rodar("A", model, tok, lambda p: montar_prompt(SYS_SEM_CONTEXTO, tarefa_sem_contexto(p["pergunta"])))
res["B"] = rodar("B", model, tok, lambda p: montar_prompt(SYS_RAG, tarefa_rag(p["_ctx"][1], p["_ctx"][0])))

from peft import PeftModel  # noqa: E402
model = PeftModel.from_pretrained(model, str(ADAPTADOR))
model.eval()
res["C"] = rodar("C", model, tok, lambda p: montar_prompt(SYS_LORA, tarefa_rag(p["_ctx"][1], p["_ctx"][0])))

# ---------------------------------------------------------------- métricas
NOMES = {"A": "A · Base sem contexto", "B": "B · Base + RAG simples", "C": "C · LoRA + RAG"}


def pct(a, b):
    return f"{a}/{b} ({a / b:.0%})" if b else "-"


resumo = {}
for k, (saida, ext) in res.items():
    v = [r for r in saida if r["categoria"] == "valida"]
    f = [r for r in saida if r["categoria"] == "fora_de_escopo"]
    resumo[k] = {
        "acerto_total": pct(sum(r["correto"] for r in saida), len(saida)),
        "json_valido": pct(sum(r["json_valido"] for r in saida), len(saida)),
        "fonte_correta": pct(sum(r["fonte_correta"] for r in v), len(v)),
        "campos_corretos": pct(sum(r["correto"] for r in v), len(v)),
        "recusa_correta": pct(sum(r["correto"] for r in f), len(f)),
        "alucinacao": pct(sum(r["alucinou"] for r in saida), len(saida)),
    }
    if ext:
        rec = [e for e in ext if e["esperado_recusa"]]
        resumo[k]["extracao_30"] = pct(sum(e["ok"] for e in ext), len(ext))
        resumo[k]["extracao_variacao"] = pct(sum(e["ok"] for e in ext if e["tipo"] == "variacao"),
                                             sum(e["tipo"] == "variacao" for e in ext))
        resumo[k]["extracao_inedita"] = pct(sum(e["ok"] for e in ext if e["tipo"] == "inedita"),
                                            sum(e["tipo"] == "inedita" for e in ext))
        resumo[k]["extracao_recusa"] = pct(sum(e["ok"] for e in rec), len(rec))
        resumo[k]["extracao_json_valido"] = pct(sum(e["json_valido"] for e in ext), len(ext))

linhas = ["## Placar das três configurações\n",
          f"Buscador `{cfg['modelo'].split('/')[-1]}`, limiar {cfg['limiar']}, geração greedy (determinística). "
          f"{sum(p['categoria']=='valida' for p in perguntas)} perguntas válidas + "
          f"{sum(p['categoria']=='fora_de_escopo' for p in perguntas)} fora de escopo.\n",
          "### Ponta a ponta (pergunta → busca → geração)\n",
          "| Métrica | " + " | ".join(NOMES.values()) + " |", "|---|---|---|---|"]
for m, rot in [("acerto_total", "Acerto total (resposta certa ou recusa certa)"),
               ("json_valido", "JSON válido (schema)"),
               ("fonte_correta", "Fonte correta (válidas)"),
               ("campos_corretos", "Campos + fonte corretos (válidas)"),
               ("recusa_correta", "Recusa correta (fora de escopo)"),
               ("alucinacao", "Alucinação (menor é melhor)")]:
    linhas.append(f"| {rot} | " + " | ".join(resumo[k][m] for k in "ABC") + " |")
linhas += ["", "### Extração isolada (30 casos com gabarito, 4 são \"não consta\")\n",
           "| Métrica | B · Base + RAG simples | C · LoRA + RAG |", "|---|---|---|"]
for m, rot in [("extracao_30", "Acerto total"), ("extracao_variacao", "Vocabulário conhecido"),
               ("extracao_inedita", "Vocabulário inédito"), ("extracao_recusa", "Recusas (\"não consta\")"),
               ("extracao_json_valido", "JSON válido")]:
    linhas.append(f"| {rot} | {resumo['B'][m]} | {resumo['C'][m]} |")
(AV / "placar.md").write_text("\n".join(linhas), encoding="utf-8")
json.dump(resumo, open(AV / "placar.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)

# ---------------------------------------------------------------- erros candidatos (critério 07)
out = ["# Erros candidatos (gerado automaticamente)\n"]
for k, (saida, ext) in res.items():
    erros = [r for r in saida if not r["correto"]]
    cont = Counter(r["motivo"].split(":")[0] for r in erros)
    out.append(f"## Config {k}: {len(erros)} erros — {dict(cont)}\n")
    vistos = set()
    for r in erros:
        tipo = r["motivo"].split(":")[0]
        if tipo in vistos:
            continue
        vistos.add(tipo)
        out.append(f"- **{r['id']}** [{r['motivo']}] pergunta: {r['pergunta']}\n  resposta: `{r['resposta'][:200]}`")
    out.append("")
(AV / "erros_candidatos.md").write_text("\n".join(out), encoding="utf-8")

print("\n".join(linhas))
print("\nErros candidatos salvos em avaliacao/erros_candidatos.md")
