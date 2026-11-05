# Identidade de Stroll — Espanha 2025

Created by: MBPaschoal  
Status: corrected locally; portable package verified; not published  
Type: implementation report  
Updated: 2026-11-04

[English](README.en.md)

**Resolvido no checkout isolado, versão local 0.10.1:** o carro 18 nas sessões TL1/TL2/TL3/Q da Espanha 2025 passa de `piloto_id: null` para `stroll`. Q mantém P14, Q1 1:13.038 e Q2 1:13.058. Não foi acrescentada participação na corrida nem alterado qualquer tempo, posição, pneu ou probabilidade.

## Causa e confirmação

A normalização canônica usava apenas os números do resultado da corrida. Stroll disputou o qualifying, mas não figura nessa classificação de corrida, de modo que quatro sessões ficaram com identidade OpenF1 e sem ID canônico.

O cruzamento validou temporada/rodada/circuito/data, número 18, quatro cadastros nativos OpenF1 (meeting 1262; sessões 9964–9967), ID Jolpica `stroll` e nascimento `1998-10-29` coincidente no F1DB fixado por hash. Nenhuma associação por semelhança de nome. [Evidência de identidade](identity-evidence.json), [capturas OpenF1](openf1-capture.json) e [revisão aprovada](approved-bundle.json).

## Implementação

O produtor descritivo passa a preservar o número do carro no qualifying. A normalização pode identificar participantes exclusivos dessa sessão e rejeita números que apontem para pilotos ou equipes diferentes entre resultado e qualifying. CSVs antigos sem número continuam sem associação inferida; fontes antigas não são reescritas.

Para a base já publicada, uma revisão pequena, fixada por hash, é aplicada em memória depois das revisões de pneus/fontes. Confere evento, sessão, número e hash completo da linha anterior; altera somente quatro folhas `piloto_id`. Ausência/corrupção da revisão é rejeitada para a base conhecida. O JSON original permanece intacto e os arquivos de pesquisa anteriores conservam seus resultados históricos.

A nova conferência posterior contra F1DB tem **2.967 tempos coincidentes**, 1.032 células ausentes em ambos e **zero pendências de identidade** no recorte comparável de qualifying. Duas células antes fora do pareamento (Q1/Q2 de Stroll) entraram na comparação, já com valores iguais. [Resultado](comparison-after-identity.json).

## Validação e entrega

- **44 testes focais** aprovados: identidade, conflitos, sessões, ausência de número, composição dos complementos e preservação do acervo.
- **150 testes portáteis** aprovados, incluindo admissão de Stroll, composição dos pneus e AppTest PT/EN.
- **733 caminhos científicos protegidos intactos**; [recibo](preservation.json).
- Primeira verificação: um teste antigo de composição esperava somente pneus/fontes e falhou após a introdução da identidade. Foi atualizado para conferir explicitamente a nova composição. O aceite de pneus continua exigindo exatamente 262 idades e verifica separadamente os quatro IDs; não houve relaxamento de seus valores.

Checkout: `/private/tmp/pitwall-stroll-identity-20261104`, branch `codex/stroll-spain-2025-identity`, base remota `4d42c5263caabfff24be2fdcbf1e78fa82e09b01`. Pacote final em `/private/tmp/pitwall-stroll-0101-final/pitwall-dashboard`; logs [focais](focused-tests.txt), [portáteis](portable-tests.txt) e [exportação](export-final.txt). A cópia de entrega e o commit são registrados em `delivery.json`.

Correção descritiva retrospectiva. Sem treino, recalibração, novas previsões, mudança de snapshots/emissões ou inferência de disponibilidade histórica. Esta entrega local não foi enviada ao GitHub nem confirmada no host público.
