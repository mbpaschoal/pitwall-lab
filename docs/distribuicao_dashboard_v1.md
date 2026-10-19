# Etapa 7 — distribuição mínima do dashboard

## Escopo e limites

Preparar uma distribuição autossuficiente para revisão e futura hospedagem gratuita. Não criar repositório público, não alterar a visibilidade do repositório/cofre e não publicar o aplicativo. O aplicativo local da etapa 6 e seu ambiente Python 3.9.6 permanecem separados.

Commit-base dos artefatos e código do dashboard: `05eec0b70b24abf9a68dae45aac36730eefb5bc5`. A receita nova tem hashes próprios; não se atribui ao commit-base a autoria de templates que surgiram nesta etapa. O manifesto da exportação deve distinguir esses insumos, as cópias byte a byte e adaptações documentais.

## Fontes científicas permitidas — exatamente nove CSV/JSON

1. `reports/modelo_v1/previsoes_validacao.csv`
2. `reports/modelo_v1/avaliacao_corridas.csv`
3. `reports/modelo_v1/metricas.json`
4. `reports/modelo_v1/calibracao.csv`
5. `reports/avaliacao_final_v1/previsoes_pre_corrida.csv`
6. `reports/avaliacao_final_v1/avaliacao_por_piloto.csv`
7. `reports/avaliacao_final_v1/avaliacao_corridas.csv`
8. `reports/avaliacao_final_v1/metricas.json`
9. `reports/avaliacao_final_v1/calibracao.csv`

Não incluir bases brutas, joblib, treinadores, avaliadores, coletores, cofre, notas de sessão, credenciais, ambientes, backups ou temporários. Documentação selecionada e código de apresentação têm sua própria allowlist. Uma eventual edição pública do relatório de 2024 pode adaptar somente links para arquivos não distribuídos, deve identificar a adaptação e nunca substituir o relatório científico original.

Os bytes das nove fontes são preservados. 2024 continua validação já explorada; 2025 é avaliação retrospectiva já realizada, com 478 casos probabilísticos e 22 dos 24 GPs nos rankings. Ausências não viram zeros e não se estima novamente nenhuma probabilidade.

## Ambiente e Community Cloud

A documentação oficial consultada nesta preparação identifica Python 3.12 como padrão atual e permite escolher a versão em **Advanced settings** durante a criação do aplicativo. O arquivo `.python-version` da distribuição registra a intenção local; não substitui essa seleção na plataforma.[1]

A distribuição usa somente um `requirements.txt` na raiz do aplicativo, sem depender do arquivo científico externo. A documentação recomenda essa organização e explica a precedência dos arquivos de dependências.[2]

Homologação local em novo CPython 3.12.15 isolado, instalado sem substituir o Python existente. Dependências candidatas já instaladas com `pip check` aprovado: Streamlit 1.50.0, Plotly 6.3.1, pandas 2.2.3, PyArrow 20.0.0, NumPy 1.26.4 e protobuf 5.29.5. NumPy/protobuf são dependências reais da pilha de apresentação. O novo ambiente não contém scikit-learn, SciPy ou joblib. Instalação não é aprovação de execução: testes e navegador são etapas separadas, com resultados registrados abaixo quando concluídos.

A configuração exportada não fixa endereço nem porta de hospedagem. O comando de uso local deve informar `--server.address 127.0.0.1`; testes paralelos usam outra porta local, sem parar a versão original.

`gatherUsageStats=false` é mantido no arquivo exportado e desativa a estatística de uso no teste local.[6] **Não se promete telemetria desligada no Community Cloud:** a documentação informa que a plataforma sobrepõe essa configuração com `gatherUsageStats=true`.[3] Nenhuma configuração de conta, nuvem ou Hermes é alterada por esta preparação.

A plataforma executa em Linux; os testes desta máquina são em macOS. A execução real na nuvem, seus recursos, versão de correção do Python e tráfego da própria plataforma só poderão ser verificados depois de uma autorização de publicação.[2][3]

## Fontes, dados e licença do código

Os termos oficiais da Jolpica identificam os dados como **CC BY-NC-SA 4.0**, com uso não comercial e contato para usos comerciais.[4] Devem ser preservados crédito, link da licença, identificação das transformações e compartilhamento sob as mesmas condições nos direitos aplicáveis. A licença não garante todos os direitos que um uso específico possa exigir.[5]

A distribuição diferencia essas condições dos direitos sobre o código. Não foi escolhida ou concedida uma licença aberta nova para o código nesta tarefa; essa é uma decisão do autor antes de publicar. Não aplicar MIT, Apache ou outra licença permissiva aos dados por associação com os arquivos Python. Hospedagem gratuita não autoriza automaticamente finalidade comercial ou qualquer uso profissional; o autor deverá verificar seu uso pretendido e, se necessário, consultar a fonte.[4][5]

## Verificação exigida antes da entrega

- Exportação por allowlist, determinismo, recusa a sobrescrita divergente, ausência de caminhos pessoais e arquivos alheios.
- Manifesto e inventário completo conferidos por código, sem incluir o próprio hash do manifesto.
- Instalação e execução dos testes pertinentes no novo Python, em uma pasta exportada independente.
- Guardas impedindo leitura do projeto original, dados/modelos, rede externa e escrita no pacote durante o aceite da interface.
- Três telas, duas temporadas, todos os GPs, métricas e N/A; metodologia e relatórios acessíveis sem conta no repositório privado.
- Navegador real quando disponível e limitações de inspeção declaradas.
- Comparação final dos 68 hashes e das versões/configurações originais; preservar a modificação preexistente do Codex no contexto.
- Commit apenas dos arquivos desta etapa no repositório privado, com leitura de volta do remoto; nenhum deploy.

## Resultado técnico antes da revisão independente

Critérios técnicos concluídos antes de solicitar o revisor forte. A distribuição contém **32 arquivos**, incluindo exatamente **nove CSV/JSON científicos**. Três exportações completas — a pasta versionada e duas novas pastas fora do projeto — produziram os mesmos bytes. Destino idêntico é idempotente; divergente é recusado sem sobrescrita. [Inventário exato](../distribuicao/pitwall-dashboard/ARQUIVOS_PUBLICACAO.txt) e [manifesto](../distribuicao/pitwall-dashboard/MANIFESTO.json).

Resultados efetivamente executados pelo agente principal, não soma de fases:

| Verificação | Ambiente/escopo | Resultado |
|---|---|---|
| Baseline anterior às alterações | Python 3.9.6 original, apenas dashboard | 26 testes aprovados |
| Exportador e hachuras | Python 3.12.15, dois módulos novos | 11 testes aprovados |
| Pacote independente | Python 3.12.15, somente testes exportados | 30 testes aprovados; zero falhas/erros |
| Aceite de apresentação | AppTest com projeto original inacessível | 48 GPs, três telas e duas temporadas |
| Cache | Cópias temporárias, bytes alterados mantendo mtime e arquivo removido | Sem métricas antigas após erro |
| Fontes e isolamento | Guardas de leitura/importação/rede/escrita | Somente nove relatórios de dados; sem acesso ao projeto original, modelo, rede externa ou escrita no pacote |
| Browser real | Chromium isolado 140.0.7339.16; desktop e 390 px | Zero erros de página e requisições externas; largura 390/390 |
| Documentação offline | Seis documentos, navegação real | Todos abertos; CSV de 2024 baixado e SHA conferido |
| Dependências | Novo ambiente, requisitos próprios | `pip check` aprovado; sem scikit-learn, SciPy ou joblib |
| Preservação | Fontes originais e ambiente | 68 SHA idênticos; nove versões relevantes originais iguais; app, loader, configuração e requisitos locais intactos |

O aceite e os testes do pacote foram executados com guardas que impedem leitura/listagem do projeto original, importação científica, rede e gravação no pacote. Fixtures inválidas e simulações de `.git`, `.venv` e `.env` ficam em diretórios temporários próprios. Não se repetiu a suíte antiga com coletores/modelo: esses testes não pertencem ao escopo autorizado.

O servidor de homologação foi iniciado de fato em `127.0.0.1:8502`, numa cópia independente, com HOME limpo e sem herdar credenciais da sessão. Não foi exposto em endereço público. A configuração local da etapa 6, em `127.0.0.1:8501`, não foi alterada.

### Correções anteriores ao revisor

Implementação/correções por **openai-codex/gpt-5.6-terra**, com identidades efetivas conferidas no banco de uso. A primeira execução foi interrompida por HTTP 429; não recebeu aprovação, e os efeitos parciais foram conferidos antes de retomar em sessões novas. O [registro estruturado](../reports/distribuicao_dashboard_v1/verificacao.json) identifica cada sessão e suas chamadas principais, sem confundir auxiliares com autoria.

- Inventário passa a distinguir arquivos de publicação de diretórios locais de Git/venv/cache. Qualquer arquivo extra, inclusive `.env`, continua detectado.
- A própria simulação de `.env` nos testes foi isolada em `TemporaryDirectory`: não pode sobrescrever/apagar credenciais de um checkout real. A guarda detectou a tentativa no teste anterior e a regressão passou após correção.
- Exportador recusa ancestrais symlink que poderiam desviar a pasta de destino; teste de validação não cria diretórios no cofre.
- Timestamp de referência convertido corretamente para UTC, sem usar relógio da exportação; hash do relatório adaptado calculado da origem, não constante manual.
- Corrigida **apenas na cópia distribuída** a hachura de barras favoritas: antes o padrão transparente sobre o fundo escondia três barras. Fundo ciano e `overlay` as tornam visíveis. Teste compara x/y, ordem, hover e valores com a função original: inalterados. O app local original não foi editado.
- Metodologia/relatórios acessíveis pelo seletor offline; aviso identifica os planos como históricos e 2025 como já avaliado. Guia fornece comandos de exportação, novo histórico Git, seleção explícita de arquivos e configuração futura da plataforma.

Não houve mudança metodológica nem alteração em probabilidades, scores, cobertura, elegibilidade ou rankings científicos.

### Limites de homologação e publicação

- Não houve deploy nem criação de repositório público. A execução em Community Cloud/Linux e seus recursos só poderão ser confirmados após autorização futura. Docker CLI não está instalado nesta máquina; não se instalou ferramenta global para simular isso.
- Capturas reais em [evidências de navegador](../reports/distribuicao_dashboard_v1/): desempenho, calibração, documentos offline, GP N/A, mobile superior e gráfico mobile. Foram inspecionados o seletor/aviso histórico, denominadores, legenda e barras favoritas. Não se certificam todos os navegadores, aparelhos ou critérios de acessibilidade; tabelas extensas não aparecem inteiras em um viewport.
- Avisos `missing ScriptRunContext` do modo bare do AppTest foram registrados; não são erros de página do navegador.
- Hospedagem gratuita não elimina condições NC/SA, nem garante telemetria desligada na plataforma. A licença aberta do código permanece para escolha expressa do autor.
- Ainda restam: aprovar o pacote e condições de uso/licença; exportar/copiar somente o inventário para fora do cofre; criar novo repositório público com histórico novo; configurar Community Cloud com Python 3.12; só então testar o deploy real e registrar seu URL verdadeiro.

### Lista completa destinada à publicação

Somente os arquivos abaixo, relativos a `distribuicao/pitwall-dashboard/`. Receita, cofre, contexto, auditorias e imagens adicionais de QA do repositório privado não fazem parte desta lista:

```text
.gitignore
.python-version
.streamlit/config.toml
ARQUIVOS_PUBLICACAO.txt
FONTES_E_DADOS.md
GUIA_HOSPEDAGEM.md
LICENCA_CODIGO.md
MANIFESTO.json
README.md
app.py
dashboard_dados.py
docs/avaliacao_final_v1.md
docs/dicionario_variaveis.md
docs/experimento_modelo_v1.md
docs/protocolo_temporal.md
docs/relatorio_2024.md
documentacao_local.py
reports/avaliacao_final_v1/avaliacao_corridas.csv
reports/avaliacao_final_v1/avaliacao_por_piloto.csv
reports/avaliacao_final_v1/calibracao.csv
reports/avaliacao_final_v1/metricas.json
reports/avaliacao_final_v1/previsoes_pre_corrida.csv
reports/avaliacao_final_v1/relatorio.md
reports/dashboard_v1/desempenho_desktop.png
reports/modelo_v1/avaliacao_corridas.csv
reports/modelo_v1/calibracao.csv
reports/modelo_v1/metricas.json
reports/modelo_v1/previsoes_validacao.csv
requirements.txt
tests/test_dashboard_app.py
tests/test_dashboard_dados.py
tests/test_distribuicao.py
```

## Revisão independente R1 e correção do bloqueio

A revisão específica da etapa 7 foi executada **depois** dos critérios, testes e documentação técnicos acima. O revisor **openai-codex / gpt-6-astra**, com **20 chamadas principais efetivamente registradas**, reprovou a primeira versão por **um P2 bloqueante**: `Path.absolute()` não remove componentes `..`, permitindo que um destino lexicalmente fora do projeto apontasse para um local proibido dentro de um **cofre fictício**. A contraprova utilizou somente dados explicitamente sintéticos no SCRATCH. **Não houve gravação no cofre real nem evidência de vazamento no pacote de 32 arquivos.**

A referência de linha do parecer R1 descreve o código anterior à correção. O [parecer completo e as rodadas](../reports/distribuicao_dashboard_v1/revisao_independente.json) são preservados, sem reaproveitar a aprovação da etapa 6. O pai confirmou modelo/provedor no registro de uso, sem confiar apenas no nome solicitado. O revisor não alterou nenhum dos **58 arquivos congelados** para R1; abriu de fato três capturas e repetiu testes/aceites. Nenhuma publicação foi realizada.

Correção restrita a `exportar_dashboard.py` e `tests/test_exportar_dashboard.py`, por **openai-codex / gpt-5.6-terra**, **9 chamadas principais efetivas**. O teste novo falhou antes da implementação e passou após recusar componentes de diretório-pai na raiz e no destino, antes de comparar caminhos ou escrever. Foram mantidas a recusa de symlinks, de destino divergente e a idempotência. A regressão verifica destino permitido, destino direto proibido, alias com `..`, raiz com `..` e ausência de arquivos proibidos num cofre fictício.

**Reverificação do agente principal em 19 de outubro de 2026:**

- **12 testes do exportador/hachuras aprovados**, incluindo a regressão P2. Não se somam os 11 da fase anterior a esse total.
- Três pacotes regenerados produziram os mesmos **32 arquivos**; nove CSV/JSON mantiveram os bytes das fontes. ZIP reconstruído e comparado membro a membro. Os arquivos de runtime da distribuição são os mesmos da versão anterior; mudou somente o manifesto para refletir o hash da receita corrigida.
- **30 testes do pacote independente aprovados** em Python 3.12.15, com zero tentativas de acesso ao projeto original/rede/importação científica/escrita no pacote.
- Aceite AppTest novamente aprovado nos **48 GPs**, três telas, duas temporadas, invariância aos alvos e invalidação de cache. Não foram executados treinamento, inferência, coletores nem a suíte científica antiga.
- Servidor reiniciado em loopback `127.0.0.1:8502`, Python 3.12/HOME limpo. Chromium repetiu os seis documentos offline e o download CSV com SHA idêntico; zero erros de página ou solicitações externas. Viewport mobile 390/390 sem transbordamento global.
- Inspecionadas capturas novas de desempenho, documentação e gráfico mobile: favoritos continuam visíveis e hachurados, 478 casos probabilísticos e 22/24 GPs de ranking aparecem separados; o aviso de 2025 já avaliado precede os planos históricos. Tabela mobile extensa não cabe integralmente no viewport, sem certificação ampla de acessibilidade.
- Os 68 SHA científicos originais permanecem iguais. `pip check` novamente aprovado; ambiente científico original e dependências não foram migrados.

Segunda revisão independente ainda pendente neste registro pré-R2. Não há autorização implícita para publicar o aplicativo ou criar repositório público.

## Revisão R2 e correção da identidade física de caminhos

O revisor **openai-codex / gpt-6-astra**, **13 chamadas principais efetivas**, confirmou a correção específica de `..`, mas reprovou a segunda versão por outro **P2 bloqueante**. Neste volume do macOS, um cofre fictício chamado `cofre` e o alias `COFRE` eram o mesmo diretório, confirmado por `Path.samefile`, sem symlink. A comparação textual recusava o destino direto, mas permitia escrita real de sentinela explicitamente sintética pelo alias. A prova ficou exclusivamente no SCRATCH; os 59 arquivos revisados e os 68 SHA científicos originais permaneceram iguais. **O pacote atual de 32 arquivos não continha conteúdo do cofre.**

Correção da segunda rodada feita por **openai-codex / gpt-5.6-terra**, **7 chamadas principais efetivas**, somente no exportador e em seu teste. A validação agora compara a identidade física da raiz (device/inode) com cada ancestral existente do destino, inclusive quando as pastas finais ainda não existem. Não usa lowercase como substituto de identidade, e mantém os bloqueios de `..`, symlinks e destino divergente, além do destino permitido e idempotência.

Regressão RED/GREEN pelo fluxo real de exportação em cofre fictício, com conteúdo explicitamente sintético: **13 testes do exportador/hachuras aprovados, sem skips**. A prova independente anterior foi novamente executada pelo pai em saída separada, preservando a evidência rejeitada: **seis cenários de confinamento, zero violações**, com volume case-insensitive e alias de identidade confirmados. Não foram criados os arquivos proibidos.

Após a correção, novamente foram regeneradas três distribuições byte idênticas e o ZIP de 32 membros; nove fontes científicas e 68 SHA originais iguais. Nenhum arquivo de runtime da distribuição mudou: só o manifesto reflete o hash da receita corrigida. Passaram outra vez os **30 testes do pacote isolado** e o aceite de **48 GPs/3 telas/2 temporadas**, sob as mesmas guardas. Servidor 8502 reiniciado e Chromium novamente aprovado, seis documentos locais e download CSV com hash, zero erros de página/requisições externas e viewport 390/390. A `.venv` científica e os arquivos originais não foram migrados ou modificados. Não se somam quantidades de fases como se fossem uma suíte nova.

Terceira revisão independente pendente neste registro pré-R3; as duas reprovações e suas prioridades ficam no [histórico de pareceres](../reports/distribuicao_dashboard_v1/revisao_independente.json). Nenhum commit S7, deploy ou repositório público foi realizado até este ponto.

## Parecer final R3 — aprovação técnica com ressalvas

**Aprovado com ressalvas, sem problemas remanescentes reportados nos cenários examinados.** Terceira revisão em contexto independente por **openai-codex / gpt-6-astra**, com **13 chamadas principais efetivas**, confirmadas no banco de uso. As rodadas R1/R2 tiveram respectivamente **20/13 chamadas principais**; geração de título não é contada como revisão. Correções por **openai-codex / gpt-5.6-terra**, sem fazer do revisor o implementador. O [histórico integral](../reports/distribuicao_dashboard_v1/revisao_independente.json) preserva as duas reprovações e o parecer final.

O revisor fez **nove contraprovas próprias** pelo fluxo real de escrita com conteúdo sintético em cofre fictício: destino direto, alias de caixa com vários ancestrais finais inexistentes, alias da própria raiz, `..` em raiz/destino e symlink recusados; destino permitido, idempotência e recusa de divergência aprovados. **Nove cenários, zero falhas**, sem escrita proibida. Os 13 testes do exportador/hachuras, 30 testes do pacote isolado e aceite de 48 GPs/3 telas/2 temporadas foram também reexecutados pelo revisor, não somente pelo produtor. Conferiu novamente origem/manifesto/ZIP, nove cópias científicas, 20 fontes contra Git-base, nova reprodução byte exata, dependências, métricas, links e preservação.

**Revisão somente leitura comprovada:** os **59 arquivos congelados** para R3 ficaram byte idênticos após a revisão. Os 68 SHA científicos, índice/HEAD do projeto e versões originais permaneceram iguais. O revisor não criou commit/repositório, alterou privacidade/remotos/configuração ou publicou aplicativo. Escritas das probes e exportações de teste ficaram no SCRATCH. O registro final de parecer e os resumos de estado são finalizados pelo pai após o retorno; código, templates, pacote e ZIP não mudam após a aprovação.

**Inspeção visual:** R3 abriu de fato três capturas reais fornecidas (desempenho, documentação e gráfico mobile); não reexecutou Chromium/download nessa rodada. O agente principal reiniciou o servidor e executou Chromium/download após a última correção. O pai inspecionou adicionalmente as capturas finais de probabilidades mobile e calibração: barras favoritas visíveis, eixos/legenda legíveis e faixas vazias sem ponto artificial. Tabela extensa fica parcial no viewport; não há certificação de acessibilidade completa ou outros navegadores/dispositivos.

**Ressalvas que continuam, sem autorização de publicação:**

1. Aprovação técnica local em macOS/Python 3.12.15, não homologação Linux/Docker/Community Cloud. Nenhum deploy foi realizado.
2. Licença aberta do código e adequação da finalidade às condições dos dados dependem do autor. O parecer não é aconselhamento jurídico nem autorização de uso comercial.
3. Telemetria local pedida como desligada não garante desligamento na nuvem; a plataforma pode sobrepor a opção. As consultas oficiais registradas são de 18/10/2026; R2/R3 não refizeram a consulta externa, e as regras devem ser reconferidas na publicação futura.
4. A varredura cobre os padrões examinados e o confinamento cobre os cenários exercitados, não uma prova universal de ausência de segredos ou de todos os comportamentos possíveis de filesystem.
5. Não se executou a suíte científica antiga, treinamento, inferência, coletores nem APIs de dados. Modelo lido exclusivamente como bytes para hash, nunca desserializado. Instalação do ambiente novo e execução real foram verificadas; não se atribui compatibilidade apenas ao `pip install`.

Entrega ao repositório existente **privado**, por allowlist separada do inventário público, sem inclusão das demais notas do cofre. A lista pública permanece os **32 arquivos** acima; receita/testes/contexto/auditorias privadas e o contêiner ZIP não são arquivos extras a copiar para o repositório público. O guia para novo histórico/repositório público e Cloud descreve uma **etapa futura**, não executada nesta entrega.

## Sources

[1] https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy
[2] https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies
[3] https://docs.streamlit.io/deploy/streamlit-community-cloud/troubleshooting
[4] https://github.com/jolpica/jolpica-f1/blob/main/TERMS.md
[5] https://creativecommons.org/licenses/by-nc-sa/4.0
[6] https://docs.streamlit.io/develop/concepts/configuration/options
