# Pilotos: México e atualização agendada

Created by: MBPaschoal
Status: local implementation; publication checks pending
Type: delivery report

Português · [English](README.en.md)

A base descritiva até Austin continua preservada. O complemento desta entrega acrescenta México 2026: 67 GPs, 1.376 resultados, 1.362 largadas e 14 DNS no conjunto. Permanecem oito corridas com chuva registrada nos intervalos efetivos. Cinco posições NC do México não são substituídas por ranks nativos; os duelos contam essas largadas sem criar placares de posição.

A referência é o mapa FIA 2026, Doc. 7, página 2: 17 curvas, sentido horário, 4,304 km. [Captura e hash](acquisition.json). A altitude é aproximação pontual de 2.234 m já documentada no acervo, não intervalo de elevações. O resultado Jolpica previamente capturado e a fonte nativa da release 0.8.20 foram reutilizados, com identidade e hashes conferidos. [Reuso das capturas](captures-acquisition.json). Nenhuma fonte preditiva, probabilidade ou modelo foi reescrita.

## Comportamento e limites

A coleta agendada atualiza o complemento mesmo quando o painel do fim de semana não muda. Repetir dados idênticos não gera uma nova versão. Falhas de qualidade mantêm a última contribuição válida; a tela mostra pendências e o monitor sinaliza atraso superior a seis horas. Retry-After persiste no cache. A atualização exige referência do circuito por edição: o registro desta entrega admite México 2026, e futuros mapas ainda precisam ser conferidos. Não é uma promessa de completude irrestrita de dados futuros.

O perfil de Ryo Hirakawa revelou uma incompatibilidade entre o campo `file` do catálogo e o leitor que pressupunha PNG. A foto JPEG original de alta resolução agora é usada com seu enquadramento e crédito Haas/Simon Galloway; perfis sem foto aprovada têm fallback sem tomar outro rosto. Datas de cobertura e cartões acompanham a projeção validada.

[Contrato PT/EN](../../docs/PILOTOS_ATUALIZACAO.md). Validação, pacote, CI e observação pública serão registrados separadamente após execução real.
