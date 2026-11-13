## Busca semântica — recall e limiar

Base: 100 trechos | 30 perguntas válidas (com gabarito) + 20 fora de escopo (devem virar "não consta")

| Buscador | recall@1 | recall@3 | limiar escolhido | acurácia da decisão no limiar |
|---|---|---|---|---|
| all-MiniLM-L6-v2 | 90% | 100% | 0.7 | 94% |
| paraphrase-multilingual-MiniLM-L12-v2 | 73% | 93% | 0.67 | 82% |

**Escolhido:** `sentence-transformers/all-MiniLM-L6-v2` com limiar **0.7**.

### Justificativa do limiar

Decisão correta = (pergunta válida com score >= limiar **e** top-1 certo) ou (pergunta fora de escopo com score < limiar).

| limiar | 0.4 | 0.5 | 0.6 | 0.65 | 0.7 | 0.75 | 0.8 | 0.85 |
|---|---|---|---|---|---|---|---|---|
| acurácia | 54% | 64% | 84% | 90% | 94% | 88% | 78% | 54% |

Scores das perguntas válidas: min 0.71, mediana 0.82. Fora de escopo: mediana 0.54, máx 0.69. O limiar fica no platô [0.7, 0.7] de máxima acurácia; usamos o ponto central para ter margem dos dois lados.