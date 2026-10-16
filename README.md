# Pitwall Lab

Portfólio de ciência de dados sobre Fórmula 1, construído passo a passo para aprendizado.

## Objetivo

No futuro: criar um dashboard que estime a probabilidade de cada piloto terminar uma corrida no pódio.

**Etapa atual:** obter os resultados do GP de São Paulo de 2024 pela API gratuita Jolpica-F1 e salvar um CSV verificável. Não há modelo de machine learning, previsão ou dashboard nesta etapa. Uma única corrida não basta para treinar uma previsão confiável.

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

## Como a coleta funciona

1. Consulta o calendário de 2024, com `limit=100`.
2. Procura uma única corrida cuja cidade seja São Paulo e cujo país seja Brazil. A comparação da cidade desconsidera acentos.
3. Lê `season` e `round` da resposta, em vez de presumir o número da etapa.
4. Usa esses identificadores para consultar `results`, os resultados da corrida principal, não da sprint.
5. Confere se os resultados pertencem à temporada e rodada descobertas e se a quantidade recebida corresponde ao total informado pela API.
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

## Arquivos

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
└── tests/
    └── test_coletar_resultados.py       # verificações automáticas
```

JSON é o formato estruturado retornado pela API. Guardá-lo permite conferir de onde saiu cada valor do CSV. CSV é uma tabela em texto que pode ser aberta em planilhas ou lida por Python. Os arquivos públicos de dados não estão excluídos pelo `.gitignore`.

## Colunas do CSV

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
- Nas seguintes, as respostas em `data/raw/` são reutilizadas. Isso é um **cache**, uma cópia local para evitar downloads repetidos. Portanto, repetir o comando normalmente não consulta possíveis correções posteriores na API.
- O espaçamento controla este processo, não outros programas ou pessoas que usem o mesmo IP. Não execute múltiplas cópias simultaneamente.
- Cada consulta tem tempo limite de 30 segundos. Problemas de rede, HTTP, JSON ou estrutura de dados encerram a execução com mensagem de falha e código de saída 1, sem inventar resultados.
- Se ocorrer HTTP 429, o script informa `Retry-After`, quando enviado, e encerra sem nova tentativa automática. Aguarde o prazo indicado antes de tentar novamente. O valor pode indicar segundos ou uma data HTTP. Se não houver prazo, não repita em sequência.
- Conteúdo existente diferente não é sobrescrito. Conteúdo igual é mantido. Antes de qualquer atualização deliberada, mova os arquivos antigos para um backup fora dos caminhos usados pelo script.
- Para consultar a API novamente, com os arquivos atuais já guardados em backup, retire dos caminhos ativos os dois JSON de `data/raw/` e o CSV. Execute apenas uma vez. Não é necessário fazer isso no uso normal.
- Uma falha não apaga um CSV anterior: se a coleta falhar, não trate um CSV antigo como resultado de uma nova consulta.

O `.gitignore` exclui o ambiente virtual, arquivos temporários Python, `.env` e padrões comuns de segredos. Ele não é um detector completo de credenciais e não protege arquivos que já estejam sendo rastreados pelo Git. Nunca coloque senhas ou tokens no código.

## Como verificar

Sem ativar o ambiente:

```bash
cd "/caminho/para/pitwall-lab"
./.venv/bin/python -m unittest discover -s tests -v
```

O teste de coleta executa o script e compara todas as células do CSV com a resposta JSON salva, além de conferir o cabeçalho, a quantidade e a ausência de pilotos duplicados. Na falta do cache, esse teste consulta a API real. Os outros dois testes simulam falhas HTTP 429 e 503 para verificar a mensagem de espera, a ausência de tentativas repetidas, a identificação do aplicativo e o tempo limite, sem criar dados de corrida fictícios e sem acessar a API.

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
