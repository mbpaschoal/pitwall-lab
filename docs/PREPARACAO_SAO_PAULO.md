# São Paulo: preparação, alertas e previsão

Português · [English](en/SAO_PAULO_PREPARATION.md)

## Automação admitida em 0.8.26

A [rotina hospedada](AUTOMACAO.md) passa a preparar e tentar uma única emissão prospectiva v1 após o encerramento observado de Q, somente para 2026/20/interlagos. Mantém todas as barreiras do produtor científico, limita tentativas e exige margem de uma hora antes da largada para publicar. O procedimento manual abaixo continua como diagnóstico e recuperação; não deve ser executado em paralelo com o coletor. Não existe previsão de São Paulo nesta entrega.

## O que está preparado

São Paulo está cadastrado como **2026/20/interlagos**, meeting OpenF1 **1299**, com cinco sessões tradicionais. Calendário Jolpica, catálogo OpenF1 e [programação oficial da F1](https://www.formula1.com/en/racing/2026/brazil) foram reconferidos em 03/11/2026. A corrida começa em 08/11 às 14h locais / 17h UTC. TL1: sexta às 12h30; TL2: 16h; TL3: sábado às 11h30; classificação: 15h (todos UTC−3).

A coleta agendada já existente começa sua janela em 05/11 às 12h30 locais, 24 horas antes do primeiro treino. A execução exata depende do agendador do GitHub; o cron não garante horário de execução. Respeita a espera do acesso gratuito e exige encerramento observado, mantendo o México no arquivo de eventos. Não usa a duração programada para afirmar que a sessão terminou.

O GP Tempo foi conferido como alternativa: **evento 21 na fonte**, contra a rodada canônica 20. A união exige país, localidade e data exatos, além da sessão correta. Na captura de 03/11, as cinco sessões estão sem resultados disponíveis; isso não constitui entrada de previsão nem garante disponibilidade futura. [Fontes, hashes e conferência](https://github.com/mbpaschoal/pitwall-lab/tree/main/reports/saopaulo_readiness_20261103).

## Alertas sem repetição

O workflow `maintenance.yml` acompanha a coleta após execuções e também por agenda horária. Uma falha na última execução concluída ou mais de seis horas sem execução concluída abre uma única ocorrência PT/EN no GitHub, atribuída ao proprietário. A repetição da mesma condição não cria comentários nem novas ocorrências. Uma execução saudável recente comenta a recuperação e encerra a ocorrência. Ocorrências manuais não são alteradas.

Uma restrição HTTP da fonte fora da espera normal passa a falhar explicitamente no workflow, preservando dados e capturas. Espera por sessão futura, janela de acesso gratuito, cooldown e ausência de mudança continuam estados normais. As notificações da ocorrência seguem as preferências da conta GitHub; não são enviadas mensagens por e-mail ou por outro serviço pelo código.

## Conferência offline antes da previsão

```sh
python -B -m operacao2026.readiness \
  --evento operacao2026/eventos/saopaulo2026.json \
  --report /private/tmp/saopaulo-preparacao-NOVO-ID.json
```

O destino deve ser novo. O comando não acessa APIs, coleta, treina ou emite previsões. Confere identidade/calendário, janela, horários observados disponíveis e SHA-256 de três artes distintas por par piloto/equipe do catálogo 2026. Essa cobertura é um inventário de artes; não é a lista de inscritos do GP nem escolhe favoritos. A equipe efetiva e a disponibilidade das cartas dos participantes devem ser novamente conferidas após Q. As cartas continuam na janela opcional, com cores da equipe e poses diferentes, sem percentuais sobre a arte.

`aguardando_classificacao` é o estado esperado antes de Q. Mesmo quando a classificação descritiva chega, o estado é `classificacao_recebida_snapshot_preditivo_pendente`, não `pronto`. Uma classificação de México ou de outra sessão não libera São Paulo; horário de encerramento futuro/inconsistente é rejeitado. A janela prospectiva fecha na largada.

## Depois da classificação principal

O acesso gratuito está programado para depois de 07/11 às 16h30 locais / 19h30 UTC, sujeito a atraso real da sessão e da fonte. Não execute a coleta preditiva antes do encerramento observado. O procedimento abaixo prepara um snapshot novo e depois consulta o produtor que decide a prontidão:

```sh
SNAPSHOT="saopaulo-pos-q-$(date -u +%Y%m%dT%H%M%SZ)"
python -B operar_2026.py coletar --id "$SNAPSHOT" --atualizar --classificacao-circuito interlagos
python -B operar_2026.py estado --snapshot "$SNAPSHOT" --temporada 2026 --rodada 20 --circuito interlagos
```

Pare se o estado não for `pronto`. Confira o histórico canônico final do México, as fontes/UTC das janelas v1 e a população efetiva de Q. O complemento descritivo não corrige automaticamente as entradas do modelo. A rota OpenF1 exige a configuração explícita de São Paulo (`--openf1-evento operacao2026/eventos/saopaulo2026.json`), inventário preservado e admissão pelo adaptador; o evento Austin do adaptador não deve ser reutilizado. GP Tempo não está admitido como substituto preditivo.

Somente com os dados reais e o estado `pronto`, informe `--temporada 2026 --rodada 20 --circuito interlagos` ao comando `emitir`, com ID novo, fim observado, URL da evidência e corte UTC atual. Siga a [cadeia operacional](https://github.com/mbpaschoal/pitwall-lab/blob/main/docs/comandos_operacao_2026.md): validar a emissão, registrá-la, gerar o asset, conferir cartas/equipes dos favoritos reais, incrementar versão, exportar, publicar e comprovar a versão pública **antes da largada**. Se faltar dependência ou a janela fechar, mantenha a indisponibilidade explícita. O verificador offline não emite previsões; a rotina hospedada é separada e segue a política explícita.

## Destaque de versão

Novas releases nascem sem substituir `Latest`. Após o pacote terminar de subir, a manutenção escolhe a maior versão estável publicada com ZIP completo e hash, limitada à `VERSION` de `main`. Não escolhe por horário de término do workflow. Uma release antiga que concluir depois não rebaixa a nova, nem se promove uma versão sem pacote. O recibo do job registra a versão escolhida e a conferência após alteração.
