# Dados atuais, correções e limites

Português · [English](en/CURRENT_DATA.md)

O acervo é descritivo e separado das entradas v1: 66 GPs/330 sessões de 2024–2026 até Austin. A aquisição complementar de 29/10 foi serial e cacheada. Os nove artefatos científicos e as emissões anteriores foram preservados.

## México — composto inicial recuperado em 02/11/2026

As cinco sessões operacionais do México têm dados recebidos após conferência. O primeiro trecho de Lawson no TL3 foi recuperado como **MEDIUM nas voltas 1–8**: o GP Tempo observa o composto nas voltas 2–8, e a FIA confirma um trecho inicial contínuo de oito voltas. A atribuição à volta 1 é reconstrução documental por continuidade, identificada na interface e no CSV. Seu tempo ausente e a idade inicial do jogo permanecem ausentes.

O seletor de pneus permite acessar treinos, classificação e corrida, com as passagens pelos boxes separadas por sessão. As coberturas original e validada continuam distintas; estado de recebimento não significa que todo campo da fonte esteja completo. A revisão do catálogo preserva os horários observados da corrida e mantém a espera conservadora do acesso gratuito em campo separado. [Fontes, reconstrução, versões e recibos públicos](../reports/lawson_tyres_mexico_20261102/README.md).

Publicação conferida no site na versão **0.8.20**, em PT/EN e desktop/mobile, com CSVs reais. A atualização automática seguinte preservou a recuperação e renovou as classificações do campeonato.

Este complemento operacional não amplia automaticamente o acervo de condições de Pilotos nem altera o modelo ou as probabilidades registradas. Os registros por versão abaixo são históricos e preservam as limitações conhecidas em cada entrega.

## Fontes alternativas do México — 0.8.3

A revisão documental recupera os 22 tempos do TL3 e identifica Lawson por número, nome e equipe na lista oficial deste evento. O recorte temporal exclui um registro de paradas anterior ao TL3 e 84 anteriores à classificação; os originais não são apagados. A classificação final e a decisão dos comissários mostram Lawson como DSQ, sem posição numérica nem tempos válidos.

A média do asfalto agora usa 100 leituras válidas: 40,7 °C, 98,0% de cobertura, sem interpolação. O relatório FIA também registra o zero anômalo; ele não revela a temperatura real daquele minuto. Permanece ausente o composto do stint inicial de Lawson (voltas 1–8 do TL3), não inferido dos stints posteriores. A revisão aplica-se também ao cache e à automação. [Fontes, decisões e pendências](../reports/mexico_fontes_alternativas_20261101/README.md).

## Operação do México — 0.8.1

O acompanhamento separado do fim de semana agora tem resultado observado de 22 pilotos, 1360 registros de voltas, pneus, paradas e campeonatos completos da rodada 19 (24 pilotos e 11 equipes). O clima considera os intervalos efetivos da corrida: média do ar de 24,2 °C; a média do asfalto fica retida por uma leitura isolada de 0 °C entre 37,4 e 37,5 °C. TL3 e algumas paradas da classificação permanecem parcialmente retidos por cadastros ausentes na fonte. Esses dados operacionais não ampliam silenciosamente o acervo de condições de Pilotos nem alteram o modelo ou a avaliação científica. [Auditoria e pendências](../reports/auditoria_calendario_mexico_20261101/README.md) · [Operação automática](OPERACAO_FIM_SEMANA.md).

## Revisão da idade dos pneus — 0.8.2

Na apresentação 0.8.6, composto ausente ou `UNKNOWN` aparece como “Não informado”; os códigos conhecidos têm legenda textual. A idade inicial corresponde às voltas já acumuladas pelo jogo no início do stint: zero permanece o valor publicado, sem comprovar pneu novo, e ausência permanece vazia na tabela/CSV. O hover usa a mesma idade; a largura das barras continua representando somente os limites publicados. “Limites comparáveis” refere-se à sequência do piloto, não à validade da idade ou do composto. Essas adaptações PT/EN são de apresentação e não alteram a base, o complemento ou as previsões.

O [complemento v1](../frontend_assets/complemento_idade_pneus_v1.json) revisa somente a idade inicial de 262 stints do acervo, em 55 sessões e 47 GPs: 210 valores antes zero agora são positivos, 36 passaram a zero e 16 mudaram entre valores positivos. A tabela e o CSV de detalhes mostram as idades revisadas. O gráfico conserva composto e limites.

A projeção-base e os snapshots originais permanecem intactos. O leitor aplica o complemento offline, com hashes e correspondência única por sessão, piloto, composto, limites e valor antigo. Se faltar a revisão obrigatória ou houver divergência, a leitura falha explicitamente. O JSON conserva as identidades nativas e as URLs, hashes e UTC das três respostas históricas usadas na auditoria. São revisões descritivas posteriores, não informações retroativamente disponíveis no corte da previsão.

Os 194 casos com revisão estrutural e 58 sem associação única ficaram fora desta entrega. As 388 idades da projeção operacional do México já concordavam com a consulta e não foram alteradas. O [PR OpenF1 #478](https://github.com/br-g/openf1/pull/478) explica a atualização de `StartLaps`; nem toda divergência da fonte foi atribuída automaticamente a ele. Modelo v1 e probabilidades registradas permanecem preservados.

## Controle de qualidade de Pilotos — 0.2.0

A [auditoria atual](../reports/pilotos_condicoes_20261029/README.md) substitui o estado de pneus da revisão inicial abaixo: 295 verificações tratadas, 50 limites adjudicados, nove compostos recuperados e 17 compostos de treinos/classificação indisponíveis nas duas fontes consultadas. Essas lacunas permanecem ausentes e impedem análises que dependam delas; não afetam resultados por condições de corrida. São 66 corridas principais, 1.354 resultados, 1.340 largadas e oito provas com chuva registrada durante os intervalos efetivamente disputados. Os 66 mapas FIA foram conferidos por edição, inclusive comprimentos que mudaram entre anos e o traçado em oito de Suzuka. Nenhum resultado da própria corrida entrou nas previsões congeladas.

## Fila de 112 itens

| Estado | Quantidade |
|---|---:|
| Conflitos de classificação resolvidos documentalmente | 71 |
| Baku/Q recuperado em fonte alternativa FIA | 1 |
| Estados de qualidade corrigidos | 2 |
| Origem do archive identificada | 1 |
| Ausências confirmadas na tabela oficial | 6 |
| Limitações de pneus confirmadas na origem | 31 |

Os 71 conflitos se dividem em 55 valores do archive confirmados, 11 valores canônicos confirmados e cinco marcações DQ preservadas como categoria própria. Não criamos posição numérica para DQ. As seis ausências não viraram tempos ou causas esportivas inventadas.

Baku/Q 2025: 243 passagens FIA, sendo 223 durações e 20 horários de referência para 20 pilotos. Não foram inventados UTC, setores ou flags de validade. As 31 limitações restantes são 17 casos de stints e 14 de estratégias; as consultas às 17 sessões confirmaram 50 limites ausentes/inconsistentes. A tentativa alternativa FastF1 encontrou 401/404 e parou; isso não demonstra inexistência de dados em toda fonte possível.

## Histórico e circuitos

O Histórico usa identidade literal da pista e data anterior; exclui a corrida atual, futuras e Sprint. Até cinco edições disponíveis são apresentadas por piloto. Austin 2026 usa 2021–2025; Austin 2024 usa 2018, 2019, 2021, 2022 e 2023, sem criar 2020. Madrid não herda Barcelona. DNS/DSQ são registros, não garantia de largada.

As 26 fichas incluem altitude aproximada nas coordenadas do calendário pelo Open-Meteo/Copernicus DEM GLO-90. Austin: 154 m nesse ponto/modelo, sem afirmar altitude mínima/máxima do traçado. Zonas de ativação DRS usam referência FIA 2025; isso não certifica cada configuração histórica. DRS não se aplica em 2026. Recordes posteriores à temporada selecionada não são retroprojetados.

## Evidência pública e reprodução local

O [resumo verificável](evidence/data-resolution.json) registra contagens, hashes e URLs oficiais. Os complementos [de classificação](evidence/qualifying-complements.csv), [voltas FIA](evidence/fia-laps.csv) e a [fila adjudicada](evidence/pendencias.csv) mantêm IDs canônicos e valores originais. As definições em inglês estão no dicionário e no resumo. Caminhos de evidência na fila são referências ao acervo local; documentos brutos e caches não são redistribuídos por esse índice. As URLs oficiais permitem inspecionar as fontes originais; obter dados hoje não prova sua disponibilidade histórica.

A origem do archive foi identificada por metadados do ZIP original, ID Kaggle e igualdade de 14 CSVs. O UTC original continua desconhecido. A licença atualmente declarada não certifica separadamente a versão histórica. As [condições por fonte](../publicacao/templates/FONTES_E_DADOS.md) permanecem distintas.


## Avaliação posterior do México — 0.8.7

A classificação final da FIA admite os 22 alvos de pódio: Lab 2/3, classificação 1/3, zero exclusões. Os cinco abandonos documentados mantêm a posição ausente. O anexo público vincula a avaliação aos hashes da emissão congelada; evidência posterior não altera probabilidades ou rankings. [Relatório de auditoria](../reports/avaliacao_mexico_20261102/relatorio.md).
