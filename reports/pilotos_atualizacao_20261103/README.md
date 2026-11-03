# Pilotos: México e atualização agendada

Created by: MBPaschoal
Status: local tests and package passed; public verification pending
Type: delivery report

Português · [English](README.en.md)

A base descritiva até Austin continua preservada. O complemento desta entrega acrescenta México 2026: 67 GPs, 1.376 resultados, 1.362 largadas e 14 DNS no conjunto. Permanecem oito corridas com chuva registrada nos intervalos efetivos. Cinco posições NC do México não são substituídas por ranks nativos; os duelos contam essas largadas sem criar placares de posição.

A referência é o mapa FIA 2026, Doc. 7, página 2: 17 curvas, sentido horário, 4,304 km. [Captura e hash](acquisition.json). A altitude é aproximação pontual de 2.234 m já documentada no acervo, não intervalo de elevações. O resultado Jolpica previamente capturado e a fonte nativa da release 0.8.20 foram reutilizados, com identidade e hashes conferidos. [Reuso das capturas](captures-acquisition.json). Nenhuma fonte preditiva, probabilidade ou modelo foi reescrita.

## Comportamento e limites

A coleta agendada atualiza o complemento mesmo quando o painel do fim de semana não muda. Repetir dados idênticos não gera uma nova versão. Falhas de qualidade mantêm a última contribuição válida; a tela mostra pendências e o monitor sinaliza atraso superior a seis horas. Retry-After persiste no cache. A atualização exige referência do circuito por edição: o registro desta entrega admite México 2026, e futuros mapas ainda precisam ser conferidos. Não é uma promessa de completude irrestrita de dados futuros.

O perfil de Ryo Hirakawa revelou uma incompatibilidade entre o campo `file` do catálogo e o leitor que pressupunha PNG. A foto JPEG original de alta resolução agora é usada com seu enquadramento e crédito Haas/Simon Galloway; perfis sem foto aprovada têm fallback sem tomar outro rosto. Datas de cobertura e cartões acompanham a projeção validada.

[Contrato PT/EN](../../docs/PILOTOS_ATUALIZACAO.md). Validação, pacote, CI e observação pública serão registrados separadamente após execução real.


## Verificação local

349 testes de código aprovados e 31 reconferências após o ajuste dos créditos; 143 testes do pacote final. O aceite focal do pacote final passou em quatro combinações PT/EN e desktop/Android, com CSV e SVG reais e SHA da foto original. A varredura visual prévia passou em 24 cenários nas seis telas. 231 arquivos protegidos conferidos contra `bb83c75`, sem alteração. [Pacote e hash](package.json) · [Fonte](source-tests.json) · [Pacote](package-tests.json) · [Navegador final](browser-final-local/acceptance.json) · [Integridade](protected-integrity.json). Implementação em cópia isolada, preservando os rascunhos da raiz original.


## Correção após a primeira execução hospedada

A primeira coleta em `41704012731` falhou porque o construtor real do cliente tentou salvar o manifesto antes de existir a pasta da consulta. Os testes anteriores exercitavam cache válido ou clientes substitutos e não expunham essa pré-condição. A 0.8.23 cria a pasta explicitamente e testa o cliente real com respostas HTTP controladas de sucesso e 429. A interrupção real por 429 também mantém Retry-After persistido. A 0.8.22 e seus recibos ficam preservados, sem reescrever a tag. A falha inicial não alterou os dados publicados.


0.8.23: 351 source tests / testes de código, 143 portable tests / testes do pacote; four final-package browser cases / quatro casos de navegador finais em PT/EN e desktop/Android. [Package / Pacote](package.json) · [Browser / Navegador](browser-local-023/acceptance.json).


## Correção dos retratos e pacote 0.8.24

O CI de navegação da 0.8.22 detectou a falta de imagem no perfil de Norris: o catálogo legado usa identidade literal no nome do arquivo, enquanto o leitor novo exigia `driver_id`. A correção preserva ambos os formatos e confere os 29 retratos. A 0.8.24 passou em 352 testes de código, 144 do pacote, quatro casos focais e na jornada completa de navegação que detectou a regressão. [Jornadas completas](exploration-local-024/evidence.json) · [Quatro casos finais](browser-local-024/acceptance.json). Versões anteriores e suas falhas ficam auditáveis; nenhuma tag foi reescrita. O monitor abriu automaticamente a ocorrência 1 pela falha da coleta inicial; a recuperação ainda precisa ser confirmada na execução corrigida.


## Recuperação automática comprovada

A coleta corrigida [41705250105](https://github.com/mbpaschoal/pitwall-lab/actions/runs/41705250105) consultou Jolpica com HTTP 200 em 19:45:21 UTC e confirmou 67 GPs, sem pendências ou mudança substantiva. A execução não criou nova versão. A ocorrência [1](https://github.com/mbpaschoal/pitwall-lab/issues/1), aberta automaticamente pela falha anterior, foi encerrada pelo monitor em 19:45:41 UTC. [Recibo](collector-recovery.json).


## Aceite corrigido, 0.8.25

O CI da 0.8.24 passou nas suítes anteriores ao contexto de busca, mas quatro verificações de Audi exigiam a rodada 18, embora a busca corretamente oferecesse o México/19. A reprodução local registra `19 !== 18` nos quatro contextos. A correção exige a última corrida validada da equipe, preserva ano/rodada/destino e passou nos mesmos quatro contextos. As 11 suítes permanecem; dois grupos independentes precisam aprovar antes da release. [Reprodução](search-context-stale-reproduction/interactions.json) · [Correção](search-context-corrected/interactions.json) · [Matriz preservada](browser-matrix.json).

O pacote 0.8.25 tem 352 testes de fonte e 144 do pacote aprovados. Código e dados de runtime são byte a byte iguais aos da 0.8.24; apenas versão, changelogs, comentário de dependências e manifesto diferem. [Comparação](package.json). A prova pública e a release finais serão registradas após sua conclusão.
