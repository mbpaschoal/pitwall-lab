# Etapa 6 — verificações do dashboard local

## Parecer final — aprovado na segunda revisão independente

A R2 aprovou o dashboard sem problemas remanescentes. Revisor efetivo **`openai-codex/gpt-6-astra`**, sessão `local-bdf6b0a4b6019bdf139b803ed1dcf93ad21ca601e03ac1972a6846efa84a42ec`, **12 chamadas da tarefa principal** confirmadas no banco pelo agente principal. O Astra repetiu os 26 testes de dashboard, o aceite restrito, as três contraprovas originais e a inspeção das três imagens reais; conferiu os 68 hashes científicos e os 19 arquivos de entrega sem divergência. O agente principal também comparou os 19 hashes antes/depois: o revisor não alterou arquivos do projeto.

Os dois pareceres estão preservados no [registro integral](revisao_independente.json). A aprovação é do dashboard local, não do uso futuro do modelo, de publicação na internet ou de todos os dispositivos/acessibilidade. Não foi repetida a suíte científica legada após a R1; sua execução anterior de 129 testes permanece identificada como histórica. A inspeção visual mobile cobriu o viewport superior, não os gráficos e tabelas abaixo da dobra.

## Primeira revisão independente — três bloqueios encontrados

A implementação inicial, testes, instruções e inspeção real foram concluídos antes de solicitar a revisão. **A primeira revisão forte reprovou três P2 de validação**, sem identificar divergências nos artefatos científicos reais: ranking incompatível com probabilidades era aceito, strings/booleanos em métricas JSON podiam passar e causar erro de formatação, e rótulos inválidos de calibração podiam causar erro de apresentação. As correções devem rejeitar os arquivos incoerentes com mensagem útil, nunca recalcular ou substituir resultados publicados.

Revisor efetivo **`openai-codex/gpt-6-astra`**, sessão `local-accc3144233d6ea1bd339c1e411fb8b3f1c70211fe62ffd3af8b0821d2af961e`, **10 chamadas da tarefa principal** confirmadas no banco. Os 18 arquivos de entrega conferidos antes/depois permaneceram byte a byte iguais; as três imagens solicitadas foram abertas com `vision_analyze`. O [parecer integral](revisao_independente.json) preserva os problemas e as linhas da versão anterior às correções. **Na conclusão da R1 não havia aprovação; o parecer final favorável veio somente na R2, acima.**

## Escopo e fontes

Dashboard somente leitura dos resultados retrospectivos v1, em Streamlit/Plotly. O [contrato](../../docs/contrato_dashboard_v1.md) precede a interface e identifica os nove CSV/JSON utilizados nas duas temporadas. Não se carrega joblib, não há inferência, treinamento, coleta, consulta externa de dados ou regeneração de bases. O servidor foi iniciado e responde em `127.0.0.1:8501`; não houve hospedagem pública ou túnel.

2024 é validação já explorada; 2025 é avaliação final retrospectiva já realizada. O dashboard mantém os denominadores de 2025: 478 casos probabilísticos e os mesmos 22 dos 24 GPs para os rankings. Os valores exibidos vêm dos arquivos, não de números copiados para o código.

## Implementação e correções efetivamente utilizadas

- Implementação: `openai-codex/gpt-5.6-terra`, sessão `20261018_142230_5052a8`.
- Correção de pré-QA: `openai-codex/gpt-5.6-terra`, sessão `local-c898bcfb3cb5ca4f8f8cbbee4ffe96c6ebf391bdc4dfb1238582230b03d9532a`.
- Correção após inspeção visual: `openai-codex/gpt-5.6-terra`, sessão `local-8817a8ce5cbfffd110463fb62cf138cc3f6c05ddde3d8cc7785c349887d3c14d`.

- Correção dos três P2 após revisão: `openai-codex/gpt-5.6-terra`, sessão `local-32a97f8814f15596521a1742952b4f7fdfa288578b3a2a83dbd85178cd7fe61f`, 20 chamadas da tarefa principal confirmadas no banco.

As identidades são conferidas nos registros de uso da tarefa principal, não pela autodescrição do agente. O fluxo de lançamento via gateway recusou parâmetros não suportados antes de executar correções; foram usadas sessões novas com os parâmetros de criação aceitos, sem alterar política ou configuração global.

### Problemas corrigidos antes da revisão forte

1. Gráfico de probabilidades falhava com zero elegíveis: `max()` recebia uma sequência vazia. Agora há figura/mensagem vazia explícita, sem probabilidades inventadas, e aviso quando não há três favoritos disponíveis.
2. O validador aceitava média de ranking adulterada em memória, desde que estivesse entre 0 e 3. Agora confere média e distribuição contra os acertos por GP publicados. Não corrige dados nem substitui as métricas originais.
3. Cobertura e estado N/A apareciam tarde na exploração. Agora temporada/função, cobertura e motivos ficam perto do título, com indicação de que alvos conhecidos são informação posterior da avaliação.
4. A legenda da calibração ficava próxima ao título do eixo horizontal na captura real. Foi movida para o topo, sem alterar coordenadas de dados, símbolos ou valores.
5. O filtro de GP parecia atuar em métricas anuais. Agora fica desabilitado fora de “Explorar um GP”, com explicação de seu âmbito.
6. A explicação de método foi ampliada para linguagem simples, incluindo elegibilidade, ausências, transformações congeladas e links dos dois relatórios.

Houve regressões RED/GREEN para as correções. **Nenhuma dessas mudanças alterou probabilidades, favoritos, métricas ou artefatos científicos das etapas 4 e 5.** Não houve alteração metodológica.

## Testes e aceitação independente

- Baseline antes de editar: **109 testes aprovados**.
- Suíte completa antes da primeira revisão: **129 testes aprovados**, zero falhas e zero erros; `pip check` passou.
- Após os três P2, **26 testes específicos de dashboard aprovados**, incluindo seis regressões novas. Não se afirma execução de uma suíte completa de 135 testes; os testes científicos/coletores não foram repetidos nesta rodada. Foram corrigidos: coerência ranking/probabilidade e desempate por ID, tipos JSON reais/inteiros sem strings/booleanos, e rótulos/limites de calibração. A tabela agora ordena e associa faixas pelos limites numéricos, não por interpretação do rótulo.
- AppTest percorreu novamente **48 GPs**, três telas e as duas temporadas depois das correções e da reinicialização do servidor. Favoritos foram comparados aos ranks publicados; alterar alvos em memória não mudou a escolha.
- GPs não avaliáveis mantiveram pontuação indefinida, sem zero artificial. Stroll/Espanha continua com previsão e alvo desconhecido; Bortoleto/São Paulo continua inelegível na base.
- Guarda de arquivos/rede no aceite do app: somente os nove CSV/JSON necessários foram abertos como relatórios; nenhum dado bruto ou modelo foi aberto, nenhuma solicitação externa ou escrita em artefatos foi registrada.
- Cache exercitado com arquivo temporário alterado mantendo o `mtime`: o aplicativo rejeitou o conteúdo novo inválido, sem mostrar dados antigos. Arquivo temporário removido produziu erro útil, sem dados antigos do cache.
- Avisos `missing ScriptRunContext` apareceram na execução isolada de ferramentas AppTest em modo bare; não foram exceções do dashboard. O navegador não registrou erros de página.

**Limite importante da suíte antiga:** os 129 testes acima foram executados pelo agente principal antes da primeira revisão. Não equivalem a 129 testes sob a guarda estrita do aplicativo. O wrapper antigo bloqueia parte dos dados preparados e a rede no processo principal, mas não herda automaticamente suas guardas em subprocessos. Um teste legado executa o coletor com seu cache local, e outro carrega o modelo real para avaliação em dados sintéticos temporários. Isso não faz parte do fluxo do dashboard, nem é reavaliação do teste real de 2025, mas impede atribuir a toda a suíte a afirmação “não abre dados/modelo e não executa coletor”. O Astra não executou esses testes: executou os **20 testes específicos de dashboard**, o aceite restrito e contraprovas próprias. A guarda estrita de nove relatórios, sem dados/modelo/rede/escrita, é a do **aceite do aplicativo**, não a da suíte científica legada.

O [registro estruturado](verificacao.json) contém os resultados observados. Scripts adicionais de auditoria em `scratch` são ferramentas internas da execução, não dependências do aplicativo nem arquivos prometidos no clone.

## Inspeção visual real

A ferramenta de navegador baseada no perfil real não suporta o navegador padrão configurado nesta máquina. Não se mudou o navegador padrão ou configuração do Hermes para contornar isso. Foi usado **Chromium isolado 140.0.7339.16**, por Playwright 1.55.0 instalado em ambiente temporário de QA, separado da pilha do projeto.

Foram navegadas as três telas e o GP não avaliável da Espanha. Capturas reais foram examinadas em desktop (1440 × 1100) e viewport mobile de 390 × 844. Na verificação final:

- Zero erros de página.
- Zero solicitações externas da página; somente `127.0.0.1` apareceu nos hosts das requisições. HTTP e WebSocket local são necessários ao Streamlit e não constituem consulta a dados externos.
- Largura do documento mobile: 390 px, igual ao viewport, sem transbordamento horizontal global. Tabelas têm rolagem interna.
- Legenda da calibração acima do gráfico, sem conflito com o título do eixo x; métodos identificados também por símbolos.
- Filtro de GP desabilitado nas telas anuais/de método; navegação preservada.

Capturas: [exploração](explorar_desktop.png), [desempenho](desempenho_desktop.png), [calibração](calibracao_desktop.png), [como funciona](como_funciona_desktop.png), [N/A](espanha_na_desktop.png), [mobile](explorar_mobile.png). São capturas de viewports reais, com rolagem quando necessário, não imagens fabricadas ou composição de uma página inteira.

Autoavaliação visual: superfície de exploração/comparação, sem hero promocional, grade de funcionalidades genéricas, blur ou gradientes decorativos. O destaque lateral colorido é restrito ao aviso retrospectivo; conteúdo, filtros e dados têm hierarquia própria.

## Preservação e ambiente

Os **68 SHA-256** de [artefatos preservados](../../docs/dashboard_artefatos_preservados.json) foram conferidos sem divergências. Dados originais permanecem fora do fluxo do dashboard; seus identificadores de objetos Git são comparados sem reabrir bases mistas para hashes.

Versões científicas preservadas: NumPy 1.26.4, SciPy 1.13.1, scikit-learn 1.6.1, joblib 1.5.3 e threadpoolctl 3.6.0. Novos pacotes do app estão em `requirements_dashboard.txt`, sob restrições do arquivo científico original. Nenhum pacote foi instalado globalmente.

Não foi executado comando para editar configuração do Hermes. O hash global de `config.yaml` mudou durante a sessão; apenas esse fato não permite atribuir a origem da mudança. Não se restaurou a configuração nem se afirma identidade byte a byte desse arquivo para todo o período. O provedor/modelo principal atual e a identidade de cada agente são tratados separadamente; a escolha de modelos nas execuções não configura automaticamente futuras revisões.

## Abrir e navegar

```bash
./.venv/bin/python -m pip install -r requirements_dashboard.txt
./.venv/bin/python -m streamlit run app.py
```

Abrir `http://127.0.0.1:8501`. Usar a lateral para escolher tela, temporada e, na exploração, o GP. No celular, abrir a lateral pelo botão no canto superior esquerdo. A tela Desempenho agrega a temporada inteira. Quando iniciar no seu terminal, manter esse terminal aberto; `Ctrl+C` encerra sua execução.

A pilha foi verificada localmente com Python 3.9.6. Não se avaliou hospedagem pública, segurança de implantação externa ou todas as combinações de navegadores/dispositivos. O código no repositório privado não significa que o aplicativo foi publicado. As limitações retrospectivas e a ausência de garantia futura permanecem; 2025 não é mais um teste intocado.
