# Pitwall Lab

Created by: MBPaschoal
Status: active
Type: project context
Updated: 2026-10-18

## Objetivo

Aprender ciência de dados com Fórmula 1 e, futuramente, estimar probabilidades de pódio em um dashboard.

## Estado documentado

O [README](../README.md) registra a etapa 7: preparar uma distribuição mínima e independente do dashboard para futura hospedagem, **sem criar repositório público, mudar a visibilidade do atual ou publicar o aplicativo**. 2025 continua avaliação retrospectiva já realizada, nunca teste intocado novamente.

## Distribuição mínima — etapa 7

- Pasta de publicação: [distribuicao/pitwall-dashboard](../distribuicao/pitwall-dashboard/README.md). Ela não é o cofre nem uma cópia do repositório inteiro. [Inventário exato](../distribuicao/pitwall-dashboard/ARQUIVOS_PUBLICACAO.txt) e [manifesto de origem/hashes](../distribuicao/pitwall-dashboard/MANIFESTO.json).
- Receita por allowlist em [exportar_dashboard.py](../exportar_dashboard.py), com templates separados em `publicacao/`. Origem congelada dos artefatos: commit `05eec0b70b24abf9a68dae45aac36730eefb5bc5`; a receita nova tem hashes próprios, sem atribuí-la falsamente a esse commit.
- Nove CSV/JSON de apresentação, código, documentação necessária, atribuição, configuração de hospedagem, requisitos, testes e captura real. Cofre, sessões, credenciais, bases brutas, joblib, ambientes, backups e temporários não são arquivos de publicação.
- Documentação e relatórios aparecem na própria interface, sem depender de acesso ao repositório privado. A edição pública do relatório 2024 adapta somente links, com origem identificada; os nove CSV/JSON e os documentos copiados sem adaptação mantêm bytes.
- CPython 3.12.15 e ambiente de homologação novos e isolados, sem migrar a `.venv` científica. A distribuição não exige scikit-learn, SciPy ou joblib. Dados, modelo e relatórios anteriores permanecem congelados.
- `requirements.txt` próprio na raiz, Python 3.12 selecionado futuramente em Advanced settings do Community Cloud. Endereço/porta de hospedagem não fixados; comando local usa explicitamente `127.0.0.1`.
- Telemetria pedida como desligada no teste local; a documentação oficial informa sobreposição para ligada no Community Cloud. Execução na nuvem e em Linux não é certificada por um teste local macOS.
- Dados mantêm CC BY-NC-SA 4.0. Licença aberta do código ainda depende de escolha do autor; não se aplica MIT aos dados. Avaliar a finalidade pretendida e condições antes de publicar.
- **Preparação técnica concluída em 19/10/2026**, com **R3 aprovado com ressalvas** por `openai-codex/gpt-6-astra`. R1/R2 reprovaram respectivamente os aliases de `..` e de caixa; `openai-codex/gpt-5.6-terra` corrigiu os dois P2 com regressões RED/GREEN. Uso efetivo das revisões 20/13/13 chamadas principais conferido; os 59 arquivos da revisão final não foram alterados pelo revisor. Nenhuma publicação ou repositório público foi criado.
- Pós-correção: 13 testes exportador/hachuras, 30 do pacote isolado, aceite 48 GPs/3 telas/2 temporadas, três exportações/ZIP byte idênticos, nove contraprovas independentes de confinamento e Chromium real com seis documentos/download CSV aprovados. Os 68 SHA e nove versões originais permaneceram iguais. Sem treino/inferência/coletores/APIs de dados; a suíte científica antiga não foi repetida.
- Pareceres/limites em [distribuição e verificação](../docs/distribuicao_dashboard_v1.md) e [histórico independente](../reports/distribuicao_dashboard_v1/revisao_independente.json). Licença/adequação de uso, autorização de publicar e teste real Linux/Cloud continuam pendentes. A aprovação da etapa 6 não substituiu a revisão da etapa 7.

Comando de exportação na raiz: `./.venv/bin/python exportar_dashboard.py`. Para outro diretório novo: `./.venv/bin/python exportar_dashboard.py --destino /caminho/novo/pitwall-dashboard`. Destino divergente não é sobrescrito. A publicação futura deve começar por esse pacote, **fora do cofre e com histórico Git novo**, nunca tornando público o repositório atual.

## Estado histórico da etapa 6

O dashboard local em Streamlit e Plotly é somente leitura e explora resultados já calculados de 2024 e 2025. Não carrega modelo, não faz inferência, treinamento ou consultas a dados e não foi publicado.

## Dashboard local — etapa 6, 2026-10-18

- [Contrato de dados](../docs/contrato_dashboard_v1.md) registrado antes da interface; [68 hashes de artefatos preservados](../docs/dashboard_artefatos_preservados.json). A modificação preexistente deste contexto, incluindo a revisão do Codex da etapa 5, foi preservada.
- `app.py` separa apresentação e gráficos de `dashboard_dados.py`, responsável por carregamento e validação. São nove CSV/JSON de resultados nas duas temporadas; não se lê `data/` ou joblib no fluxo do aplicativo.
- Telas **Explorar um GP**, **Desempenho** e **Como funciona**. Filtro de temporada nas telas; GP aplicado somente à exploração. Probabilidades do modelo e referência de classificação são visualmente separadas dos resultados posteriores.
- 2025 mantém 478 casos probabilísticos e 22 dos 24 GPs nos rankings. Espanha e São Paulo são N/A, com motivos; integrantes conhecidos podem ser mostrados sem pontuar o GP incompleto e sem inventar ordem.
- A suíte completa teve 129 aprovados antes da primeira revisão forte. O Astra encontrou três P2 de validação em cópias temporárias, sem divergência nos artefatos reais. Foram corrigidos por `openai-codex/gpt-5.6-terra`, com seis regressões RED/GREEN; 26 testes de dashboard passaram depois. A suíte antiga não foi repetida porque contém testes que executam coletor com cache e modelo real sobre dados sintéticos. Aceite restrito em AppTest percorreu novamente 48 GPs e as três telas para ambas as temporadas, conferindo favoritos contra os ranks publicados e invariância aos alvos.
- Revisão independente concluída: R1 e R2 por **`openai-codex/gpt-6-astra`**, com 10 e 12 chamadas principais efetivamente confirmadas no banco. R1 reprovou três P2; Terra corrigiu, e R2 aprovou sem remanescentes, com 26 testes de dashboard, contraprovas e três capturas reais inspecionadas. Os 19 arquivos de entrega não foram alterados pelo revisor. [Pareceres preservados](../reports/dashboard_v1/revisao_independente.json).
- Cache por bytes, somente em memória. Testes reais de AppTest alteraram uma cópia temporária mantendo o `mtime` e removeram um arquivo: apareceram erros úteis, não dados antigos do cache. Nenhum artefato real foi modificado.
- Inspeção real em Chromium isolado, desktop de 1440 px e viewport de 390 px: nenhum erro de página, nenhuma solicitação externa; sem transbordamento horizontal no documento mobile. [Capturas reais e evidências](../reports/dashboard_v1/verificacao.md).
- Dependências adicionais em `requirements_dashboard.txt`, com restrições da pilha científica existente. As cinco versões científicas e os 68 hashes permaneceram iguais. Instalações apenas nos ambientes isolados, sem alteração global de pacotes.
- A configuração dos modelos do Hermes não foi editada pela tarefa. O hash global do arquivo de configuração variou durante a sessão; não se atribui preservação byte a byte desse arquivo a todo o período nem se restaura uma possível alteração externa. A identidade efetiva dos agentes é verificada pelos registros de uso.

Iniciar na raiz: `./.venv/bin/python -m streamlit run app.py`. Abrir `http://127.0.0.1:8501`; servidor limitado à própria máquina e telemetria desativada. O código poderá ser versionado no repositório privado, mas isso não constitui hospedagem ou publicação do aplicativo. Não há cenários “e se”, login, chatbot, edição de dados ou previsão ao vivo.

Os registros seguintes descrevem as etapas anteriores e mantêm seu contexto histórico.

## Revisão do Codex da etapa 6 — 2026-10-18

Revisado o commit [05eec0b](https://github.com/mbpaschoal/pitwall-lab/commit/05eec0b70b24abf9a68dae45aac36730eefb5bc5), identificado pelo conector GitHub e correspondente ao HEAD local. A consulta de metadados confirmou que o repositório permanece privado.

- Os 26 testes específicos de dashboard passaram; a suíte completa da versão corrigida também foi executada nesta revisão: 135 testes aprovados. Essa execução posterior não altera os registros históricos da rodada anterior de QA.
- `pip check` não encontrou dependências quebradas. Os 68 hashes de artefatos preservados conferem, sem divergências.
- O código separa carregamento/validação e apresentação; os testes AppTest percorrem os GPs e as três telas, verificando cobertura e mensagens de erro. Foi inspecionada a captura desktop de desempenho já preservada; esta revisão não produziu nova sessão visual em navegador.
- Nenhum problema bloqueante encontrado para o escopo local. Não houve alteração de código, dados, modelo ou relatórios científicos.

Proposta seguinte: preparar uma distribuição mínima e revisável para hospedagem gratuita, com dependências reconhecidas pelo Streamlit Community Cloud e ambiente separado em Python suportado. Não mudar a visibilidade deste repositório/cofre nem publicar automaticamente. A lista de arquivos exportados deve ser explícita e incluir apenas aplicativo, artefatos necessários, metodologia e atribuição.

Referências oficiais consultadas nesta revisão: [dependências](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies) e [implantação e versão de Python](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy). A pilha científica local deve permanecer preservada; a distribuição pública ainda não foi testada nem publicada.

## Avaliação final congelada — etapa 5, 2026-10-18

- O [plano final](../docs/avaliacao_final_v1.md) foi registrado antes de abrir o teste. SHA-256: `7b67a47d1136dc02bc24236dfbf6acb8e9e4e646a6d9cb68cba09a4fc6da8983`. Modelo, metadados, plano v1 e treinador mantiveram seus bytes.
- O script `avaliar_modelo_v1.py` usa exclusivamente teste e esquema como fontes de dados; faz inferência com o pipeline local salvo, sem `fit`, `fit_transform`, `partial_fit`, recalibração ou escolhas orientadas pelo teste.
- 480 registros de piloto por GP preparados; 479 receberam previsão; 478 elegíveis com alvo conhecido entraram nas métricas probabilísticas. Os rankings compartilham **22 dos 24 GPs**, sem atribuir zero aos dois excluídos.
- Espanha/rodada 9: alvo de `stroll` desconhecido, mas previsão gerada. São Paulo/rodada 21: `bortoleto` inelegível por classificação ausente na base. São fatos da fotografia preparada; não foram investigadas causas com novas consultas.
- Modelo: log loss 0,2033 e Brier 0,0585, ante 0,4238 e 0,1279 da constante congelada. Ranking: média 2,3182 contra 2,2727 da classificação; ambos acertaram os três integrantes em 8/22 GPs (36,36%). A vantagem média é pequena; houve empate nos pódios completos.
- As três execuções reais produziram os mesmos onze artefatos. Guardas registraram zero chamadas de ajuste e zero rede; o estado em memória de três pipelines e 16 arquivos congelados permaneceu igual. Um oráculo separado, sem retreinar nem importar o avaliador, reconstruiu probabilidades a partir dos parâmetros salvos e conferiu métricas, calibração e rankings.
- Os 109 testes passaram antes da abertura real de 2025, incluindo dados sintéticos de teste para invariância a alvos, cobertura incompleta, períodos incorretos, ausência de ajuste e proteção contra sobrescrita.
- [Resultados e limites](../reports/avaliacao_final_v1/relatorio.md), [métricas](../reports/avaliacao_final_v1/metricas.json), [comparação descritiva com 2024](../reports/avaliacao_final_v1/comparacao_2024.json), [cobertura por GP](../reports/avaliacao_final_v1/cobertura_gps.csv) e [manifesto](../reports/avaliacao_final_v1/manifesto.json).
- [Revisão independente da etapa 5](../reports/revisao_final_v1.md): aprovada por `openai-codex/gpt-6-astra`, com identidade efetiva verificada no registro de uso; 109 testes sem falhas, contraprovas e duas reproduções adicionais. Implementação por `openai-codex/gpt-5.6-terra`. Nenhum bloqueio encontrado; nenhuma mudança metodológica após observar 2025.

A comparação com 2024 usa temporadas e denominadores distintos; não sustenta significância estatística, causalidade ou superioridade futura. Permanecem a dependência entre participantes do mesmo GP, o pequeno número de temporadas e as revisões retrospectivas das fontes. Os registros abaixo descrevem períodos anteriores, quando 2025 ainda estava reservado.

## Revisão do Codex da etapa 5 — 2026-10-18

Revisado o commit [9559c33](https://github.com/mbpaschoal/pitwall-lab/commit/9559c33d331176fe2a749bb73020194d8de20cf6), identificado pelo conector GitHub e correspondente ao HEAD local. Nenhum problema bloqueante encontrado no escopo da avaliação final retrospectiva v1.

- Os 109 testes passaram. O diff entre as etapas 4 e 5 preserva modelo, metadados, treinador, requisitos, plano v1 e relatórios da etapa 4.
- Duas reproduções em pasta temporária geraram os onze artefatos publicados, byte a byte. A rede e os métodos de ajuste dos estágios do pipeline foram bloqueados; dentro de `data/`, somente teste e esquema foram lidos. Quinze arquivos anteriores conferidos permaneceram iguais durante a auditoria.
- Uma conferência independente, sem usar `predict_proba` para reconstruir probabilidades, aplicou os parâmetros salvos às entradas de teste. Probabilidades, log loss, Brier, calibração por faixa, favoritos e rankings coincidiram com os resultados publicados.
- Confirmados 480 registros preparados, 479 previsões e 478 casos probabilísticos; os rankings usam os mesmos 22 GPs, excluindo rodadas 9 e 21 pelos motivos de cobertura já documentados.
- O modelo identificou 51 integrantes de pódio contra 50 da classificação e ambos acertaram os três integrantes em 8/22 GPs. A vantagem de ranking é pequena. Não há afirmação de significância estatística ou superioridade futura.

**Registro histórico da etapa 5 — proposta executada na etapa 6:** construir um dashboard que apresente o estudo retrospectivo, previsões calculadas, referências, cobertura e limitações. Isso não autoriza reajustar o modelo nem voltar a tratar 2025 como teste intocado. A revisão da etapa 5 verificou consistência dos registros e hashes; não certifica externamente a cronologia histórica de todo acesso anterior aos dados. Não alterou código, dados ou artefatos da avaliação.

## Execução verificada da etapa 4 — 2026-10-18

- O [plano fixado antes do treino](../docs/experimento_modelo_v1.md) teve SHA-256 `d6c671526aafe1ca8a1a6b98934a1d1915eb7a102872d51e5385991257fec569` registrado antes do primeiro ajuste.
- A rotina leu somente `treino.csv`, `validacao.csv` e `colunas.json`; não abriu nem avaliou 2025, não chamou API e não executou coletores/preparador.
- Foram ajustadas 1.319 linhas elegíveis e rotuladas de treino. Em 2024, as 479 linhas e os 24 GPs ficaram cobertos e avaliáveis pelas regras fixadas.
- O modelo teve log loss 0,2296 e Brier 0,0709, ante 0,4233 e 0,1277 da constante de treino. No top 3, obteve média 1,96 e 6/24 GPs com os três integrantes, contra 1,88 e 4/24 para o ranking da classificação. As diferenças da troca numérica ficaram nos últimos dígitos e não alteraram conclusões.
- Os 100 testes passaram, incluindo as duas regressões geométricas do gráfico de calibração e a contraprova simulada de multiplicação matricial, avisos numéricos como erro no ajuste/previsão, abertura exclusiva das três fontes permitidas, isolamento treino/validação, colunas proibidas, alvo desconhecido, cobertura parcial, bloqueio de 2025/rede, reprodutibilidade e proteção contra sobrescrita.
- As duas execuções reais seguidas com `numpy==1.26.4` geraram bytes idênticos para os dez artefatos de `models/modelo_v1/` e `reports/modelo_v1/`, sem `RuntimeWarning` nem `ConvergenceWarning`.
- A fotografia anterior de `models/modelo_v1/` e `reports/modelo_v1/` foi movida explicitamente, com hashes conferidos antes e depois, para backup único fora do repositório antes da regeneração autorizada.
- O bloqueio numérico foi resolvido ao fixar `numpy==1.26.4`: a contraprova simulada com a fotografia anterior 2.0.2 emitia `RuntimeWarning` em multiplicação matricial; com 1.26.4 não emitiu. Isso documenta uma incompatibilidade observada nesta máquina, não uma afirmação sobre a causa interna do BLAS. O código agora converte `RuntimeWarning` em erro no ajuste e na previsão, sem ocultá-lo.

Os resultados de 2024 são retrospectivos e de desenvolvimento: não provam generalização para 2025. Coeficientes e probabilidades não recebem interpretação causal; as limitações de revisões retrospectivas, pequena janela temporal e dependência entre pilotos do mesmo GP permanecem.

## Revisão do Codex da etapa 4 — 2026-10-18

Revisado o commit [9a3b7b8](https://github.com/mbpaschoal/pitwall-lab/commit/9a3b7b832334888af799e981cd173f26339c28d2), identificado pelo conector GitHub e correspondente ao HEAD local. Nenhum problema bloqueante encontrado no escopo do experimento v1.

- Os 100 testes passaram e `pip check` não encontrou dependências quebradas.
- Duas reproduções do experimento em pasta temporária geraram os mesmos dez artefatos publicados, byte a byte. Uma guarda de abertura de arquivos permitiu somente `treino.csv`, `validacao.csv` e `colunas.json` dentro de `data/`; a rede foi bloqueada. Não foram abertos dados reais de 2025.
- Uma implementação de conferência separada recalculou medianas, médias e escalas das 1.319 linhas elegíveis e rotuladas de treino e as 479 probabilidades de validação a partir dos coeficientes. Log loss, Brier, rankings e contagens coincidiram com os relatórios.
- O ranking identificou 47 integrantes de pódio contra 45 da referência de classificação nos mesmos 24 GPs. A vantagem é pequena e não foi apresentada como evidência de significância ou generalização.

**Registro histórico da etapa 4, proposta agora executada na etapa 5:** congelar o experimento v1 e suas regras, definir o tratamento de cobertura/alvos desconhecidos da avaliação final antes de consultar seus resultados e então avaliar o teste reservado sem reajuste orientado por ele. Manter explícita a natureza retrospectiva. A revisão da etapa 4 não alterou código, dados ou artefatos do modelo.

## Revisão verificada da etapa 3 em 2026-10-18

O commit [467fc19](https://github.com/mbpaschoal/pitwall-lab/commit/467fc19d74a090db73634f3db89132f6557a9f75) foi identificado pelo conector GitHub e correspondia ao HEAD local naquela revisão da etapa 3, sem diferenças nos arquivos rastreados na conferência inicial.

- Os 82 testes passaram no ambiente virtual existente.
- A preparação foi executada offline com saídas em pasta temporária: 19 artefatos idênticos aos publicados, incluindo o comprovante.
- Uma conferência independente dos JSON originais recalculou as posições de classificação, médias, contadores e IDs das janelas das 2.279 linhas, sem divergências. Foram conferidos 120 hashes de fontes e 18 hashes de saídas.
- A base contém 114 corridas; 1.320 linhas de treino (2021–2023), 479 de validação (2024) e 480 de teste reservado (2025). Essas são contagens de integridade, não métricas de previsão.
- Não foram executadas consultas à API, treinamento ou avaliação de desempenho em 2025.

Conclusão da revisão: nenhum problema bloqueante encontrado para encerrar a preparação histórica. Antes de treinar, definir elegibilidade dos participantes, tratamento de entradas ausentes e posições de classificação ambíguas; manter alvos desconhecidos distintos de negativos. Congelar essas regras antes da avaliação final. As limitações sobre revisões históricas e o horário de encerramento desconhecido continuam válidas, conforme o [protocolo](../docs/protocolo_temporal.md).

## Decisões e restrições

- Preservar as entregas das etapas anteriores.
- Preparar dados offline a partir de fontes validadas e caches completos.
- Separar entradas, identificação, alvos e desfechos de auditoria.
- Usar apenas informações anteriores ao corte temporal e registrar suas limitações.
- Tratar ausências explicitamente, sem convertê-las automaticamente em desempenho zero.
- Não substituir saídas diferentes sem preservar backup explícito, conforme o README.

## Próximas ações

1. Interpretar a [avaliação final v1](../reports/avaliacao_final_v1/relatorio.md) junto da cobertura por GP, sem extrapolar os 22 GPs avaliáveis para os 24.
2. Registrar dúvidas e hipóteses em `inbox/` e `ideas/`, com fontes.
3. Qualquer versão futura precisa de novo plano e avaliação honesta: 2025 já foi observado e não é mais teste intocado. Não ajustar o v1 nesta tarefa.

## Fontes

- [[notes/Pitwall Lab - Index]]
- [Protocolo temporal](../docs/protocolo_temporal.md)
- [Dicionário de variáveis](../docs/dicionario_variaveis.md)
- [Relatório de qualidade](../reports/historico/qualidade.md)
- [Relatório do modelo v1](../reports/modelo_v1/relatorio.md)
