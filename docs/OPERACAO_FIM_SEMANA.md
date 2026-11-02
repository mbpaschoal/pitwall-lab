# Fim de semana do México · 2026

## Publicação e concorrência

A publicação confere o `main` remoto antes do commit/tag e após uma rejeição do push atômico. Se o ramo avançou, agenda uma execução nova em `main`, com as capturas preservadas e todas as validações refeitas sobre o código e a versão atuais. Não se faz rebase de pacotes gerados nem push forçado. Há até duas recuperações por cadeia; erros de autenticação e limites permanecem explícitos. [Runbook PT/EN](https://github.com/mbpaschoal/pitwall-lab/blob/main/docs/runbooks/automatic-publication.md).

[English](en/WEEKEND_OPERATION.md)

O objetivo é acompanhar o que cada fonte já publicou, sem chamar uma sessão futura de dado observado. Identidade: **2026 / 19 / rodriguez**, meeting OpenF1 **1298**. Configuração auditável: [`mexico2026.json`](https://github.com/mbpaschoal/pitwall-lab/blob/main/operacao2026/eventos/mexico2026.json).

| Sessão | Horário de Brasília | Session key |
|---|---|---|
| TL1 | 30/10, 15h30 | 11397 |
| TL2 | 30/10, 19h | 11398 |
| TL3 | 31/10, 14h30 | 11399 |
| Classificação | 31/10, 18h | 11400 |
| Corrida | 01/11, 17h | 11404 |

Fontes: [calendário F1](https://www.formula1.com/en/racing/2026/mexico), [organizador](https://www.mexicogp.mx/mediacenter/la-guia-mas-completa-para-vivir-el-mexico-gp-2026/) e catálogo público OpenF1. Os horários programados não comprovam o encerramento.

## Coleta e publicação

No ambiente de análise existente, execute **um coletor por vez**:

```sh
.venv/bin/python -B -m operacao2026.weekend --evento operacao2026/eventos/mexico2026.json --publicar-status --preparar-qualificacao
```

O produtor espera o fim programado mais dez minutos e exige `SESSION FINISHED`; a classificação exige Q3. Preserva JSON, URL, status HTTP, UTC e SHA-256. Coleta drivers, resultados da sessão, voltas, pneus, paradas, sensores e controle de corrida. Não consulta telemetria futura. Uma sessão incompleta continua marcada como parcial. Respostas 429 impõem espera persistida de ao menos uma hora ou `Retry-After`, se maior. Dados concluídos usam cache com verificação de hashes; `--rever-concluidas` cria uma nova captura para conferir revisões.

Os originais ficam em `data/operacao_2026/fins_de_semana/`, fora do Git. `frontend_assets/operacao_fim_semana.json` contém apenas a projeção pública. O app lê esse arquivo offline; executar o coletor **não** publica no Streamlit. Cada mudança relevante exige versão, notas PT/EN, exportação, testes, commit/push e conferência da implantação. Mudanças apenas no horário de consulta não justificam uma versão.

O clima previsto vem da [Open-Meteo](https://open-meteo.com/en/docs/), com horário da consulta. O clima observado vem dos sensores OpenF1 durante os intervalos efetivos da corrida, excluindo interrupções; cobertura insuficiente permanece explícita. Temperatura do ar não é temperatura do asfalto. Nenhum serviço pago foi habilitado. Acesso gratuito a dados históricos não garante publicação imediata após cada sessão.

Depois da corrida, campeonatos usam os endpoints oficiais Jolpica da **rodada 19**, com paginação completa. Uma classificação de outra rodada é rejeitada. Novas observações só entram nos rankings históricos de Pilotos após as verificações de clima, pneus, identidade e circuito; coletar os arquivos não basta para aprovar sua interpretação.

## Previsão e avaliação

Após Q3: faça um snapshot novo com `operar_2026.py coletar --id NOVO_ID --classificacao-circuito rodriguez` e confira `estado --snapshot NOVO_ID --temporada 2026 --rodada 19 --circuito rodriguez`. Prefira a classificação canônica. Se ela não estiver disponível, o bundle OpenF1 preservado é admitido apenas com `--openf1-evento operacao2026/eventos/mexico2026.json` e `--openf1-diretorio BUNDLE`, identidade e UTCs validados. Consulte `operar_2026.py emitir --help` para os argumentos completos.

A emissão exige código operacional commitado, modelo congelado, histórico admitido completo e corte após todas as fontes e antes da largada. **Sem emissão e publicação comprovadas antes de 01/11 às 20h UTC, o México fica sem previsão prospectiva.** Não retrodate nem reaproveite Austin. Registre a emissão real em `operacao2026/eventos/emissoes_registradas.json`, preservando as declarações anteriores. O produtor `preparar_dashboard_race_weekend.py --snapshot NOVO_ID` permite usar o snapshot novo na exportação, sem alterar o padrão histórico de Austin.

Acertos do Lab em 2026 considera somente previsões registradas com resultado posterior validado. Não mistura ensaios retrospectivos; uma amostra pequena não demonstra superioridade. O modelo v1, as 15 entradas e as probabilidades existentes continuam congelados.

## Automação hospedada

O [workflow de coleta](https://github.com/mbpaschoal/pitwall-lab/actions/workflows/coletar-dados.yml) substitui o acompanhamento local: executa nos servidores do GitHub a cada meia hora, nos minutos 7 e 37. Não depende do computador pessoal nem de pedidos no chat. Pode haver atraso do agendador, sem garantia de tempo real.

`operacao2026/cloud.py` usa a configuração explícita do México e descobre os próximos GPs de 2026 pelo calendário canônico, data exata e meeting OpenF1. Sessões Sprint são preservadas. Trabalha da véspera do primeiro treino até 48 horas depois da corrida; fora dessa janela não coleta telemetria. Após 16 horas do fim programado da corrida, faz uma conferência de revisões. Uma identidade ambígua interrompe a operação.

As execuções são serializadas, preservam cache e espera entre tentativas e repetem a busca quando uma fonte atrasar. O cache pode ser removido pelo GitHub; nesse caso, uma nova captura tem seu próprio UTC. Os originais também ficam no asset `capturas-originais.tar.gz` das releases automáticas, independentemente do cache. O estado persistido tem limite de 128 MiB e o arquivo comprimido de 32 MiB. Não há tokens nas capturas.

Somente mudanças relevantes geram versão, notas PT/EN, exportação, testes, conferência de navegação, commit/tag e release. Horários de consulta e previsões meteorológicas isoladas não geram uma release; a previsão por hora é renovada junto com dados novos das sessões. O app mostra a última verificação publicada e um link para o workflow. GPs anteriores são preservados em arquivo público próprio, sem emprestar dados do GP seguinte. O mesmo workflow valida a entrega porque commits feitos pelo `GITHUB_TOKEN` não disparam outros workflows de push. Uma falha aparece no histórico do Actions; o horário exibido não é avançado artificialmente.

Usa executores Linux padrão de repositório público, sem habilitar serviços pagos ou aumentar limites de armazenamento. Cache e registros têm seus limites próprios. Os testes de navegador do produto retêm evidências por três dias. [Custos do GitHub Actions](https://docs.github.com/en/billing/concepts/product-billing/github-actions).

Esta automação coleta e publica contexto descritivo. Não treina modelos nem emite probabilidades: as regras de emissão prospectiva acima continuam obrigatórias.

## Cadastro ausente em uma sessão

Se um número aparece nos resultados, voltas, pneus ou paradas mas seu cadastro está ausente, a sessão fica parcial e apenas as tabelas/projeções que dependem desse cadastro ficam bloqueadas. Os originais, recibos e número sem cadastro são preservados. A coleta das outras sessões continua, sem copiar nomes de outra sessão ou GP. Sessões parciais são consultadas novamente nas execuções seguintes. Duplicações, conflitos de voltas e sessões divergentes continuam interrompendo a coleta; a exceção se restringe ao cadastro ausente.

### Ocorrência verificada em 01/11/2026

No TL3 (`11399`), a captura trouxe 22 resultados e 21 cadastros: o número 30 aparece nos resultados/voltas/pneus, mas falta em `drivers`; a consulta específica retornou 404. Paradas de TL3 e classificação (`11400`) também contêm o número 236 sem cadastro. A classificação mantém seus 22 resultados, voltas e pneus válidos; só suas paradas ficam retidas. TL3 mantém os grupos afetados bloqueados, com os números e grupos registrados em `qualidade_identidade`. Nenhum nome foi inferido ou copiado de outra sessão. A cobertura publicada distingue sessão parcial de corrida futura.

A correção foi testada com cadastro ausente, continuação até Q, conservação de resultados válidos, duplicações e conflitos de voltas. A comparação da previsão do México aguarda o resultado posterior validado; esta recuperação não reemite probabilidades.

Fontes: [cadastros TL3](https://api.openf1.org/v1/drivers?session_key=11399), [resultados TL3](https://api.openf1.org/v1/session_result?session_key=11399), [paradas Q](https://api.openf1.org/v1/pit?session_key=11400). A disponibilidade pode mudar após as capturas registradas.

## Revisão pós-corrida — 0.8.1

A [política da OpenF1](https://openf1.org/#faq) classifica como ao vivo os 30 minutos anteriores e posteriores às sessões. A coleta gratuita agora aguarda essa janela, sem autenticação paga. Isso explica os 401 observados nas execuções agendadas; não significa inexistência dos dados históricos. Fora da janela, falhas de identidade ou catálogo continuam interrompendo a operação.

Se o catálogo continuar respondendo 401/403, a execução registra `provider_access_restricted`, preserva a resposta bruta e mantém os dados públicos anteriores. O próximo horário agendado tenta novamente; não há repetição imediata nem contratação automática. Essa restrição de acesso não é tratada como uma coleta bem-sucedida ou como ausência de resultados.

O catálogo do México estendeu o fim programado de Race de 22h para 23h UTC; a revisão e o SHA da fonte estão na configuração. Essa alteração serve à espera da coleta. O encerramento efetivo observado foi 22:23:54 UTC e não foi substituído pelo horário programado.

A corrida trouxe 205 medições meteorológicas e 1360 registros de voltas. A fonte também incluiu 12 mensagens anteriores ao início declarado, com IDs da corrida. A janela de clima registra seus índices e as exclui por contexto temporal, sem apagar o bruto ou usar a programação como largada real. O início e a retomada reais continuam necessários; um segundo início dentro da sessão, sem suspensão, continua inválido. A interrupção entre 21:06 e 21:45 UTC fica fora das médias. A média do ar é 24,2 °C. A média bruta do asfalto (40,3 °C) fica retida para revisão: inclui uma leitura isolada de 0 °C entre 37,4 e 37,5 °C.

Há três sessões completas de cinco. TL3 permanece parcial pelo cadastro 30 ausente e paradas 236 sem cadastro; Q preserva resultados/voltas/pneus e retém as paradas afetadas. Resultado OpenF1 observado e campeonatos da rodada 19 são contexto posterior. A emissão do México e suas probabilidades não foram alteradas; sua admissão à avaliação do modelo continua uma etapa separada.

O calendário também foi confrontado com a F1: [Bahrein na Malásia é um evento oficial em Sepang](https://www.formula1.com/en/latest/article/formula-1-and-fia-confirm-that-malaysia-will-join-the-2026-calendar-as-host-venue-for-the-bahrain-grand-prix.6lL7vjFEM2VVynRHvg1TCf). Nome do evento, país anfitrião e circuito são campos distintos; a apresentação não altera a identidade canônica.

## Fontes alternativas — entrega 0.8.3

A revisão documental recupera os 22 tempos do TL3 e identifica Lawson por número, nome e equipe na lista oficial deste evento. O recorte temporal exclui um registro de paradas anterior ao TL3 e 84 anteriores à classificação; os originais não são apagados. A classificação final e a decisão dos comissários mostram Lawson como DSQ, sem posição numérica nem tempos válidos.

A média do asfalto agora usa 100 leituras válidas: 40,7 °C, 98,0% de cobertura, sem interpolação. O relatório FIA também registra o zero anômalo; ele não revela a temperatura real daquele minuto. Permanece ausente o composto do stint inicial de Lawson (voltas 1–8 do TL3), não inferido dos stints posteriores. A revisão aplica-se também ao cache e à automação. [Fontes, decisões e pendências](https://github.com/mbpaschoal/pitwall-lab/blob/main/reports/mexico_fontes_alternativas_20261101/README.md).
