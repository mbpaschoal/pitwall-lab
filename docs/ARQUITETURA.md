# Organização do código

Português · [English](en/ARCHITECTURE.md)

O [blueprint](BLUEPRINT.md) determina responsabilidades. A implementação usa um pacote Python importável, sem instalação adicional. `app.py` continua sendo o entrypoint do Streamlit; módulos pequenos na raiz encaminham os comandos antigos.

| Área | Implementação | Responsabilidade |
|---|---|---|
| Dashboard | `pitwall/dashboard/` | Composição, navegação e vistas do acervo. |
| Dados | `pitwall/data/` | Leitores, validação, projeção offline, aquisição serial e adjudicação. |
| Idiomas | `pitwall/i18n/` | Catálogo offline PT/EN e adaptação exclusiva de apresentação. |
| Pesquisa | `pitwall/research/` | Pesquisa retrospectiva v2 isolada, sem promoção do modelo. |
| Operação | `operacao2026/` | Snapshots, corte, estado e emissão de GPs. |
| Publicação | `pitwall/publishing/`, `publicacao/`, `exportar_dashboard.py` | Documentação allowlistada, templates e exportação portátil. |
| Revisão | `tests/`, `validar_blueprint.py`, `verificar_pacote.py` | Contratos, regressões, integridade e aceite no navegador. |
| Evidência científica | `data/`, `models/`, `reports/`, produtores v1 originais | Artefatos e scripts congelados, preservados nos caminhos originais. |

## Fluxo e limites

A aquisição é explícita e serial. A preparação offline gera assets. Leitores verificam schemas e identidades. A interface apresenta cópias locais; não coleta, treina ou infere durante a navegação. O exportador usa allowlist e distingue baseline científico de build de apresentação.

Os módulos da raiz com nome antigo existem para compatibilidade; não são implementações duplicadas. Novas mudanças devem ocorrer no pacote. A compatibilidade preserva imports usados pelos testes e por comandos existentes. Os scripts v1 congelados não foram movidos só para uniformizar a aparência das pastas: seus caminhos e hashes são parte da evidência.

## Tradução

`pitwall/i18n/en.json` contém os textos visíveis. Português é o padrão. O idioma é específico da sessão e persiste como `lang=pt|en` nos links. Valores canônicos de widgets, IDs, caminhos e URLs não são traduzidos. A camada `streamlit.py` adapta apenas argumentos de exibição e cópias de tabelas/gráficos; o Streamlit não recebe patches globais.

Documentos ingleses ficam em `docs/en/`; a seleção usa uma allowlist explícita. Downloads científicos conservam os bytes e identificadores originais, acompanhados de explicação em inglês. Downloads de tabelas descritivas seguem o idioma selecionado. Uma tradução nunca altera os dados-fonte nem a evidência de disponibilidade temporal.

## Como alterar

`fan_views.GP_CHAPTERS` conserva a ordem, os IDs canônicos e os rótulos dos seis capítulos do GP. Links e abas nativas usam essa mesma definição; a tradução ocorre na apresentação. As pontes locais de acessibilidade e movimento usam `st.iframe` em contêineres ocultos, com altura mínima válida de 1 px e `tab_index=-1`; gráficos Plotly usam `width="stretch"`, conforme o Streamlit fixado.

O produtor offline `pitwall/data/dashboard_projection.py` organiza a projeção do acervo em funções por domínio. `preparar()` confere fontes, resolve identidades, coordena sessões/voltas/clima/pneus/campeonatos, aplica histórico e complementos e valida a gravação. A interface continua consumindo o JSON produzido; esse produtor não integra o runtime portátil. A ordem das etapas faz parte do comportamento preservado.

Em Pilotos, `pilot_views._restore_navigation_state` aplica o estado salvo e os parâmetros de um link antes da composição visual. Um link já processado não restaura novamente os widgets; os critérios compartilhados preservam seu estado entre reruns de componentes. `PILOT_QUERY_KEYS` define a mesma ordem de parâmetros para ler e compartilhar a seleção.

Comece pelo contrato de papel no blueprint. Mantenha funções pequenas, nomes descritivos, dependências explícitas e testes no comportamento. Evite copiar implementações entre pacote, raiz e distribuição: o pacote portátil é gerado. Registre nova versão para cada entrega e teste o pacote isolado e o idioma afetado. Não faça descoberta irrestrita de testes para uma alteração de apresentação: ela pode executar ciência.

## Entrega 0.3.0

`pitwall/dashboard/model_views.py` concentra a avaliação do Lab; `pilot_views.py` compõe exploração, perfil e duelo. `driver_duel.py` calcula somente em largadas compartilhadas, sem dependências de interface. `search.py` busca entidades locais; `share_cards.py` exporta SVG sem recursos externos. O favorito usa o componente local em `frontend_assets/favorite/` e o armazenamento do navegador.

`distribuicao/pitwall-dashboard/` é gerado pela allowlist e não deve ser editado diretamente. O ZIP é anexado à release, evitando duplicar um binário grande em cada commit. O CI valida a árvore realmente servida. `validar_blueprint.py` pertence ao cofre local e não é requisito da instalação pública.


Pilotos mantém a base original e incorpora GPs posteriores em complemento validado por `pitwall/data/driver_updates.py`. O produtor descritivo `operacao2026/driver_archive.py` participa da coleta agendada e publica por allowlist atômica. Pendências conservam dados validados e acionam o monitor. [Contrato e limites](PILOTOS_ATUALIZACAO.md).

## Fronteiras verificadas na revisão 0.12.6

`pitwall/data/standings_state.py` resolve a publicação do campeonato: evento selecionado, corte do snapshot e estado da atualização são informações diferentes. Uma falha de refresh conserva o snapshot válido do mesmo evento com aviso e procedência; outro evento ou uma tabela incompleta não fornecem pontuações. As telas tratam indisponibilidade do leitor operacional sem perder os dados já validados.

Leitores JSON validam a raiz antes de acessar campos; erros de domínio orientam os consumidores. A busca reutiliza o leitor editorial. Fontes opcionais ausentes não viram caminhos de procedência. O cooldown de captura é persistido e verificado antes de qualquer nova consulta. Escritas de imagens são exclusivas e idempotentes por bytes; divergências preservam o arquivo anterior.

Na pesquisa isolada, timestamps exigem fuso explícito, destinos existentes são recusados e tabelas vazias mantêm esquema. Folds sem alvos conhecidos têm cobertura insuficiente, sem zero artificial; identidades duplicadas são rejeitadas antes do filtro de previsões disponíveis. Esses contratos são testados com exemplos sintéticos, sem promover a pesquisa ao v1.

Para revisar novamente: seguir um fluxo de entrada até saída, nomear o cenário de falha, demonstrá-lo num teste e corrigir a menor responsabilidade possível. A cobertura de leitura e a execução de testes são registros distintos. Inspeção sintática, teste local, CI, pacote e navegador público respondem a perguntas diferentes; nenhum substitui os demais. Os módulos de compatibilidade e a distribuição gerada não são candidatos a remoção só por parecerem duplicados.
