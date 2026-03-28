# Base de Conhecimento

## Dados Utilizados

| Arquivo             | Formato | Utilização no Agente                                                        |
| ------------------- | ------- | --------------------------------------------------------------------------- |
| `cpus.csv`          | CSV     | Selecionar processadores com base em desempenho, consumo e custo-benefício  |
| `gpus.csv`          | CSV     | Definir placa de vídeo conforme perfil (gamer, IA, edição) e orçamento      |
| `ram.csv`           | CSV     | Escolher memória adequada (capacidade e frequência) conforme uso            |
| `storage.csv`       | CSV     | Determinar tipo e capacidade de armazenamento (NVMe, SATA)                  |
| `motherboards.csv`  | CSV     | Garantir compatibilidade com CPU e suporte a upgrades                       |
| `psu.csv`           | CSV     | Dimensionar fonte com base no consumo total e margem de segurança           |
| `cases.csv`         | CSV     | Selecionar gabinete considerando airflow e perfil do usuário                |
| `profiles.csv`      | CSV     | Definir prioridades de hardware conforme tipo de usuário                    |
| `build_rules.csv`   | CSV     | Aplicar regras de decisão (ex: mínimo de RAM, preferência por NVIDIA, etc.) |
| `compatibility.csv` | CSV     | Validar compatibilidade entre CPU e placa-mãe                               |
| `config.json`       | JSON    | Controlar pesos de decisão e regras globais do sistema                      |


> [!TIP]
> **Quer um dataset mais robusto?** Você pode utilizar datasets públicos do [Hugging Face](https://huggingface.co/datasets) relacionados a finanças, desde que sejam adequados ao contexto do desafio.

---

## Adaptações nos Dados

> Você modificou ou expandiu os dados mockados? Descreva aqui.

Sim, os dados mockados foram completamente substituídos para uma base mais coerente com o agente, descartando a ideia exemplo de um agente financeiro.
A nova base conta com arquivos e dados reais de toda a configuração de um computador, separado peça por peça, 
contendo também um score baseado no orçamento e no perfil do usuário e um arquivo de compatibilidade, que garante que as peças recomendadas sejam sempre compatíveis.

---

## Estratégia de Integração

Como os dados são carregados?

Descreva como seu agente acessa a base de conhecimento.

Os dados são armazenados localmente na pasta data/ em formato CSV e JSON.
No início da execução do agente, todos os arquivos são carregados utilizando Pandas (para CSV) e json (para configuração).

O carregamento é feito uma única vez e mantido em memória para garantir performance durante as recomendações.

Script de carregamento (estrutura real do projeto):

```python
import pandas as pd
import json
import os

class DataLoader:
    def __init__(self, base_path="data"):
        self.base_path = base_path
        self.data = {}
        self.load_all()

    def load_csv(self, filename):
        path = os.path.join(self.base_path, filename)
        return pd.read_csv(path)

    def load_json(self, filename):
        path = os.path.join(self.base_path, filename)
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def load_all(self):
        self.data["cpus"] = self.load_csv("cpus.csv")
        self.data["gpus"] = self.load_csv("gpus.csv")
        self.data["ram"] = self.load_csv("ram.csv")
        self.data["storage"] = self.load_csv("storage.csv")
        self.data["motherboards"] = self.load_csv("motherboards.csv")
        self.data["psu"] = self.load_csv("psu.csv")
        self.data["cases"] = self.load_csv("cases.csv")
        self.data["profiles"] = self.load_csv("profiles.csv")
        self.data["build_rules"] = self.load_csv("build_rules.csv")
        self.data["compatibility"] = self.load_csv("compatibility.csv")
        self.data["config"] = self.load_json("configuration_weights.json")
```

## Como os dados são usados no prompt?

Os dados vão no system prompt? São consultados dinamicamente?

Os dados não são totalmente injetados no prompt (para evitar excesso de tokens).
Em vez disso, o sistema utiliza uma abordagem híbrida:

- Consulta dinâmica (principal)
O agente Python filtra e seleciona apenas as melhores opções com base no orçamento e perfil.
- Contexto reduzido para o LLM
Apenas os componentes finalistas (top escolhas) são enviados para o modelo de linguagem.
- System prompt fixo
Define regras de montagem (compatibilidade, balanceamento, prioridades por perfil).
- Dados estruturados no prompt
O LLM recebe um JSON com:
-Opções selecionadas
-Regras aplicáveis
-Perfil do usuário

Isso garante:

Eficiência (baixo custo de tokens)
Precisão (dados filtrados previamente)
Controle (regras aplicadas via código)

## Exemplo de Contexto Montado

Mostre um exemplo de como os dados são formatados para o agente.
```json
{
  "usuario": {
    "perfil": "gamer",
    "orcamento": 5000
  },
  "opcoes_filtradas": {
    "cpu": [
      {"modelo": "Ryzen 5 5600", "preco": 899},
      {"modelo": "Intel i5-12400F", "preco": 950}
    ],
    "gpu": [
      {"modelo": "RX 7600", "preco": 1800},
      {"modelo": "RTX 4060", "preco": 2000}
    ],
    "ram": [
      {"modelo": "16GB DDR4 3200", "preco": 350}
    ]
  },
  "regras_aplicadas": [
    "priorizar GPU para gamer",
    "mínimo 16GB RAM",
    "não ultrapassar orçamento",
    "garantir compatibilidade de socket"
  ]
}
```

## Exemplo de Contexto Montado

Exemplo real de como os dados são estruturados e enviados ao agente (LLM) após o pré-processamento em Python.
```txt
[CONTEXTO DO USUÁRIO]
Perfil: gamer
Orçamento: R$ 5000

[PRIORIDADES]
GPU: alta
CPU: média
RAM: média
Storage: média

[OPÇÕES DISPONÍVEIS]

CPU:
- Ryzen 5 5600 (6c/12t, AM4) - R$ 899
- i5-12400F (6c/12t, LGA1700) - R$ 950

GPU:
- RX 7600 (8GB) - R$ 1800
- RTX 4060 (8GB) - R$ 2000

RAM:
- 16GB DDR4 3200 - R$ 350

Storage:
- SSD NVMe 1TB - R$ 400

Placa-mãe:
- B550M (AM4) - R$ 700
- B660M (LGA1700) - R$ 750

Fonte:
- 650W 80+ Bronze - R$ 320

Gabinete:
- Airflow alto - R$ 200

[REGRAS]
- Não ultrapassar orçamento
- Priorizar GPU (perfil gamer)
- Mínimo 16GB RAM
- Usar SSD NVMe
- Garantir compatibilidade (CPU + placa-mãe)
- Fonte com margem de segurança

[OBJETIVO]
Montar o melhor PC possível equilibrando desempenho e custo.
```
