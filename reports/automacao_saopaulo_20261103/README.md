# Automação e preparação de São Paulo — 03/11/2026

Português · [English](README.en.md)

Created by: MBPaschoal
Status: published v0.8.26; public loading limits recorded
Type: delivery evidence

Entrega 0.8.26: [inventário das rotinas, limites e responsáveis](../../docs/AUTOMACAO.md). O orquestrador não foi executado para emitir uma previsão futura; São Paulo aguarda o encerramento real de Q. Testes com relógios/transportes controlados exercitam as barreiras sem fabricar uma emissão real.

As referências visuais em `sources/` vieram dos mapas detalhados oficiais F1 das páginas de 2026: Interlagos, Las Vegas, Lusail e Yas Marina. Os recibos preservam URL, UTC real de obtenção, bytes e SHA-256. A direção e as curvas numeradas foram conferidas visualmente. Os comprimentos foram conferidos nas respectivas páginas oficiais; não se trata de homologação FIA nem de uma declaração sobre alterações futuras. Altitudes Open-Meteo são aproximações nos pontos do calendário canônico, sem relação com temperatura do asfalto ou desnível total do circuito.

| Circuito | Curvas | Sentido | km | Altitude pontual |
|---|---:|---|---:|---:|
| Interlagos | 15 | Anti-horário | 4,309 | 779 m |
| Las Vegas | 17 | Anti-horário | 6,201 | 644 m |
| Lusail | 16 | Horário | 5,419 | 12 m |
| Yas Marina | 16 | Anti-horário | 5,281 | 7 m |

Páginas oficiais: [São Paulo](https://www.formula1.com/en/racing/2026/brazil), [Las Vegas](https://www.formula1.com/en/racing/2026/las-vegas), [Qatar](https://www.formula1.com/en/racing/2026/qatar), [Abu Dhabi](https://www.formula1.com/en/racing/2026/united-arab-emirates). [API de altitude](https://open-meteo.com/en/docs/elevation-api).

O download usa `on_click="ignore"`, opção documentada para evitar reexecução. O teste de navegador verifica o arquivo salvo, idioma e envio de mensagens `rerun_script`, além da preservação do piloto selecionado. Isso não comprova por si só o download servido na nuvem; a conferência pública será registrada separadamente. [Documentação Streamlit 1.50](https://docs.streamlit.io/1.50.0/develop/api-reference/widgets/st.download_button).

Também foi corrigida a criação do diretório antes de instanciar o cliente real na descoberta de calendário. O teste usa o cliente verdadeiro com transporte local, preserva a primeira resposta e não faz HTTP.

O código foi desenvolvido em checkout isolado a partir de `a31b006`, preservando os rascunhos locais. Modelo v1, probabilidades e emissões existentes devem continuar byte a byte iguais; o recibo final registrará a conferência. Nenhuma automação local adicional foi criada: a antiga rotina do México está pausada e a nova rotina fica hospedada no GitHub.


## Validação local antes da publicação

Pacote: 144 testes aprovados. Navegação completa e quatro casos de downloads PT/EN em computador e Android emulado passaram: CSV/SVG salvos, idioma correto, zero reexecuções causadas pelo download e filtros preservados. A bateria ampliada passou em 390 testes antes dos últimos casos de reforço; a suíte focal final passou em 47. Foram incorporadas 344 cópias de originais (106.220.808 bytes), sem conflitos, e o registro de 19 emissões ficou válido. O modelo congelado carregou com seus hashes/fingerprint originais, sem inferência. [Recibo local](local-validation.json), [preparação offline](offline-readiness.json), [preservação](protected-integrity.json) e [inventário dos originais](restoration-plan.json). CI/release/deploy permanecem pendentes nesta etapa.


## Publicação e limites da conferência pública

Versão **0.8.26 publicada e Latest**, CIs de main/tag aprovados, 394 testes de código, 144 do pacote e 11 suítes de navegador. A coleta hospedada concluiu saudável: 67 GPs, sem pendências e sem nova versão por recebimentos idênticos. ZIP publicado com 665.855.915 bytes e SHA-256 `8a7d60cb69b17d0977d9650bc909a9b39323ab08de671b10939c43e148b35ceb`, igual ao local. O Streamlit serviu o build `f60379c599caaaddb05c4d66340713e0e0227914a874cd42049361abd8c03c0a` em sessão limpa.

O SVG e o CSV em inglês foram baixados em Android emulado por entrada direta com link completo e por navegação a partir de Como funciona: zero reexecuções por download; a entrada direta passou sem recarga e a segunda precisou de uma. Computador/PT também passou. Outras tentativas públicas falharam no bootstrap, ao carregar módulos do Streamlit ou ao completar o download. Uma primeira matriz desktop usou toque indevidamente; essa falha é do teste e foi separada. Não se declara a matriz pública inteira aprovada nem validação em aparelho físico. Todos os registros, inclusive falhas, foram preservados.

[Release](https://github.com/mbpaschoal/pitwall-lab/releases/tag/v0.8.26) · [Recibo final](delivery-final.json) · [CI, release e ZIP](github-final.json) · [Testes finais](source-tests-final.json) · [Inglês móvel direto](public-mobile-focused/direct.json) · [Inglês móvel após entrada em Como funciona](public-mobile-focused/welcome.json).

## Aprendizado desta entrega

A interface já funcionava com os assets, mas o produtor científico precisava de originais que ainda não estavam no checkout do GitHub. A verificação ampliada revelou a lacuna antes da automação pós-Q. Foram incorporadas 344 cópias idênticas, completando o registro de 19 emissões; CI agora confere esse registro e carrega o modelo com seu fingerprint original, sem inferência. A data desta incorporação não cria evidência retroativa de publicação antes de uma corrida. O modelo e as probabilidades anteriores continuam preservados.

A correção do download evita reexecutar a página; as tentativas públicas também mostraram uma instabilidade distinta no carregamento dos componentes. Guardar os dois resultados permite avaliar o limite real da entrega.
