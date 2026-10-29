# Dados atuais, correções e limites

Português · [English](en/CURRENT_DATA.md)

O acervo é descritivo e separado das entradas v1: 66 GPs/330 sessões de 2024–2026 até Austin. A aquisição complementar de 29/10 foi serial e cacheada. Os nove artefatos científicos e as emissões anteriores foram preservados.

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
