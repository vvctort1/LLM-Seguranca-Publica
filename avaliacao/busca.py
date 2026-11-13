"""Critério 03: mede recall@1 e recall@3 de dois buscadores e escolhe/justifica o limiar.

Saídas: avaliacao/busca_resultados.md, avaliacao/limiar.json, avaliacao/limiar.png
"""
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))
from comum import Buscador, carregar_base  # noqa: E402

MODELOS = ["sentence-transformers/all-MiniLM-L6-v2",
           "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"]

base = carregar_base()
ids = [b["id_bo"] for b in base]
textos = [b["texto"] for b in base]
perguntas = [json.loads(l) for l in open(RAIZ / "avaliacao" / "perguntas.jsonl", encoding="utf-8")]
validas = [p for p in perguntas if p["categoria"] == "valida"]
fora = [p for p in perguntas if p["categoria"] == "fora_de_escopo"]


def avaliar_modelo(nome):
    b = Buscador(nome, textos)
    r = {"modelo": nome, "valida": [], "fora": []}
    for p in validas:
        top = b.buscar(p["pergunta"], 3)
        gold = set(p["gold_ids"])
        r["valida"].append({"score": top[0][1], "hit1": ids[top[0][0]] in gold,
                            "hit3": any(ids[i] in gold for i, _ in top)})
    for p in fora:
        r["fora"].append({"score": b.buscar(p["pergunta"], 1)[0][1]})
    r["recall1"] = sum(x["hit1"] for x in r["valida"]) / len(validas)
    r["recall3"] = sum(x["hit3"] for x in r["valida"]) / len(validas)

    def acuracia(t):
        ok = sum(x["score"] >= t and x["hit1"] for x in r["valida"]) + sum(x["score"] < t for x in r["fora"])
        return ok / len(perguntas)

    grade = [round(0.20 + 0.01 * i, 2) for i in range(76)]            # 0.20 ... 0.95
    acc = {t: acuracia(t) for t in grade}
    melhor = max(acc.values())
    plateau = sorted(t for t in grade if acc[t] == melhor)
    r["limiar"] = round(plateau[len(plateau) // 2], 2)                # meio do platô de melhor acurácia
    r["acuracia"] = melhor
    r["plateau"] = (plateau[0], plateau[-1])
    r["acc_por_limiar"] = {t: acc[t] for t in [0.40, 0.50, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85]}
    return r


res = [avaliar_modelo(m) for m in MODELOS]
melhor = max(res, key=lambda r: (r["recall1"], r["acuracia"]))

# ---------------------------------------------------------------- relatório
linhas = ["## Busca semântica — recall e limiar\n",
          f"Base: {len(base)} trechos | {len(validas)} perguntas válidas (com gabarito) + "
          f"{len(fora)} fora de escopo (devem virar \"não consta\")\n",
          "| Buscador | recall@1 | recall@3 | limiar escolhido | acurácia da decisão no limiar |",
          "|---|---|---|---|---|"]
for r in res:
    linhas.append(f"| {r['modelo'].split('/')[-1]} | {r['recall1']:.0%} | {r['recall3']:.0%} | "
                  f"{r['limiar']} | {r['acuracia']:.0%} |")
linhas += ["", f"**Escolhido:** `{melhor['modelo']}` com limiar **{melhor['limiar']}**.", "",
           "### Justificativa do limiar", "",
           "Decisão correta = (pergunta válida com score >= limiar **e** top-1 certo) ou "
           "(pergunta fora de escopo com score < limiar).", "",
           "| limiar | " + " | ".join(str(t) for t in melhor["acc_por_limiar"]) + " |",
           "|---|" + "---|" * len(melhor["acc_por_limiar"]),
           "| acurácia | " + " | ".join(f"{v:.0%}" for v in melhor["acc_por_limiar"].values()) + " |", ""]
vs = sorted(x["score"] for x in melhor["valida"])
fs = sorted(x["score"] for x in melhor["fora"])
linhas.append(f"Scores das perguntas válidas: min {vs[0]:.2f}, mediana {vs[len(vs)//2]:.2f}. "
              f"Fora de escopo: mediana {fs[len(fs)//2]:.2f}, máx {fs[-1]:.2f}. "
              f"O limiar fica no platô [{melhor['plateau'][0]}, {melhor['plateau'][1]}] de máxima acurácia; "
              "usamos o ponto central para ter margem dos dois lados.")
(RAIZ / "avaliacao" / "busca_resultados.md").write_text("\n".join(linhas), encoding="utf-8")
json.dump({"modelo": melhor["modelo"], "limiar": melhor["limiar"], "recall1": melhor["recall1"],
           "recall3": melhor["recall3"], "acuracia": melhor["acuracia"]},
          open(RAIZ / "avaliacao" / "limiar.json", "w"), indent=2)

# ---------------------------------------------------------------- gráfico
import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

plt.figure(figsize=(7, 3.5))
plt.hist(vs, bins=15, alpha=.7, label="válidas")
plt.hist(fs, bins=15, alpha=.7, label="fora de escopo")
plt.axvline(melhor["limiar"], color="k", ls="--", label=f"limiar {melhor['limiar']}")
plt.xlabel("score de similaridade (top-1)")
plt.ylabel("perguntas")
plt.legend()
plt.tight_layout()
plt.savefig(RAIZ / "avaliacao" / "limiar.png", dpi=130)

print("\n".join(linhas))
