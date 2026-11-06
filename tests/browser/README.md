# Aceite de navegação e contexto / Navigation and context acceptance

Os testes leem o dashboard e clicam como um usuário. Não coletam dados nem alteram probabilidades. Requerem Playwright e um servidor já iniciado. Use contextos novos para conferir uma publicação e informe a versão esperada.

The checks read the dashboard and click through user flows. They do not collect racing data or change probabilities. Playwright and a running server are required. Use fresh browser contexts and an expected version when validating a deployment.

```sh
PITWALL_EXPECTED_VERSION="$(cat VERSION)" node tests/browser/aceite_contexto.cjs http://127.0.0.1:8501 /tmp/context-evidence
```

`aceite_contexto.cjs` executa quatro fluxos em PT/EN e larguras 390/1440: marca/pódio, campeonato→perfil, busca curta com contexto da equipe, e filtro→idioma→chips→limpar. Deve ser o smoke de CI. Falhas de clique produzem captura e `interactions.json`; não há clique forçado.

`aceite_contexto.cjs` runs four flows in PT/EN at widths 390/1440: brand/podium, standings→profile, short search with team context, and filter→language→chips→clear. It is the CI smoke. Failed clicks produce a screenshot and `interactions.json`; clicks are never forced.

`aceite_interacoes.cjs` executa a auditoria funcional completa, incluindo favoritos, documentos, CSV/SVG, cartões e idiomas. `aceite_links.cjs` verifica 100 estados e todos os anchors renderizados, inclusive destinos de fragmentos. Para comparar o CSV científico baixado com o original, defina `PITWALL_SOURCE_ROOT` como a raiz do pacote validado.

`aceite_interacoes.cjs` runs the full interaction audit, including favorites, documents, CSV/SVG, cards and language changes. `aceite_links.cjs` checks 100 states and every rendered anchor, including fragment targets. Set `PITWALL_SOURCE_ROOT` to the validated package root to compare downloaded scientific CSV bytes with the original.

Variáveis / Environment:

- `PLAYWRIGHT_BROWSER=chromium|webkit` (padrão/default: chromium).
- `PLAYWRIGHT_CHANNEL=chrome` opcional / optional.
- `PLAYWRIGHT_MODULE` caminho de módulo alternativo / alternate module path.
- `PLAYWRIGHT_BROWSERS_PATH` cache dos navegadores / browser cache.
- `PITWALL_EXPECTED_VERSION` versão exibida obrigatória / required served version.
- `PITWALL_SOURCE_ROOT` raiz com artefatos originais / root containing original artifacts.
- `PITWALL_FLOW` filtro opcional por nome de fluxo / optional flow-name substring filter.

A versão/tela/idioma e o estado idle são aguardados antes das asserções; a página pública do Streamlit é reconhecida pelo iframe do aplicativo. HTTP externo é auditado em recibos separados: disponibilidade atual não garante funcionamento futuro. Canvas, gráficos e dispositivos físicos exigem os outros aceites do projeto.

Checks wait for the expected version, route, language and idle state. Streamlit Cloud's app iframe is supported. External HTTP availability is recorded separately and does not guarantee future reachability. Canvas, charts and physical devices require the project's other acceptance checks.

`PITWALL_CONCURRENCY=2` permite até dois contextos simultâneos por conjunto; o padrão é um. `PITWALL_RESUME=1` retoma somente casos aprovados de uma execução com mesma URL, engine e versão esperada, preservando a evidência original. As saídas são gravadas atomicamente. Em publicação, o aceite compara também URL externa/iframe e recarrega capítulos e retorno documental para conferir persistência.

`PITWALL_CONCURRENCY=2` enables at most two concurrent contexts per suite; the default is one. `PITWALL_RESUME=1` reuses only passed cases for the same base URL, engine and expected version, preserving the original evidence. Output files are written atomically. Public acceptance also compares outer/iframe routes and reloads chapters and document returns to verify persistence.

`aceite_controles.cjs` mede a bandeira preta/branca e o alinhamento dos expansores nas seis telas PT/EN em 390/1440 px; aceita Chromium/WebKit e verifica abertura/fechamento, margem, centro vertical e área mínima de toque de 44 px.

`aceite_controles.cjs` checks the black/white flag and expander alignment across all six screens in PT/EN at 390/1440 px, with Chromium/WebKit, toggles, paragraph margins, vertical centers and 44 px touch targets.

`verificar_publicacao.cjs VERSION COLLECTION_JSON [OUTPUT]` confirma a entrega de dados já publicada em quatro casos PT/EN e 390/1440 px. Exige o evento no calendário e no estado coletado do pacote, fotos decodificadas e hashes conferidos, controles prontos e build exato. Limite: duas tentativas por caso, oito minutos no conjunto; JSON conserva falhas e capturas. `PITWALL_SOURCE_ROOT` define o pacote esperado; `PITWALL_PUBLIC_BASE_URL` permite ensaio local explícito. O workflow usa o domínio público padrão.

`verificar_publicacao.cjs VERSION COLLECTION_JSON [OUTPUT]` checks an already-published data delivery in four PT/EN desktop/mobile cases. It requires the event in both the package calendar and collected state, decoded photographs with matching hashes, ready controls and exact build. Two attempts per case, eight minutes total; JSON retains failures and screenshots. `PITWALL_SOURCE_ROOT` selects the expected package; `PITWALL_PUBLIC_BASE_URL` permits explicit local rehearsal. The workflow defaults to the public domain.

`node --test tests/browser/test_verificar_publicacao.cjs` executa dez contraprovas, oito com navegador real / runs ten counterexamples, eight with real browsers: approved pixels, wrong SHA, broken photo, PT/EN readiness, native/link controls, foreign origin and package/event/version mismatch.


`aceite_resiliencia.cjs BASE_URL OUTPUT` bloqueia os módulos nativos Radio/Button e exige links por teclado nos seis destinos, troca de idioma, contexto de GP, alvos de 44 px e ausência de transbordamento em PT/EN e 390/1440 px. Os 12 aceites anteriores continuam no CI. O modo normal mantém os mesmos controles; os links alternativos ficam ocultos e fora da navegação por teclado quando os controles nativos estão disponíveis.

`aceite_resiliencia.cjs BASE_URL OUTPUT` blocks native Radio/Button modules and requires keyboard links through all six destinations, language switching, GP context, 44 px targets and no overflow in PT/EN at 390/1440 px. All previous 12 CI checks remain. Native controls stay unchanged; alternative links are hidden and excluded from keyboard navigation when native controls are available.

O recibo público v2 registra controles nativos/links/mistos; uma alternativa só conta quando está visível e aponta para a mesma aplicação/idiomas admitidos. O verificador clica a navegação alternativa quando usada e troca o idioma de fato, preservando GP e tela; erro visível não recuperado reprova o aceite. Duas tentativas por caso, até 120 segundos por tentativa, oito minutos totais.

Public receipt v2 records native/link/mixed controls. An alternative counts only when visible and targeting the same app/admitted locales. The verifier clicks alternative navigation when used and actually switches language while retaining GP and page; unrecovered visible errors fail acceptance. Two attempts per case, at most 120 seconds each, eight minutes overall.

## Acabamento e Duelo / Editorial finish and head to head

`node tests/browser/aceite_editorial.cjs URL OUTPUT` cobre PT/EN em 390/1440 px, retratos na mesma linha, diferença conferida por contagem independente dos resultados-fonte, troca real de condição/métrica, mínimo de amostra, ausência de largadas em comum, idioma e redução manual/pelo sistema. `PLAYWRIGHT_BROWSER=webkit` seleciona o segundo motor. Respeita `PITWALL_SOURCE_ROOT`, `PLAYWRIGHT_MODULE` e `PLAYWRIGHT_CHANNEL`. Cada falha gera captura e recibo explícito.

The runner checks PT/EN desktop/mobile portraits, independently counted metric differences, real condition/metric changes, minimum samples, no shared starts, language preservation and manual/system reduced motion. Failures produce screenshots and explicit receipts.

## Roteiros históricos / Historical runners

`aceite_dashboard.cjs` e `aceite_idiomas.cjs` conservam os seletores da interface anterior à navegação atual. São referências históricas e não compõem o CI ou o aceite de uma nova publicação. Use os roteiros atuais descritos acima; um resultado desses dois arquivos não comprova a entrega atual.

`aceite_dashboard.cjs` and `aceite_idiomas.cjs` retain selectors from the earlier interface. They are historical references, excluded from CI and new-release acceptance. Use the current runners above; results from these two files do not prove delivery of the current product.

Os recibos de fim de semana só indicam `passed` após os quatro casos PT/EN e desktop/mobile; uma execução parcial indica `in_progress` e conserva falhas. / Weekend receipts indicate `passed` only after all four PT/EN desktop/mobile cases; partial runs remain `in_progress` and retain failures.
