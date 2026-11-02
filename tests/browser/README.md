# Aceite de navegação e contexto / Navigation and context acceptance

Os testes leem o dashboard e clicam como um usuário. Não coletam dados nem alteram probabilidades. Requerem Playwright e um servidor já iniciado. Use contextos novos para conferir uma publicação e informe a versão esperada.

The checks read the dashboard and click through user flows. They do not collect racing data or change probabilities. Playwright and a running server are required. Use fresh browser contexts and an expected version when validating a deployment.

```sh
PITWALL_EXPECTED_VERSION=0.8.16 node tests/browser/aceite_contexto.cjs http://127.0.0.1:8501 /tmp/context-evidence
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
