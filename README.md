# LLM local para consulta de boletins de ocorrência (segurança pública)

Pipeline **RAG + LoRA** com Qwen2.5-3B-Instruct (4 bits) que recebe uma pergunta sobre ocorrências, busca o boletim
relevante e devolve um **JSON validado** com as entidades (`local`, `crime`, `arma`, `tipo_arma`,
`estado_vitima`) e a **fonte** (`id_bo`). Se nenhum boletim atinge o limiar, responde `{"resultado": "não consta"}`.

Relatório completo: [RELATORIO.md](RELATORIO.md)

## Estrutura

```
notebooks/   01_treinamento_lora.ipynb (treino e avaliações iniciais, com saídas)
             02_pipeline_e_placar.ipynb (base, busca, placar final, com saídas)
base/        base_conhecimento.json (100 trechos com fonte) e treino.jsonl (200 exemplos do LoRA)
avaliacao/   perguntas.jsonl, gabarito_base.json, teste_extracao.jsonl, busca.py, placar.py,
             busca_resultados.md, placar.md, limiar.json, erros_candidatos.md
src/         comum.py (prompts, parser, validação, LGPD), gerar_dados.py, api.py
modelo-lora-rag/   adaptador LoRA treinado (saída do notebook 01)
```

## Como reproduzir

Requisitos: Python 3.13, GPU NVIDIA com ~8 GB de VRAM (testado em RTX 4060), CUDA 13.

```bash
python -m venv .venv && .venv\Scripts\activate        # Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt

# 1) (opcional) retreinar o LoRA: rode notebooks/01_treinamento_lora.ipynb e
#    copie a pasta gerada modelo-lora-rag/ para a raiz do repositório.

# 2) Base, gabarito e perguntas (seed fixa = 42)
python src/gerar_dados.py

# 3) Busca: recall@1, recall@3 e limiar  -> avaliacao/busca_resultados.md, limiar.json
python avaliacao/busca.py

# 4) Placar das 3 configurações         -> avaliacao/placar.md, erros_candidatos.md
python avaliacao/placar.py
```

Ou rode `notebooks/02_pipeline_e_placar.ipynb` de cima para baixo. A geração é greedy
(`do_sample=False`), então os resultados são reproduzíveis na mesma versão de bibliotecas.

## API

```bash
uvicorn src.api:app --port 8000        # docs em http://localhost:8000/docs
```

`GET /saude` → `{"status": "ok", "trechos_na_base": 100, "limiar": ...}`

`POST /consulta`

```bash
curl -X POST http://localhost:8000/consulta -H "Content-Type: application/json" \
     -d '{"pergunta": "Houve roubo na rua augusta com uma faca?"}'
```

```json
{
  "score": 0.78, "limiar": 0.62, "pii_mascarada": false,
  "resposta": {"local": "rua augusta", "crime": "roubo", "arma": true, "tipo_arma": "branca",
               "estado_vitima": "lesao", "fonte": "BO-1234"},
  "fonte": "BO-1234",
  "trecho": "Aconteceu um roubo na rua augusta. O bandido tava com uma faca. tá sangrando.",
  "explicacao": "Entidades extraídas do boletim BO-1234 (similaridade 0.78 >= 0.62)."
}
```

Sem boletim relevante: `{"resposta": {"resultado": "não consta"}, "fonte": null, ...}`. Erros: `422` (entrada
inválida: 3 a 300 caracteres) e `429` (rate limit de 30 req/min por IP).

## Segurança, explicabilidade e LGPD

| Tema | Como é tratado |
|---|---|
| Prompt injection | A pergunta do usuário **não entra no prompt do LLM**; só o boletim recuperado entra |
| Saída do modelo | Validada por schema (pydantic, categorias fechadas) e a `fonte` é conferida com o boletim recuperado; se falhar, vira "não consta" |
| Abuso | Entrada limitada a 300 caracteres, caracteres de controle removidos, rate limit por IP |
| Explicabilidade | A resposta traz `fonte`, `trecho` original, `score` e `limiar` |
| LGPD | CPF, e-mail e telefone são mascarados antes de qualquer processamento; perguntas não são gravadas nem logadas; a base é **sintética** (sem dados pessoais); processamento 100% local (nenhum dado sai da máquina); minimização de dados |

## Limitações

Base sintética de 100 boletins com vocabulário controlado; o desempenho em boletins reais, com linguagem livre,
não foi medido. Não use como único critério para decisões de segurança pública.


## Link Youtube

- Para Acessar a demonstração clique <a href="https://youtu.be/Wq1OEOU3vTE">aqui</a>.


## Integrantes

| Nome completo | RM |
|---|---|
| Arthur Baldissera Marcos Claumann | 550219 |
| Pedro Henrique Fernandes Lô de Barros | 97937 |
| Ricardo Ramos Vergani | 550166 |
| Victor Kenzo Toma | 551649 |