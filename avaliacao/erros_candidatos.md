# Erros candidatos (gerado automaticamente)

## Config A: 34 erros — {'fonte inexistente (alucinação)': 27, 'recusa indevida (pergunta válida)': 3, 'não recusou fora de escopo': 4}

- **Q01** [fonte inexistente (alucinação)] pergunta: Tem relato de agressão em praça da sé? Eles usaram uma faca.
  resposta: `{"local": "praça da sé", "crime": "agressão", "arma": "faca", "tipo_arma": "lanceira", "estado_vitima": "nenhum informado", "fonte": "notícia"}`
- **Q07** [recusa indevida (pergunta válida)] pergunta: Houve algum caso de ameaça em rua de trás em que o criminoso estava com uma pistola?
  resposta: `{"resultado": "não consta"}`
- **Q35** [não recusou fora de escopo] pergunta: Briga de dinossauros T-Rex no museu de história natural.
  resposta: `{"local": "museu de história natural", "crime": "briga de dinossauros T-Rex", "arma": "nenhum informado", "tipo_arma": "nenhum informado", "estado_vitima": "nenhum informado", "fonte": "não consta"}`

## Config B: 16 erros — {'fonte errada (busca trouxe outro boletim)': 3, 'campo errado': 13}

- **Q03** [fonte errada (busca trouxe outro boletim)] pergunta: Tem relato de ameaça em ponto de ônibus? Eles usaram um facão.
  resposta: `{"local": "ponto de ônibus", "crime": "ameaça", "arma": true, "tipo_arma": "branca", "estado_vitima": "fatalidade", "fonte": "BO-7528"}`
- **Q06** [campo errado: crime,estado_vitima] pergunta: Preciso do boletim de homicídio ocorrido em rua de trás envolvendo um revólver.
  resposta: `{"local": "rua de trás", "crime": "homicidio", "arma": true, "tipo_arma": "fogo", "estado_vitima": "fatalidade", "fonte": "BO-9293"}`

## Config C: 5 erros — {'fonte errada (busca trouxe outro boletim)': 3, 'campo errado': 2}

- **Q03** [fonte errada (busca trouxe outro boletim)] pergunta: Tem relato de ameaça em ponto de ônibus? Eles usaram um facão.
  resposta: `{"local": "ponto de ônibus", "crime": "ameaça", "arma": true, "tipo_arma": "branca", "estado_vitima": "fatalidade", "fonte": "BO-7528"}`
- **Q28** [campo errado: arma,tipo_arma] pergunta: Vandalismo em estacionamento do shopping, o bandido tava com na mão grande.
  resposta: `{"local": "estacionamento do shopping", "crime": "vandalismo", "arma": true, "tipo_arma": "branca", "estado_vitima": "sem_lesao", "fonte": "BO-3753"}`
