# Automação e preparação de São Paulo — 03/11/2026

Português · [English](README.en.md)

Created by: MBPaschoal
Status: implementação em validação; publicação ainda não confirmada
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


## Validação local

Pacote: 144 testes aprovados. Navegação completa e quatro casos de downloads PT/EN em computador e Android emulado passaram: CSV/SVG salvos, idioma correto, zero reexecuções causadas pelo download e filtros preservados. A bateria ampliada passou em 390 testes antes dos últimos casos de reforço; a suíte focal final passou em 47. Foram incorporadas 344 cópias de originais (106.220.808 bytes), sem conflitos, e o registro de 19 emissões ficou válido. O modelo congelado carregou com seus hashes/fingerprint originais, sem inferência. [Recibo local](local-validation.json), [preparação offline](offline-readiness.json), [preservação](protected-integrity.json) e [inventário dos originais](restoration-plan.json). CI/release/deploy permanecem pendentes nesta etapa.
