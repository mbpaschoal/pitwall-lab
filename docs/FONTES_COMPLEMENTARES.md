# Fontes complementares

[English](en/COMPLEMENTARY_SOURCES.md)

O acervo usa um complemento descritivo aprovado de F1DB, documentos FIA e contexto Pirelli. A base original permanece intacta: o leitor valida primeiro os hashes da base e das 262 revisões de idade dos pneus já aprovadas, depois aplica `frontend_assets/complemento_fontes_v1.json` em memória. O complemento também é fixado por hash. A navegação não coleta, treina ou infere; não altera as 15 entradas, o modelo v1 ou as probabilidades registradas.

## Fontes e admissão

[F1DB v2026.19.0](https://github.com/f1db/f1db/releases/tag/v2026.19.0) é um candidato complementar, com atribuição [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). A amostra contém 61 registros de classificação de São Paulo 2024/2025 e México 2026. A identidade combina temporada, rodada, data, coordenadas, número do carro no evento e nascimento; IDs dos provedores ficam separados. Valores canônicos, candidatos e campos admitidos permanecem distintos.

Somente transcrições documentais revisadas em PDF FIA podem alterar campos de uma nova projeção. Os três Q2 admitidos de São Paulo 2024 já estavam corretos na interface: a entrega acrescenta procedência. México 2026 não pertence ao acervo-base de 66 GPs/330 sessões; a revisão de DSQ permanece no complemento, sem criar um GP ausente. DSQ/DNS/NC preservam observações brutas, mas retiram posições e tempos válidos de apresentação. Os documentos FIA mantêm suas condições próprias.

[Pirelli — São Paulo 2026](https://press.pirelli.com/pirelli-brings-the-softer-trio-back-to-interlagos/), publicado em 03/11/2026, fornece alocação HARD C3/MEDIUM C4/SOFT C5 e contexto de pista. Fatos e expectativas ficam separados, fora das sessões observadas. O artigo não demonstra estratégia executada ou efeito causal. Nenhuma licença F1DB/Jolpica foi estendida a Pirelli/FIA. Veja [atribuições do pacote](../publicacao/templates/FONTES_E_DADOS.md).

## Reprodução e limites

O módulo `pitwall.data.complementary_sources` aceita planos locais e fontes brutas preservadas para construir um complemento offline. Esses inputs de autoria permanecem no arquivo local da pesquisa e não são publicados com o aplicativo. O CI público verifica o complemento aprovado e a composição real com a revisão de pneus, além de testar o construtor e recusas de admissão com fixtures controladas. A revisão documental original não é substituída pelo CI.

Para reproduzir a projeção sem modificar a base, use `python -B -m pitwall.data.complementary_sources project --asset frontend_assets/acervo_dashboard.json --bundle frontend_assets/complemento_fontes_v1.json --output /private/tmp/acervo-complementado.json`. Essa saída independente contém o complemento de fontes; o leitor `pitwall.data.archive.carregar` é a via de composição completa com as idades dos pneus. O produtor de autoria `preparar_acervo_dashboard.py` também aceita `--complemento-fontes`. Saídas divergentes exigem destino novo; o mesmo complemento é idempotente.

As entregas locais 0.9.0 e 0.9.1 permanecem preservadas separadamente. A 0.9.2 integra a admissão à base pública 0.8.31, conservando suas correções de segurança, toque e navegação. Captura em 04/11/2026 não demonstra disponibilidade antes de cortes históricos. Nenhum ganho preditivo foi estabelecido. Testes locais, CI, release e versão servida no Streamlit são evidências diferentes.
