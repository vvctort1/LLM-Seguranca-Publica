## Placar das três configurações

Buscador `all-MiniLM-L6-v2`, limiar 0.7, geração greedy (determinística). 30 perguntas válidas + 20 fora de escopo.

### Ponta a ponta (pergunta → busca → geração)

| Métrica | A · Base sem contexto | B · Base + RAG simples | C · LoRA + RAG |
|---|---|---|---|
| Acerto total (resposta certa ou recusa certa) | 16/50 (32%) | 34/50 (68%) | 45/50 (90%) |
| JSON válido (schema) | 19/50 (38%) | 46/50 (92%) | 50/50 (100%) |
| Fonte correta (válidas) | 0/30 (0%) | 27/30 (90%) | 27/30 (90%) |
| Campos + fonte corretos (válidas) | 0/30 (0%) | 14/30 (47%) | 25/30 (83%) |
| Recusa correta (fora de escopo) | 16/20 (80%) | 20/20 (100%) | 20/20 (100%) |
| Alucinação (menor é melhor) | 31/50 (62%) | 14/50 (28%) | 3/50 (6%) |

### Extração isolada (30 casos com gabarito, 4 são "não consta")

| Métrica | B · Base + RAG simples | C · LoRA + RAG |
|---|---|---|
| Acerto total | 11/30 (37%) | 23/30 (77%) |
| Vocabulário conhecido | 5/15 (33%) | 13/15 (87%) |
| Vocabulário inédito | 6/15 (40%) | 10/15 (67%) |
| Recusas ("não consta") | 4/4 (100%) | 4/4 (100%) |
| JSON válido | 29/30 (97%) | 29/30 (97%) |