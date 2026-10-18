# Pitwall Lab

Portfólio de ciência de dados sobre Fórmula 1, construído passo a passo para aprendizado.

## Objetivo

No futuro: criar um dashboard que estime a probabilidade de cada piloto terminar uma corrida no pódio.

**Etapa atual:** a etapa 4 treinou e avaliou localmente o modelo v1 de probabilidade individual de pódio. O treino usa 2021–2023 e a validação usa 2024; 2025 continua reservado, não foi aberto nem avaliado. As seções das etapas 1–3 abaixo são histórico preservado, não descrição do estado atual.

## Etapa 4 — modelo v1, sem abrir 2025

### Como reproduzir

Com as dependências já instaladas no ambiente virtual:

```bash
./.venv/bin/python treinar_modelo_v1.py
./.venv/bin/python -m unittest discover -s tests -v
```

Em outra máquina, instale antes as versões fixadas:

```bash
./.venv/bin/python -m pip install -r requirements_modelo_v1.txt
```

O treinamento lê exclusivamente `data/preparado/treino.csv`, `validacao.csv` e `colunas.json`. A seleção é uma lista fixa de 15 entradas do [plano do experimento](docs/experimento_modelo_v1.md); chaves, identificação, `podio` e auditoria são recusados como entrada. O plano existia antes do ajuste; seu SHA-256 é `d6c671526aafe1ca8a1a6b98934a1d1915eb7a102872d51e5385991257fec569`.

### Resultado em 2024

- Cobertura: 479 linhas, 24 GPs, todas elegíveis e com alvo conhecido; os 24 GPs atenderam às regras comuns de ranking.
- Modelo logístico: log loss **0,2296** e Brier **0,0709**. Referência constante do treino: **0,4233** e **0,1277**, respectivamente. Menor é melhor.
- Ranking top 3: modelo com média de **1,96** integrantes corretos e **6/24 (25,00%)** de GPs com os três integrantes; referência de classificação com **1,88** e **4/24 (16,67%)**.
- A única linha inelegível de treino foi `mick_schumacher`, Mônaco 2021, por `classificacao_ausente`. A validação teve 0 alvos desconhecidos e 8 linhas com classificação ambígua; os detalhes estão nos CSVs de cobertura e previsões.

Estes são resultados retrospectivos na validação já explorada de 2024, não previsão registrada antes das corridas nem evidência de generalização para 2025. As probabilidades por piloto não foram forçadas a somar três em cada GP.

### Entregas

- [Revisão independente e correções](reports/modelo_v1/revisao_independente.md), com [os dois pareceres completos](reports/modelo_v1/revisao_independente.json): aprovação final por `openai-codex/gpt-6-astra`, rota efetiva conferida e **100 testes aprovados**. Implementação e correções por `openai-codex/gpt-5.6-terra`; 2025 permaneceu fechado.
- [Relatório e limitações](reports/modelo_v1/relatorio.md), [métricas estruturadas](reports/modelo_v1/metricas.json), [previsões da validação](reports/modelo_v1/previsoes_validacao.csv) e [avaliação por corrida](reports/modelo_v1/avaliacao_corridas.csv).
- [Calibração por dez faixas](reports/modelo_v1/calibracao.csv) e [gráfico SVG](reports/modelo_v1/calibracao.svg).
- [Coeficientes padronizados](reports/modelo_v1/coeficientes.csv), [cobertura do treino](reports/modelo_v1/cobertura_treino.csv), [metadados e hashes](models/modelo_v1/metadados.json) e `models/modelo_v1/modelo.joblib`.

O joblib foi produzido localmente e não deve ser carregado quando vier de terceiros. Duas execuções consecutivas produziram bytes idênticos para os dez artefatos. Saídas existentes diferentes são preservadas, sem sobrescrita automática.

### Usar o pipeline salvo sem treinar novamente

Na pasta do projeto, com as mesmas versões instaladas, o exemplo abaixo reaplica o pipeline **somente à validação de 2024** e mostra as cinco primeiras probabilidades. Não usa `.fit`, não abre 2025 e não grava arquivos:

```bash
./.venv/bin/python - <<'PY'
import json
from pathlib import Path
import joblib
from treinar_modelo_v1 import carregar_dados, prever_validacao

artefato = joblib.load('models/modelo_v1/modelo.joblib')  # somente arquivo local confiável
meta = json.loads(Path('models/modelo_v1/metadados.json').read_text())
fontes = carregar_dados('data/preparado')
previsoes = prever_validacao(
    artefato['pipeline'], meta['constante_treino'],
    fontes['validacao'], fontes['esquema'],
)
for linha in previsoes[:5]:
    print(linha['corrida'], linha['piloto_id'], linha['probabilidade_modelo'])
PY
```

O pipeline guarda as medianas, escalas e coeficientes aprendidos no treino. A função de previsão seleciona apenas as entradas autorizadas; o alvo não é fornecido ao classificador. Reproduzir em outra plataforma pode alterar os últimos dígitos numéricos: as versões e o Python da execução estão em `metadados.json`.


### Correção de compatibilidade numérica

O experimento usa `numpy==1.26.4`. Com a fotografia anterior `numpy==2.0.2`, uma contraprova simulada de multiplicação matricial emitia `RuntimeWarning`, embora entradas e saída fossem finitas. A contraprova equivalente com 1.26.4 não emitiu avisos; as duas execuções reais também não. Isso identifica uma incompatibilidade observada da pilha anterior nesta máquina, sem atribuir causa interna específica ao BLAS. O código agora transforma `RuntimeWarning` em erro durante ajuste e previsão, sem suprimi-los.

## Etapa 3 — base histórica sem treinamento

### O que executar

Na pasta do projeto, usando o ambiente virtual existente:

```bash
./.venv/bin/python coletar_historico.py --temporadas 2021 2022 2023 2024 2025
./.venv/bin/python preparar_historico.py
./.venv/bin/python -m unittest discover -s tests -v
```

O primeiro comando consulta apenas calendários, resultados **principais** e classificação. Na primeira coleta pode levar vários minutos: cada consulta é espaçada por pelo menos oito segundos. Não execute coletores em paralelo. O novo coletor recebe as temporadas por parâmetro; **os comandos antigos continuam iguais**, restritos às entregas originais.

Para reproduzir sem novas consultas à API:

```bash
./.venv/bin/python coletar_historico.py --temporadas 2021 2022 2023 2024 2025 --somente-cache
./.venv/bin/python preparar_historico.py
```

A preparação é sempre offline. Primeiro valida todas as fontes, depois cria as variáveis e só então grava as saídas finais. Não produz base completa se faltar uma temporada/página obrigatória ou se houver inconsistências. Saídas existentes diferentes não são substituídas: preserve um backup explícito antes de aceitar uma atualização deliberada. Falhas de rede ou HTTP 429 encerram a coleta sem repetição automática. Uma execução interrompida pode ser retomada com os caches válidos, mas não transforma cache parcial em base completa.

### Entregas

- [Qualidade por temporada e cobertura](reports/historico/qualidade.md), com relatórios individuais de 2021 a 2025 e [contagens em JSON](reports/historico/qualidade.json).
- [Revisão independente, correções e testes](reports/historico/revisao_etapa3.md): aprovação alternativa com provedor/modelo efetivos conferidos; revisão Astra inicial interrompida por limite de uso.
- [Dicionário das variáveis e fórmulas](docs/dicionario_variaveis.md).
- [Protocolo temporal e divisão treino/validação/teste](docs/protocolo_temporal.md).
- [Base histórica completa para auditoria](data/preparado/base_historica.csv).
- [Entradas permitidas](data/preparado/entradas.csv), [identificação](data/preparado/identificacao.csv), [alvos](data/preparado/alvos.csv) e [desfechos apenas para auditoria](data/preparado/auditoria_resultados.csv), separados fisicamente e relacionados pelas mesmas chaves.
- [Papéis das colunas](data/preparado/colunas.json), [janelas auditáveis](data/preparado/auditoria_janelas.json), [divisões por corrida](data/preparado/divisoes.csv) e [comprovante da preparação](data/preparado/verificacao.json).
- JSON originais e proveniência em `data/historico/2021/` até `data/historico/2025/`.
- Scripts `coletar_historico.py` e `preparar_historico.py`, com testes adicionais em `tests/`.

Os arquivos `treino.csv`, `validacao.csv` e `teste_final_reservado.csv`, em `data/preparado/`, são visões completas por período. Para um futuro modelo, use **somente** as entradas explicitamente listadas em `colunas.json`; não forneça automaticamente todas as colunas da base completa ou desses recortes.

### Como pensar nas variáveis

Cada linha representa um piloto em um GP. A chave é **temporada + rodada + piloto_id**. A classificação vem de `QualifyingResults.position`, nunca de `Results.grid`. Se a API repetir uma posição de classificação para pilotos distintos, a base preserva a posição original em todas as linhas e marca `posicao_classificacao_repetida=1`; isso sinaliza ambiguidade, sem inventar desempate, eliminar pilotos ou substituir a classificação pelo grid retrospectivo. As ocorrências aparecem nos relatórios de qualidade.

- Média da posição final e taxa de pódios: até **cinco participações anteriores do piloto**, com denominadores explícitos.
- Pontos da equipe: soma dos pontos de seus pilotos nos até **cinco GPs anteriores da equipe**, dividida pelo número real de registros de pilotos nesses eventos. Não é a soma de pontos por GP, e não inclui sprints.
- Sem histórico, as médias ficam vazias e os contadores são zero. Isso não significa desempenho zero nem necessariamente estreia na F1.
- Sem classificação, a linha não desaparece; há indicadores de ausência. A equipe pré-corrida não é preenchida usando o resultado atual.
- Posição final, pontos, status e grid da corrida atual ficam apenas na auditoria. `podio` é o alvo, nunca entrada. Sem resultado, o alvo é desconhecido, não zero.

A união externa preserva participantes presentes em apenas uma das fontes. Os relatórios listam os IDs sem correspondência e diferenciam ausência observada de hipóteses explicativas. Não eliminamos abandonos, não largadas ou desclassificações.

### Corte temporal e limites que não podem ser escondidos

O corte conceitual é o encerramento da sessão que define a ordem-base do GP. Nos eventos Sprint de 2021–2022, essa sessão é a Sprint; a variável de classificação continua sendo a tomada de tempos anterior à Sprint, com a diferença sinalizada. Não presumimos um dia fixo do fim de semana.

A API informa inícios de sessões, não encerramentos comprovados. O fim fica desconhecido. Para as **janelas históricas**, usamos um limite conservador anterior ao fim: início da sessão, ou início UTC do dia se só houver data ou o campo `time` vier vazio. Horários não vazios precisam estar em UTC com `Z`; valores inválidos interrompem a preparação. Resultados de um GP anterior só entram a partir do dia UTC seguinte à sua data, nunca na própria corrida ou em uma corrida futura. Essa regra é explicada, com suas limitações, no protocolo.

**Datas da coleta atual não provam disponibilidade histórica.** Os JSON consultados hoje podem incorporar revisões posteriores ao corte. Os testes controlam a ordem dos cálculos, não certificam a versão que estava publicada anos atrás. Este é um estudo retrospectivo, não prova de uma previsão realmente emitida ao fim da classificação.

Novas respostas registram URL, parâmetros, instante UTC de obtenção e SHA-256 dos bytes originais. Caches antigos reaproveitados sem data de coleta ficam com `obtido_em_utc: desconhecida`; não usamos a data do arquivo ou commit como se fosse a da consulta original. Os arquivos antigos não são alterados.

### Avaliação cronológica definida, mas ainda não executada

| Divisão | Temporadas | Finalidade |
|---|---|---|
| Treino | 2021–2023 | Futuro ajuste do modelo e das transformações. |
| Validação | 2024 | Desenvolvimento; **já explorada**, não é teste intocado. |
| Teste final reservado | 2025 | Somente integridade e preparação mecânica nesta etapa. |

Todos os pilotos de um GP ficam na mesma divisão. Depois de uma corrida, seus resultados podem entrar no histórico da seguinte, inclusive dentro de 2025. Isso **não autoriza ajustar o modelo ou os transformadores usando o teste**. Não calculamos desempenho em 2025, não selecionamos variáveis por seus resultados e não ajustamos imputação ou normalização em toda a base.

O projeto continua usando somente a biblioteca padrão do Python, dados públicos e ferramentas gratuitas. A configuração dos modelos do Hermes não faz parte desta etapa e não foi alterada.

## Etapa 2 — temporada completa e primeira referência

### Entregas e resultado principal

- [Relatório completo em português](reports/temporada_2024/relatorio.md), com tabelas, gráficos, metodologia, fontes e limitações.
- [Base de 2024](data/temporada_2024/resultados_2024.csv): **24 corridas principais e 479 registros**, incluindo abandonos, não largadas e desclassificações.
- [Comprovante e resumo da verificação](data/temporada_2024/verificacao.json): corridas esperadas/coletadas, registros por corrida, campos ausentes, duplicações, status, pódios e hashes dos arquivos.
- [Avaliação da regra em cada corrida](reports/temporada_2024/avaliacao_por_corrida.csv): pilotos escolhidos, pódio real, IDs e acertos, ignorando a ordem.
- [Frequência por grid](reports/temporada_2024/frequencia_grid.csv) e [resumo calculado](reports/temporada_2024/resumo.json).

A regra **escolher os pilotos do grid 1, 2 e 3** acertou, em média, **2,00 dos 3 integrantes por corrida**. Foram **48/72 pódios (66,67%)** vindos do top 3 do grid; os três integrantes corretos ocorreram em **5/24 corridas (20,83%)**. Todas as 24 corridas foram avaliáveis, sem posições 1, 2 ou 3 ausentes ou duplicadas.

São Paulo foi a única corrida com **0 de 3 acertos: 1/24 (4,17%)**. Isso a torna incomum descritivamente em 2024, sem provar que esse circuito será sempre imprevisível.

### Comandos para reproduzir

Use a pasta do projeto e o ambiente virtual já preparado. Substitua o caminho de exemplo pelo caminho local; na máquina original, a pasta se chama `F1`.

```bash
cd "/caminho/para/pitwall-lab"
./.venv/bin/python coletar_temporada.py
./.venv/bin/python analisar_temporada.py
./.venv/bin/python -m unittest discover -s tests -v
open reports/temporada_2024/previa.html
```

Não é necessário instalar bibliotecas novas. Os gráficos são **SVG estáticos**, e a prévia é um HTML autocontido, não um dashboard. O relatório Markdown pode ser lido diretamente no GitHub.

- `coletar_temporada.py`: descobre as corridas pelo calendário, consulta apenas `/2024/results/`, pagina com `limit`/`offset`, valida e monta a tabela. Reaproveita o calendário válido da etapa 1 sem alterá-lo. Nesta extração, os resultados exigiram cinco páginas da API, além do calendário reaproveitado.
- `analisar_temporada.py`: não acessa a rede. Reconstrói a base das páginas locais e confere o CSV e o comprovante antes de gerar as tabelas e os gráficos.
- Repetir os comandos normalmente reutiliza o cache. Não busca automaticamente correções posteriores da API.

### Arquivos adicionais

```text
coletar_temporada.py
analisar_temporada.py
tests/test_temporada.py
data/temporada_2024/
├── resultados_2024.csv
├── verificacao.json
└── raw/
    ├── calendario_offset_0000.json
    ├── resultados_offset_0000.json
    ├── resultados_offset_0100.json
    ├── resultados_offset_0200.json
    ├── resultados_offset_0300.json
    └── resultados_offset_0400.json
reports/temporada_2024/
├── relatorio.md
├── resumo.json
├── frequencia_grid.csv
├── avaliacao_por_corrida.csv
├── frequencia_grid.svg
├── acertos_por_corrida.svg
├── distribuicao_acertos.svg
└── previa.html
```

### Colunas da base de 2024

| Coluna | Significado |
| --- | --- |
| `temporada` | Ano da temporada. |
| `rodada` | Número da etapa descoberto no calendário. |
| `corrida` | Nome da corrida na fonte. |
| `data_corrida` | Data no formato ano-mês-dia, conforme a API. |
| `circuito_id` / `circuito` | Identificador e nome do circuito. |
| `piloto_id` / `piloto` | Identificador e nome do piloto. |
| `equipe_id` / `equipe` | Identificador e nome da equipe naquela corrida. |
| `posicao_largada` | Grid registrado nos resultados; zero é tratado separadamente. |
| `posicao_final` | Posição numérica do resultado da API. |
| `status` | Situação final, preservada na forma original. |
| `pontos` | Pontos da corrida principal; não inclui pontos de sprints. |
| `podio` | `1` se a posição final está entre 1 e 3; `0` nos demais casos. |

A chave de cada registro é **temporada + rodada + piloto_id**. Os relacionamentos usam IDs, não nomes. O indicador de pódio é o resultado que queremos estudar, não uma informação disponível antes da corrida. Posição final, status final e pontos também não devem ser usados para escolher retrospectivamente os favoritos.

### Verificação, diferenças e acesso responsável

Não há campos obrigatórios ausentes nem duplicações de temporada/rodada/piloto nesta base. Todas as corridas têm exatamente três posições de pódio. **A Austrália tem 19 registros**; as demais têm 20. O comunicado da Williams explica a retirada de Sargeant após a decisão de usar seu carro para Albon. Não adicionamos uma linha fictícia nem exigimos 20 registros em toda corrida. O relatório contém a contagem de cada etapa e a fonte dessa investigação.

Há um único `grid=0`, Ocon no México. A documentação original Ergast, à qual a Jolpica remete para lacunas, define zero como largada do **pit lane**. A notícia oficial da F1 confirma esse caso. Não é uma posição melhor que a pole, e sua frequência aparece separada. Não presumimos que todos os casos reais de pit lane estejam codificados como zero. As fontes estão no relatório.

O coletor se identifica como `PitwallLab/0.2.0`, incluindo a versão do Python, e espaça requisições por pelo menos oito segundos. Foram conferidos os limites documentados de 4/s e 500/h; são sujeitos a mudanças e compartilhados pelo IP. Não execute várias cópias simultaneamente. HTTP 429 encerra a coleta com orientação de espera, sem repetição automática.

Cada página precisa ter estrutura válida, identificadores, campos necessários, total, limite e offset coerentes antes de ser gravada. Uma corrida pode atravessar páginas: a união usa IDs e não duplica os registros. A tabela final e seu comprovante só são produzidos depois da conferência completa. **Caches parciais não são uma base completa.** Se houver falha, a execução termina com saída 1, informa o problema e preserva saídas anteriores. A análise rejeita base parcial, alterada ou sem comprovante válido.

Conteúdo existente diferente não é sobrescrito. Para cache inválido, mova **somente o arquivo indicado** para backup fora do projeto e execute novamente; mantenha as demais páginas válidas. Para atualizar deliberadamente toda a fotografia da temporada, guarde um backup da pasta `data/temporada_2024` e dos relatórios antes de retirar os arquivos dos caminhos ativos. Não apague os dados de São Paulo da etapa 1. Caso os relatórios existentes sejam diferentes dos recém-calculados, também é necessário preservá-los em backup antes de regenerar.

Os novos testes são sem rede e incluem paginação com corrida dividida, falha intermediária sem tabela final, totais incoerentes, campos inválidos, duplicações, três pódios, grid zero, ausência/duplicação de favoritos, acertos sem ordem, ausência de filtro por status e proteção contra sobrescrita. Os testes anteriores foram mantidos.

### Prévia dos gráficos

**Leitura:** barras representam frequências observadas. Os rótulos mostram numerador, denominador e porcentagem. Isso não é uma probabilidade estimada por um modelo.

![Pódio por posição de grid](reports/temporada_2024/frequencia_grid.svg)

![Acertos por corrida](reports/temporada_2024/acertos_por_corrida.svg)

![Distribuição de acertos](reports/temporada_2024/distribuicao_acertos.svg)

### Limites da referência

Esta é uma avaliação **retrospectiva do grid registrado nos resultados**, não uma previsão registrada logo após a classificação. Penalidades e mudanças de grid podem ocorrer depois desse momento. Nenhum favorito foi escolhido pelo status ou resultado final.

Um futuro modelo precisará superar a referência em dados não usados para ajustá-lo e em condições comparáveis de disponibilidade das informações. A média de 2,00 acertos e a taxa de 20,83% de pódios completos são referências descritivas de 2024, não metas garantidas para qualquer temporada. Não treinamos modelos nesta etapa nem atribuímos causalidade às associações observadas.


## Ferramentas e ambiente

- Ambiente verificado nesta máquina: Python 3.9.6 e Git 2.54.0 (Apple Git-157).
- O script usa somente a biblioteca padrão do Python. Não é necessário instalar pacotes com `pip`, pagar serviços, criar conta ou informar chave de API para esta consulta.
- `.venv/` é o **ambiente virtual**: uma pasta com um Python separado para este projeto. Quando houver bibliotecas adicionais, elas poderão ser instaladas aqui sem misturar com as de outros projetos. Não é uma máquina virtual e não muda seu Python global.
- O Git mantém o histórico local do projeto; o GitHub pode hospedar uma cópia remota. O `.gitignore` exclui o ambiente virtual e padrões comuns de segredos do versionamento. Antes de publicar, revise os arquivos selecionados e a identidade do autor dos commits.

## Como executar no macOS

Abra o Terminal e copie os comandos abaixo, uma linha por vez. Substitua `/caminho/para/pitwall-lab` pelo caminho da pasta do projeto no seu computador (ela pode se chamar `F1` na máquina original). As aspas permitem caminhos com espaços. Não copie o caminho de exemplo literalmente.

```bash
cd "/caminho/para/pitwall-lab"
source .venv/bin/activate
python coletar_resultados.py
```

- `cd`: entra na pasta do projeto.
- `source .venv/bin/activate`: faz o Terminal usar o Python isolado. É preciso repetir a ativação ao abrir outro Terminal.
- `python coletar_resultados.py`: executa a coleta ou reutiliza as respostas já salvas.

Alternativa equivalente, sem ativação:

```bash
cd "/caminho/para/pitwall-lab"
./.venv/bin/python coletar_resultados.py
```

Para sair do ambiente ativado:

```bash
deactivate
```

O ambiente já foi criado nesta máquina. **Apenas se a pasta `.venv` não existir**, por exemplo em outra máquina, crie-a antes da ativação:

```bash
cd "/caminho/para/pitwall-lab"
python3 -m venv .venv
```

Não copie um ambiente virtual entre computadores: recrie-o. Como o projeto está no Dropbox, a pasta `.venv` pode ser sincronizada pelo Dropbox; o `.gitignore` só controla o Git, não a sincronização do Dropbox.

## Como funciona a coleta de São Paulo (etapa 1)

1. Consulta o calendário de 2024, com `limit=100`.
2. Procura uma única corrida cuja cidade seja São Paulo e cujo país seja Brazil. A comparação da cidade desconsidera acentos.
3. Lê `season` e `round` da resposta, em vez de presumir o número da etapa.
4. Usa esses identificadores para consultar `results`, os resultados da corrida principal, não da sprint.
5. Valida a estrutura de cada resposta, tanto da rede quanto do cache, antes de utilizá-la. Confere os tipos, campos necessários, temporada, rodada e quantidade de registros. Uma nova resposta só é gravada no cache depois dessa validação.
6. Ordena pela posição final e salva as cinco colunas no CSV, em UTF-8, separado por vírgulas.

Identificação obtida pela execução real:

- Nome: São Paulo Grand Prix.
- Data: 2024-11-03 (3 de novembro de 2024).
- Temporada: `2024`.
- Rodada: `21`.
- Identificador do circuito: `interlagos`.
- Registros recebidos: `20`.

Consultas utilizadas:

```text
https://api.jolpi.ca/ergast/f1/2024/?limit=100
https://api.jolpi.ca/ergast/f1/2024/21/results/?limit=100
```

O número `21` acima documenta a descoberta; o código não o fixa manualmente.

## Arquivos da etapa 1 — preservados

```text
F1/
├── .gitignore
├── .venv/                              # Python isolado; não versionar
├── README.md
├── coletar_resultados.py                # coleta e conversão
├── data/
│   ├── resultados_sao_paulo_2024.csv    # tabela para análise
│   └── raw/
│       ├── calendario_2024.json         # resposta original do calendário
│       └── resultados_sao_paulo_2024.json # resposta original dos resultados
├── gerar_grafico.py                     # gráfico estático a partir do CSV
├── reports/
│   ├── largada_vs_resultado_sp2024.html
│   └── largada_vs_resultado_sp2024.svg
└── tests/
    ├── test_coletar_resultados.py       # testes originais da coleta
    ├── test_gerar_grafico.py            # teste original do gráfico
    └── test_validacao_respostas.py      # regressões sem rede
```

JSON é o formato estruturado retornado pela API. Guardá-lo permite conferir de onde saiu cada valor do CSV. CSV é uma tabela em texto que pode ser aberta em planilhas ou lida por Python. Os arquivos públicos de dados não estão excluídos pelo `.gitignore`.

## Colunas do CSV de São Paulo

| Coluna | Significado | Campo de origem |
| --- | --- | --- |
| `piloto` | Nome e sobrenome do piloto conforme a API. | `Driver.givenName` + `Driver.familyName` |
| `equipe` | Nome da equipe naquela corrida, não necessariamente a equipe atual. | `Constructor.name` |
| `posicao_largada` | Posição no grid informada pela fonte; não é a posição da classificação de sábado. | `grid` |
| `posicao_final` | Posição numérica retornada pela API, em ordem crescente. | `position` |
| `status` | Situação do piloto ao final, mantida em inglês para preservar a fonte. | `status` |

Status presentes nesta resposta: `Finished` = terminou; `Retired` = abandonou; `Did not start` = não largou; `Disqualified` = desclassificado.

**Atenção:** a API também atribui posições numéricas aos registros de pilotos que não largaram ou foram desclassificados. Portanto, não interprete `posicao_final` sozinha como prova de que o piloto completou a prova. A largada de pilotos que não largaram também é preservada exatamente como a fonte a informa. Nenhum desses casos foi removido ou corrigido manualmente.

## Acesso responsável, cache e falhas

A documentação consultada informa limite sem autenticação de **4 requisições por segundo e 500 por hora**, sujeito a alterações. O aplicativo se identifica pelo cabeçalho `User-Agent`: `PitwallLab/0.1.0 Python/3.9.6 (educational portfolio; urllib)` nesta máquina (a versão do Python é preenchida automaticamente).

- Na primeira execução, são feitas duas consultas sequenciais, com pelo menos 8 segundos entre seus inícios.
- Nas seguintes, as respostas em `data/raw/` são validadas e, se válidas, reutilizadas sem regravação. Isso é um **cache**, uma cópia local para evitar downloads repetidos. Portanto, repetir o comando normalmente não consulta possíveis correções posteriores na API.
- O espaçamento controla este processo, não outros programas ou pessoas que usem o mesmo IP. Não execute múltiplas cópias simultaneamente.
- Cada consulta tem tempo limite de 30 segundos. Problemas de rede, HTTP, JSON ou estrutura de dados encerram a execução com mensagem de falha e código de saída 1, sem inventar resultados.
- Se ocorrer HTTP 429, o script informa `Retry-After`, quando enviado, e encerra sem nova tentativa automática. Aguarde o prazo indicado antes de tentar novamente. O valor pode indicar segundos ou uma data HTTP. Se não houver prazo, não repita em sequência.
- Conteúdo existente diferente não é sobrescrito. Conteúdo igual é mantido. Antes de qualquer atualização deliberada, mova os arquivos antigos para um backup fora dos caminhos usados pelo script.
- Para consultar a API novamente, com os arquivos atuais já guardados em backup, retire dos caminhos ativos os dois JSON de `data/raw/` e o CSV. Execute apenas uma vez. Não é necessário fazer isso no uso normal.
- Uma falha não apaga um CSV anterior: se a coleta falhar, não trate um CSV antigo como resultado de uma nova consulta.

### Respostas inválidas: o que é verificado

JSON é um formato de dados. Um JSON pode estar escrito corretamente e ainda assim não conter o que precisamos: `[]` é uma lista, não o objeto esperado; `{"MRData": {}}` é um objeto, mas está incompleto.

O programa aplica as **mesmas regras à rede e ao cache**, específicas para cada endpoint (tipo de consulta):

- **Em ambos:** JSON em UTF-8, objeto principal, `MRData`, `RaceTable`, temporada esperada, total numérico em texto e lista não vazia de corridas. Os elementos das listas também precisam ser objetos.
- **Calendário:** quantidade de corridas igual ao total; temporada e rodada de cada corrida; nome, data em texto, circuito e localização com cidade e país.
- **Resultados:** uma única corrida, temporada e rodada correspondentes à consulta, lista de resultados não vazia e quantidade igual ao total. Cada registro precisa conter nome e sobrenome do piloto, nome da equipe, grid, posição e status, com os tipos esperados.
- Campos textuais obrigatórios não podem estar vazios. Valores numéricos seguem o formato de texto com dígitos da API; o grid pode ser zero, enquanto rodada, posição e total precisam ser positivos.

Campos adicionais da fonte não são descartados dos JSON. A validação verifica a estrutura necessária para a coleta: ela não certifica a exatidão esportiva de cada valor.

Uma resposta inválida **da rede não cria cache para aquele endpoint**. Se outra resposta válida já tiver sido salva durante a execução, ela é preservada. JSON malformado, codificação inválida e estrutura inesperada são convertidos em mensagens claras. O programa escreve a falha no Terminal e termina com **código de saída 1**, o sinal que outros programas usam para reconhecer um erro.

Não usamos `except Exception` para esconder falhas. As validações geram um erro específico, `RespostaInvalida`, derivado de `ValueError`; a execução principal trata erros esperados de dados e de acesso a arquivos/rede (`ValueError` e `OSError`). Erros inesperados de programação, como `TypeError`, não são disfarçados como dados inválidos.

### Como recuperar um cache inválido sem perder dados válidos

Se um cache falhar na validação, a mensagem começa com **`Cache inválido`**, mostra o caminho do arquivo e explica o campo ausente ou incorreto. O arquivo é mantido intacto. O programa não o apaga, não o sobrescreve e não tenta baixá-lo novamente automaticamente.

1. Identifique **somente o arquivo indicado** pela mensagem.
2. Mova esse arquivo para um backup fora da pasta do projeto, preservando seu conteúdo para inspeção. Não mova os demais JSON válidos nem o CSV.
3. Execute novamente `./.venv/bin/python coletar_resultados.py`, dentro da pasta do projeto.
4. O JSON que agora estiver ausente será consultado novamente; os demais caches válidos continuarão a ser reutilizados. Aguarde os limites da API se houver uma mensagem HTTP 429.

Se a nova resposta ainda for inválida, o script voltará a falhar sem gravar aquele cache. Se uma nova coleta válida produzir um CSV diferente do já existente, a proteção contra sobrescrita continua valendo: faça um backup deliberado do CSV antes de aceitar a atualização. Não remova todos os dados para resolver um único cache defeituoso.

O `.gitignore` exclui o ambiente virtual, arquivos temporários Python, `.env` e padrões comuns de segredos. Ele não é um detector completo de credenciais e não protege arquivos que já estejam sendo rastreados pelo Git. Nunca coloque senhas ou tokens no código.

## Como verificar

Sem ativar o ambiente:

```bash
cd "/caminho/para/pitwall-lab"
./.venv/bin/python -m unittest discover -s tests -v
```

O teste de coleta executa o script e compara todas as células do CSV com a resposta JSON salva, além de conferir o cabeçalho, a quantidade e a ausência de pilotos duplicados. Na falta do cache, esse teste consulta a API real. Os outros dois testes simulam falhas HTTP 429 e 503 para verificar a mensagem de espera, a ausência de tentativas repetidas, a identificação do aplicativo e o tempo limite, sem criar dados de corrida fictícios e sem acessar a API.

Os quatro testes originais (incluindo o gráfico) foram mantidos. O arquivo `tests/test_validacao_respostas.py` acrescenta testes **sem rede**, com respostas simuladas e cópias temporárias das respostas reais. Eles cobrem `[]`, objetos incompletos, tipos incorretos, campos ausentes, totais e identificadores incoerentes, JSON malformado e UTF-8 inválido, tanto na rede quanto no cache. Também verificam que respostas inválidas não criam cache, que caches existentes são preservados, que dados válidos continuam aceitos e que erros de programação não são mascarados.

Há testes que executam o script inteiro em subprocessos isolados para conferir **saída 1, mensagem sem traceback para dados inválidos e preservação dos outros arquivos**. Eles também verificam que importar os testes históricos não altera `TMPDIR` nem `tempfile.tempdir`; os temporários seguem o diretório escolhido pelo executor. A rede nesses testes está bloqueada por simulação; os dados originais do projeto não são usados como destino de gravações inválidas.

Para executar apenas as novas regressões sem rede:

```bash
./.venv/bin/python -m unittest discover -s tests -p test_validacao_respostas.py -v
```

Para visualizar o CSV no Terminal:

```bash
cd "/caminho/para/pitwall-lab"
./.venv/bin/python -c 'from pathlib import Path; print(Path("data/resultados_sao_paulo_2024.csv").read_text(encoding="utf-8"))'
```

## Gráfico: largada versus resultado por piloto

O script `gerar_grafico.py` lê o CSV já existente, sem consultar a API e sem instalar bibliotecas. Ele gera uma imagem vetorial SVG e uma página HTML estática autocontida; não é um dashboard.

```bash
cd "/caminho/para/pitwall-lab"
./.venv/bin/python gerar_grafico.py
open reports/largada_vs_resultado_sp2024.html
```

Arquivos adicionais: `gerar_grafico.py`, `tests/test_gerar_grafico.py`, `reports/largada_vs_resultado_sp2024.svg` e `reports/largada_vs_resultado_sp2024.html`.

### Leitura

- Cada linha corresponde a um piloto; a ordem segue a posição final informada pela API.
- O eixo horizontal vai de 1 a 20: menor número, à esquerda, representa posição melhor.
- Círculo azul vazado: grid informado. Círculo verde cheio: resultado com status `Finished`.
- O saldo é `posicao_largada - posicao_final`, apenas para `Finished`. Positivo indica avanço entre as duas posições; negativo, recuo. Isso não conta ultrapassagens.
- Losangos âmbar indicam posições numéricas da API com status especial. Eles não recebem linha de comparação nem saldo: abandono, não largada e desclassificação não equivalem a uma chegada normal.

### Três observações verificáveis neste CSV

1. Max Verstappen passou de 17º para 1º: saldo de +16, o maior entre os pilotos com status `Finished`.
2. Nenhum dos três primeiros no resultado veio das três primeiras posições do grid informado: Verstappen (17º), Ocon (4º) e Gasly (13º).
3. Norris (1º para 6º) e Alonso (9º para 14º) tiveram saldo de −5, a maior queda entre os pilotos com status `Finished`.

Observação é algo que os dados permitem conferir. Hipótese é uma explicação a ser testada. Por exemplo: “a estratégia de paradas contribuiu para a recuperação de Verstappen” é uma hipótese, não uma conclusão deste CSV. Faltam dados de voltas, paradas e acontecimentos da corrida para investigar causas. Uma corrida isolada também não permite generalizar para a temporada.

### Cuidados com o status

Neste CSV há 15 `Finished`, 2 `Retired` (Sainz e Colapinto), 2 `Did not start` (Albon e Stroll) e 1 `Disqualified` (Hülkenberg). `Retired` não informa aqui o motivo específico do abandono; `Disqualified` também não informa o motivo da desclassificação.

Albon tem grid 7 e posição numérica 18, mas `Did not start`: não devemos dizer que largou em 7º e perdeu 11 posições na pista. Sainz tem grid 20 e posição numérica 16, mas `Retired`: a diferença aritmética não comprova quatro ultrapassagens nem que completou a corrida.

Preservamos todos os registros no gráfico. Para comparar mudanças de posição entre quem terminou, usamos apenas `Finished`, explicitando o filtro. Isso exclui casos importantes e pode gerar viés de seleção: não representa todo o pelotão nem uma medida pura de habilidade. Não elimine abandonos silenciosamente e não atribua suas causas a partir destes cinco campos.

O teste do gráfico confere os 20 pilotos e suas posições contra o CSV, distingue os marcadores por status e verifica que o CSV não foi alterado. Ele integra o mesmo comando de testes já documentado acima.

## Fontes oficiais consultadas

- Documentação geral e identificação do aplicativo: https://github.com/jolpica/jolpica-f1/blob/main/docs/README.md
- Limites de acesso: https://github.com/jolpica/jolpica-f1/blob/main/docs/rate_limits.md
- Calendário: https://github.com/jolpica/jolpica-f1/blob/main/docs/endpoints/races.md
- Resultados e campos: https://github.com/jolpica/jolpica-f1/blob/main/docs/endpoints/results.md
- Termos de uso: https://github.com/jolpica/jolpica-f1/blob/main/TERMS.md

Projeto educacional independente, sem vínculo oficial com a Fórmula 1. **Fonte dos dados: Jolpica-F1. Conforme seus termos, os dados são disponibilizados sob CC BY-NC-SA 4.0 (Atribuição–NãoComercial–CompartilhaIgual).** O CSV é uma conversão de formato e seleção de campos da resposta original, sem correção manual dos valores. Preserve a atribuição e a licença ao compartilhar os dados; usos comerciais exigem contato com a Jolpica-F1. Consulte os termos antes de outros usos.

## Como explicar esta etapa em uma entrevista

“Preparei um ambiente Python isolado e fiz uma coleta reproduzível de dados históricos. Descobri a rodada no calendário da API, guardei as respostas originais e converti os resultados para CSV. Identifiquei o aplicativo, reduzi consultas com cache e tratei falhas básicas. Conferi todos os valores do CSV contra a fonte. Ainda não construí um modelo preditivo.”
