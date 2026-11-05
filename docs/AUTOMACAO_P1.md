# Operação automática do prospectivo P1

Created by: MBPaschoal
Status: implemented; activation and live receipts tracked separately
Type: operational documentation

[English](en/P1_AUTOMATION.md) · [Automação geral](AUTOMACAO.md)

## Rotina hospedada

O job `prospective` segue o job `collect` no workflow de coleta já existente. Usa `main` atualizado, após a publicação nativa, e o token temporário do GitHub Actions com `contents: write`. Não exige computador pessoal, PAT, nova chave ou novo cron. O agendamento continua solicitando execução a cada 30 minutos, sujeito a atrasos e indisponibilidade do GitHub. Coletores continuam seriais.

1. Antes de Q, registra espera e não consulta nem escreve releases P1.
2. Após Q observado e emissão prospectiva v1 validada pelo registry, executa o comparador congelado. Confere novamente todas as probabilidades Q, as v1 originais, arquivos, modelos, população e calendário.
3. Publica `paired-probabilities.json` em uma release pública específica do evento, por exemplo `p1-2026-20-interlagos`, sem promover essa release a `Latest`. Recusa substituição de qualquer asset existente. O verificador original consulta metadados sem chave, conferindo digest, tamanho e UTCs do servidor antes de largada−60min, exclusivo.
4. Confere a previsão v1 realmente servida no dashboard em oito contextos novos: Chromium/WebKit, português/inglês e 390/1440 px. Confere versão, controles/idioma, temporada/GP selecionados, favoritos canônicos e as 22 probabilidades do gráfico contra o par original. Capturas, erros de página e tentativas ficam preservados. São larguras emuladas, não aparelhos físicos. Q permanece no asset público; não é apresentado como um novo modelo da interface.
5. Publica `host-acceptance.json` antes da largada. Par público sem essa prova continua sem aceite completo. Em execuções posteriores, reaproveita os mesmos bytes e a prova anterior; não refaz o par nem finge nova observação do host.
6. Depois da corrida e da validação posterior já existente, publica alvos e Brier/log loss descritivos em assets separados, por hash da evidência posterior. Alvo desconhecido permanece desconhecido; DNF/DNS/DSQ seguem o leitor nativo. Não muda elegibilidade, probabilidades ou pesos. Revisões posteriores preservam a primeira fotografia.

## Bloqueios, recuperação e cobertura

A integração preserva o [protocolo público original](https://github.com/mbpaschoal/pitwall-lab/blob/6206fd4c82012e60a0bcad3ebe935efc6406ffeb/reports/prospectivo_p1_20261105/protocolo.md) e seus arquivos. O adaptador verifica o SHA-256 fixo do manifesto e todos os arquivos registrados antes de executar os auxiliares. Esta é a integração operacional prevista no protocolo, sem mudança de receita, janela dos 20 GPs ou critérios científicos.

A política continua admitindo somente **2026/20/interlagos**. Novos GPs/temporadas precisam de calendário, roster, fontes e admissão revistos antes do corte; P1 não autoriza extensão silenciosa. Conflito de fonte, ID de Câmara não resolvido, mudança do horário da largada, entrada parcial ou alteração de modelo bloqueiam a etapa. Não inferir ID/número, ampliar prazo ou substituir v1 para recuperar cobertura.

Tentativas de preparação/publicação e de aceite do host têm contadores duráveis separados nos assets: no máximo quatro por fase, com intervalo mínimo de duas horas. Cada caso de navegador permite duas tentativas; o job inteiro tem 20 minutos. Requisições individuais têm timeout de 30 segundos; falhas de transporte não viram ausência de release. Respostas 403/429/5xx interrompem a execução. Uma falha entre upload e recibo é recuperada baixando os bytes públicos existentes e conferindo-os contra a emissão nativa. O código nunca usa `clobber`, DELETE ou force push.

Se o par faltar quando fechar o prazo, publica um registro de falta de cobertura, sem probabilidades tardias. Se a prova do host faltar na largada, também registra ausência e não a preenche depois. O job falha visivelmente; a manutenção existente acompanha a conclusão do workflow e trata a ocorrência. As provas do par, do host e dos alvos posteriores permanecem separadas. Evidências de execução têm retenção de 90 dias; assets públicos são a evidência durável independente do cache.

## Limites do resultado

O job calcula métricas descritivas por GP. Os checkpoints científicos dos 20 GPs, incluindo cobertura de eventos não admitidos, bootstrap e conclusão comparativa formal, continuam sujeitos ao protocolo; este job não escolhe modelos nem declara vitória a cada corrida. O relatório completo de 20 GPs não é substituído por um recibo individual.

Teste com fixture, CI aprovado ou execução antes de Q não prova captura real após Q, publicação futura ou aceite da previsão de São Paulo. Antes de Q, a execução correta termina em `waiting_for_observed_qualifying`. Após incorporação em `main`, o próximo agendamento assume o trabalho rotineiro, preservando os bloqueios que exigem revisão humana.

Código: [adaptador](../pitwall/operations/prospective.py), [workflow](../.github/workflows/coletar-dados.yml), [aceite do host](../tests/browser/verificar_p1.cjs), [contraprovas](../tests/test_prospective_automation.py).

Referência da API: [releases e publicação](https://docs.github.com/en/rest/releases/releases). Os horários do servidor e o digest são conferidos; um horário local não comprova publicação pública.
