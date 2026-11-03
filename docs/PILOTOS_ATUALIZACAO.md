# Atualização das análises de Pilotos

Português · [English](en/DRIVER_UPDATES.md)

A versão 0.8.22 incorpora o México 2026 às comparações: 67 GPs, 1.376 resultados e 1.362 largadas. A base original até Austin permanece idêntica. O complemento é descritivo e nunca entra nas 15 variáveis nem altera probabilidades ou emissões v1.

## Como funciona

O GitHub Actions executa a coleta serial a cada 30 minutos durante a janela operacional, respeitando o acesso gratuito e as esperas da fonte. Depois do encerramento observado da corrida, `operacao2026/driver_archive.py` confere identidade, população completa, largadas, voltas, pontos e desclassificações entre o resultado canônico Jolpica e a fonte nativa OpenF1 já capturada. Usa as posições da revisão oficial: NC não vira colocação presumida. Só então acrescenta o GP ao complemento `frontend_assets/pilotos_condicoes_operacao.json`, ligado ao hash da base.

Chuva e sensores usam os intervalos efetivamente disputados, excluindo pausas por bandeira vermelha e a leitura anômala já adjudicada no México. Curvas, comprimento e sentido exigem referência da edição em `operacao2026/driver_circuit_reviews.json`. **O registro desta entrega admite México 2026.** A admissão dos mapas dos próximos GPs ainda é uma revisão humana documentada; sem ela, a automação mantém o GP pendente. Não reutiliza mapas de anos anteriores como se fossem certificados para 2026.

Recebimentos idênticos não geram versões; uma mudança substantiva gera nova versão, notas PT/EN, pacote e publicação após validação. Isso funciona mesmo quando só Pilotos muda. O navegador lê arquivos locais e não consulta APIs. A tela e os cartões de compartilhamento informam a corrida mais recente validada.

## Falhas e limites

Uma divergência mantém a última contribuição válida e uma pendência explícita na interface. Após seis horas do encerramento, a checagem falha e o monitor de coleta existente abre ou atualiza uma ocorrência; repetições permanecem silenciosas. Uma fonte inválida ou hash alterado interrompe a execução. `Retry-After` persiste entre execuções. Dependências que ainda não foram publicadas podem exigir conferência, sem precisar de lembretes periódicos do usuário.

Abandonos contam nas largadas. Médias de colocação e o placar de duelos usam somente posições oficiais conhecidas, sem DSQ. As condições se sobrepõem e não isolam o efeito do carro. A ausência de retrato não impede o perfil nem autoriza usar a foto de outro piloto.

## Evidência

- [Relatório da entrega](../reports/pilotos_atualizacao_20261103/README.md).
- [Resultado canônico capturado](../reports/saopaulo_readiness_20261103/admitted-sources/mexico-results.json).
- [Mapa FIA da edição 2026](https://www.fia.com/system/files/decision-document/2026_mexico_city_grand_prix_-_competition_notes_-_circuit_map_pit_lane_drawing_and_emergency_exits_map.pdf), página 2, Doc. 7: 17 curvas, sentido horário, 4,304 km. Altitude de 2.234 m é aproximação pontual Open-Meteo, não amplitude do circuito.
- Testes de atualização: `tests.test_driver_updates`; integração da coleta: `tests.test_weekend_cloud`; projeção portátil: `tests.test_driver_projection`; perfil e idiomas: `tests.test_pilot_views`.
