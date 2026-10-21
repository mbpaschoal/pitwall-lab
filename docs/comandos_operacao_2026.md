# Operação 2026 — comandos manuais

Created by: MBPaschoal
Status: coleta real, cache e ensaio retrospectivo executados; Austin aguardando classificação
Type: operational guide

Use a raiz do projeto e o ambiente Python já instalado, **sem instalar nada**:

```sh
cd "/Users/MBPaschoal/Dropbox/Projetos pessoais/F1"
```

Não execute dois coletores ao mesmo tempo. Os IDs devem ser novos; uma pasta existente nunca é substituída. Nenhuma etapa abaixo é agendada automaticamente.

## A. Atualizar o histórico disponível

```sh
SNAPSHOT="coleta-$(date -u +%Y%m%dT%H%M%SZ)"
./.venv/bin/python operar_2026.py coletar --id "$SNAPSHOT" --atualizar
```

O programa descobre as rodadas no calendário, coleta somente GPs principais liberados até o corte atual e consulta a classificação principal de Austin e Singapura. Não presume número de pilotos. O intervalo mínimo é oito segundos, tentativas são limitadas, `Retry-After` excessivo interrompe e o lock serializa a coleta.

Sem `--atualizar`, resultados completos e validados podem vir do cache, preservando bytes e UTC original; calendário e classificações são consultados novamente. Falha não autoriza repetir indefinidamente nem apagar uma pasta parcial: examine a mensagem e use outro ID depois de resolver a causa.

**Executado em 19/10/2026:** `coleta-20261019T164713Z`: 17 GPs, 374 resultados, nenhuma lacuna passada e seis eventos futuros. `cache-verificado-20261019` reutilizou os 17 resultados e fez apenas três novas consultas (calendário e duas classificações), preservando UTC/hash do cache.

## B. Consultar Austin e repetir o ensaio de Singapura

Pode usar o snapshot criado em A. Para repetir somente o ensaio, sem nova coleta, use a fotografia já existente:

```sh
SNAPSHOT="coleta-20261019T164713Z"
./.venv/bin/python operar_2026.py estado --snapshot "$SNAPSHOT"
ENSAIO="ensaio-singapura-$(date -u +%Y%m%dT%H%M%SZ)"
./.venv/bin/python operar_2026.py ensaio --snapshot "$SNAPSHOT" --id "$ENSAIO"
```

Singapura foi escolhida antes da coleta, por critério cronológico, não por desempenho. A saída é **ENSAIO RETROSPECTIVO**, nunca uma previsão registrada antes daquele GP. Fonte obtida agora não prova disponibilidade histórica. Não há avaliação de acerto nem ajuste por desempenho nesta etapa.

O leitor seleciona `endpoint` e `rodada` no índice **antes** de abrir/hash/JSON dos resultados. Não abre o resultado de Singapura nem posteriores para prever Singapura. A emissão preserva calendário, classificação e resultados anteriores admitidos. Para Austin, classificação vazia significa `aguardando_classificacao`, sem carregar modelo ou inventar favoritos.

## C. Após a classificação principal de Austin — execução futura manual

Início programado: **24/10/2026 às 21h UTC / 18h de São Paulo**. Largada programada: **25/10/2026 às 20h UTC / 17h de São Paulo**. Reconfirme as sessões oficiais: programação não comprova encerramento nem garante publicação imediata na Jolpica.

Depois de confirmar que a classificação terminou, colete uma fotografia nova:

```sh
SNAPSHOT="austin-pos-q-$(date -u +%Y%m%dT%H%M%SZ)"
./.venv/bin/python operar_2026.py coletar --id "$SNAPSHOT" --atualizar --classificacao-circuito americas
./.venv/bin/python operar_2026.py estado --snapshot "$SNAPSHOT"
```

**Se o estado não for `pronto`, pare.** Não use outra classificação, não repita consultas infinitamente e não invente o fim da sessão. Guarde uma URL verificável de confirmação do encerramento; o fim meramente programado não serve como observação.

Somente com `pronto`, informe os dados observados quando os comandos abaixo perguntarem:

```sh
printf 'Fim confirmado da sessão em UTC (AAAA-MM-DDTHH:MM:SSZ): '
read -r FIM_Q
printf 'URL http(s) da evidência de encerramento: '
read -r FONTE_Q
CORTE="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
EMISSAO="austin-prospectivo-$(date -u +%Y%m%dT%H%M%SZ)"
./.venv/bin/python operar_2026.py emitir --snapshot "$SNAPSHOT" --id "$EMISSAO" --sessao-encerrada-em "$FIM_Q" --fonte-encerramento "$FONTE_Q" --corte "$CORTE"
```

O código exige: início Q ≤ fim confirmado ≤ obtenção de **cada página de Q** ≤ corte ≤ validação da publicação < largada. Calendário, resultados de 2026 e cada fonte histórica **admitida** precisam ter UTC válido e não posterior ao corte; somente as páginas de Q têm também o limite inferior do fim confirmado. As datas são comparadas como instantes UTC, não como texto.

Para o legado 2021–2025, o leitor ainda confere hash e abre as páginas necessárias para indexar a proveniência, mas a admissão prospectiva é determinada exatamente pelas dependências das janelas v1 já formadas: resultados dos GPs presentes nas últimas cinco participações de cada piloto ou nos últimos cinco GPs da equipe, mais as páginas de calendário dos anos desses GPs. Uma página mista é admitida se contiver algum GP necessário. As demais ficam listadas como abertas, porém excluídas por ausência de contribuição; seu UTC original, inclusive `desconhecida`, não é alterado. Se uma fonte sem UTC for necessária, a emissão é bloqueada — não há imputação por mtime, commit, verificação local ou nova coleta automática. `historicos.json` separa resultados lidos dos resultados efetivamente fornecidos à matriz, e o manifesto preserva origem, hash, timestamp e associação de eventos de cada raw legado.

Exige identidade exata, paginação completa, IDs literais válidos, horários conhecidos e componentes operacionais commitados e intactos. O lote é preparado separadamente e validado antes e depois da publicação, inclusive durante serialização, escrita e após a troca atômica: se atravessar a largada, não resta uma pasta final válida; os bytes são preservados apenas como parcial inválida para diagnóstico. Não existe opção CLI para retrodatá-lo. Alterações no cofre fora desses componentes não bloqueiam a emissão. Se a verificação falhar, não contorne o bloqueio; uma nova consulta exige nova fotografia.

Uma correção usa ID novo e ambos os argumentos `--versao-anterior ID_ANTERIOR --motivo-correcao MOTIVO_DOCUMENTADO`, nunca substituição. Não reexecute o comando com um ID já emitido.

## Saídas, limitações e alternativa gratuita

Cada emissão contém `probabilidades.csv`, `entradas.json` (15 entradas em ordem), `cobertura.json`, `historicos.json`, `fontes.json`, raw admitidos, `relatorio.md` e `manifesto.json` com hashes/modelo/Git. O ensaio de desenvolvimento identifica código ainda não commitado; a fotografia final pós-commit identifica o commit real dos componentes. Arquivos locais, relógio e commit **não são prova externa imutável** de uma previsão anterior ao GP.

Cobertura é sobre os registros de classificação publicados, não lista independente de inscritos. Não se garante todo o pelotão se a fonte estiver incompleta. A política operacional é conservadora: se qualquer GP principal anterior já admitido ao alvo tiver resultado indisponível (inclusive resposta vazia), a emissão é bloqueada; não se interpreta a lacuna da fonte como ausência de participação. Em emissão completa, `cobertura.json` e `relatorio.md` registram a lista vazia de lacunas relevantes e a política aplicada. Novos IDs são literais, sem união manual de equipes. A constante, imputação, escalas e coeficientes permanecem os do v1; desempenho de 2024/2025 não garante calibração em 2026. Probabilidades não são ordem P1/P2/P3 e não são forçadas a somar três.

Se a API atrasar, mantenha a espera. Alternativa gratuita verificável: classificação oficial F1 do evento ou documento FIA. Uma transcrição manual precisa preservar original/URL/UTC/hash, evento, mapeamento literal verificado e responsável, e deve ser marcada manual. **Não há importador manual implementado**: sem esses controles e sem implementação validada, este CLI permanece bloqueado. Veja [protocolo](protocolo_operacional_2026_v1.md) e [fontes](fontes_operacao_2026.md).
