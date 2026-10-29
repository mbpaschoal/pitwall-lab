# Entrega 0.1.0 / Release 0.1.0

## Português

Esta entrega reúne as últimas correções locais de dados e interface com a primeira política explícita de versões do produto. As notas completas estão no [changelog](../CHANGELOG.md).

- Histórico: até cinco edições anteriores da mesma pista, excluindo a prova atual, futuras e Sprint.
- Circuitos: 26 fichas; altitude aproximada, referência de DRS e recorde com piloto/ano.
- Dados: 75 itens resolvidos, seis ausências confirmadas e 31 limitações de pneus preservadas.
- Idiomas: botões nativos BR/GB no canto inferior, lado a lado também no celular. Troca de idioma mantém tela, GP, aba e filtros.
- Código: 27 módulos reorganizados em responsabilidades do blueprint; compatibilidade dos comandos antigos. Produtores científicos congelados preservam seus caminhos.
- Documentação atual e notas de versão PT/EN; protocolos científicos têm traduções separadas. Registros históricos mantêm os originais e um guia de leitura em inglês, sem reescrever o Git.

## Verificação local

A auditoria ampla executou 139 testes. Após ajustes, a suíte final dos módulos afetados executou 68 testes; o pacote isolado passou em 59 testes portáteis. As suítes se sobrepõem, portanto não somar esses números como testes distintos.

O navegador conferiu desktop 1440×1000 e celular 390×844 em iframe: clique nas duas bandeiras, idioma em documentos/gráficos/tabelas, GP/aba preservados, CSV descritivo em inglês e CSV científico byte idêntico. O build servido localmente corresponde ao manifesto. Os 614 arquivos científicos/fontes/emissões protegidos mantiveram SHA-256. A navegação não executou coleta, treino ou inferência.

O pacote possui 138 arquivos. Build: `f1ec70494fa0925e82b1a5bf41f8af5f2bd3359699dee7c67126f7a7c0326708`. A verificação local antecede a publicação; a confirmação pública é registrada separadamente após o push.

## Aprendizado nesta implementação

Traduzir rótulos não basta: mudanças de idioma também podem recriar controles e perder sua seleção. Os testes encontraram esse caso na Metodologia; os valores canônicos passaram a ser preservados explicitamente. Blocos de código e CSVs científicos também receberam contraprovas para impedir tradução de identificadores ou alteração de evidência. A inspeção móvel encontrou o empilhamento das bandeiras, corrigido antes da publicação.

## English

This delivery combines the latest local data/UI corrections with the first explicit product-version policy. Full notes are in the [changelog](../CHANGELOG.en.md).

- History: up to five previous editions at the same circuit, excluding the current race, future races and Sprint.
- Circuits: 26 profiles, approximate altitude, DRS reference and record holder/year.
- Data: 75 resolved items, six confirmed absences and 31 preserved tyre limitations.
- Languages: native BR/GB controls in the lower corner, side by side on mobile. Switching retains screen, GP, tab and filters.
- Code: 27 modules organised by blueprint responsibility with compatible old commands. Frozen scientific producers retain their paths.
- Current documentation/version notes in PT/EN, with separate scientific-document translations. Historical originals and an English reading guide preserve the Git record.

The broad local audit ran 139 tests. Following adjustments, the final affected-module suite ran 68; the isolated package passed 59 portable tests. Suites overlap and must not be summed as distinct tests.

Browser checks used 1440×1000 desktop and 390×844 mobile iframe sessions: both flags clicked, translated documents/charts/tables, retained GP/tab, English descriptive CSV and byte-identical scientific CSV. The local served build matches the manifest. SHA-256 remained unchanged for 614 protected scientific/source/emission files. Browsing performed no collection, training or inference.

The 138-file package has build `f1ec70494fa0925e82b1a5bf41f8af5f2bd3359699dee7c67126f7a7c0326708`. Local verification precedes publication; public confirmation is recorded separately after push.

A lesson from implementation: translating labels can recreate controls and lose their selections. Tests found this in Methodology; canonical values are now explicitly retained. Code blocks/scientific CSVs have counterchecks against translated identifiers or altered evidence. Mobile inspection caught vertically stacked flags, corrected before publication.
