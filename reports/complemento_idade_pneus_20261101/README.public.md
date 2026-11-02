# Idade dos pneus / Tyre age — resumo público

Created by: MBPaschoal
Status: locally completed in draft 0.8.2; integrated into release 0.8.3
Type: data delivery summary

## Português

O complemento revisa somente a idade inicial de 262 stints do acervo, em 55 sessões/47 GPs: 210 valores de zero para positivo, 36 de positivo para zero e 16 entre valores positivos. A revisão de idade não preenche o composto inicial ausente do México. Os demais campos e os snapshots originais permanecem iguais.

O leitor confere hashes, sessão, piloto, composto, limites e idade anterior antes de aplicar a revisão sobre uma cópia em memória. Complemento ausente ou incompatível interrompe a leitura, sem retornar silenciosamente a idades antigas. A base, o modelo e as probabilidades conservam seus bytes. As três fontes e os UTCs estão no complemento; revisão posterior não comprova disponibilidade histórica.

A validação original do rascunho local 0.8.2 registrou 38 testes focais, seis de exportação, 135 portáteis e 12 jornadas locais com comparação de CSVs. A publicação conjunta usa a versão 0.8.3 e possui verificação própria. Os recibos originais e os brutos permanecem locais; os indicadores abaixo preservam o escopo e a data daquela validação.

## English

The complement revises only initial tyre age for 262 archive stints across 55 sessions and 47 GPs: 210 zero-to-positive values, 36 positive-to-zero and 16 changes between positive values. It does not supply the missing initial Mexico compound. Other fields and original snapshots stay unchanged.

The reader verifies hashes, native identities, compound, bounds and previous age before applying an in-memory copy. Missing or incompatible complements fail rather than silently returning known old ages. The original base, model and forecasts retain their bytes. The three source receipts and UTCs are included; later revision does not establish earlier availability.

Original local draft 0.8.2 validation recorded 38 focused tests, six export checks, 135 portable tests and 12 local journeys with CSV comparisons. Joint publication is release 0.8.3 and has separate acceptance. Original raw data and detailed local receipts remain outside this summary; the historical validation scope is preserved below.

## Artefatos / Artifacts

- [Complemento e fontes / Complement and sources](../../frontend_assets/complemento_idade_pneus_v1.json)
- [Leitor / Reader](../../pitwall/data/tyre_age.py)
- [Testes / Regressions](../../tests/test_tyre_age.py)
- [Indicadores locais originais / Original local indicators](validation.json)
- [Entrega conjunta / Joint delivery](../mexico_fontes_alternativas_20261101/README.md)
