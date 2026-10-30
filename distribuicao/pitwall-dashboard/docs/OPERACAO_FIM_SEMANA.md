# Fim de semana do México · 2026

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

O acompanhamento local depende deste computador e do Codex disponíveis. Não é uma coleta hospedada 24 horas. Se uma fonte atrasar, mantenha a ausência explícita e registre a pendência.
