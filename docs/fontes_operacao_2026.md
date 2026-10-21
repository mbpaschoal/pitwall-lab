# Fontes e disponibilidade — operação 2026

## Programação conferida

As páginas oficiais F1 e COTA consultadas em 19/10/2026 indicam classificação de Austin em **24/10**, início **21:00 UTC / 18:00 America/Sao_Paulo**, e corrida em **25/10**, largada **20:00 UTC / 17:00 America/Sao_Paulo**. O fim programado da classificação é 22:00 UTC / 19:00 São Paulo; não é o encerramento observado.[1][2]

A conversão usou `zoneinfo` com America/Chicago e America/Sao_Paulo. O código não fixa a rodada; busca o evento por calendário e circuitId. Singapura foi escolhida previamente pelo critério cronológico de último GP anterior a Austin, sem escolher por qualidade do resultado.[3]

## API e ensaio de acesso real

O contrato de limites consultado recomenda cache e filtros e informa 4 requisições por segundo e 500 por hora, sujeitos a alteração. A implementação adota oito segundos entre acessos e tentativas limitadas, respeitando Retry-After.[4]

A verificação real inicial preservada em `data/operacao_2026/preflight/` recebeu HTTP 200 em três acessos sequenciais: calendário, classificação de Austin e classificação de Singapura. O [registro de disponibilidade](../reports/operacao_2026/disponibilidade_inicial.json) contém URLs, parâmetros, obtenção UTC e hashes dos bytes originais, não respostas simuladas.

- Calendário: **23 eventos** na fotografia da API, não um total anual imposto no programa.
- Austin: rodada **18 descoberta**, classificação com **zero registros**, estado **aguardando classificação**. Nenhuma probabilidade ou favorito foi criado.
- Singapura: rodada **17 descoberta**, classificação com **22 registros publicados**. Isso mede a cobertura da fonte, não certifica uma lista independente de inscritos.

Não foi medida a latência da publicação de Austin: a sessão ainda é futura. Não se promete disponibilidade imediata após a classificação. O preflight não substitui a atualização/validação manual depois da sessão.

## Indisponibilidade e alternativa

A página oficial F1 de Austin está acessível hoje, mas não contém resultado de classificação futuro. A página oficial de [Singapura](https://www.formula1.com/en/racing/2026/singapore) também foi obtida com HTTP 200 para verificar o acesso gratuito ao sítio. A alternativa documentada é consultar a classificação oficial do evento na F1 ou um documento de classificação da FIA, quando publicado; não é garantia de prazo ou de que a informação futura já exista.

Uma transcrição manual exige original preservado, URL, obtenção UTC/hash, identidade do GP, mapeamento explícito verificado para driverId/constructorId, validação e marcação manual. Não unir equipe pelo nome, reutilizar outro GP ou gerar fixture como se fosse publicação oficial. Se esses requisitos não puderem ser satisfeitos, manter espera sem emitir.

As fontes e fotografias identificam o que foi obtido agora, não comprovam a versão histórica dos dados nem fornecem prova externa imutável de horário. O ensaio continuará retrospectivo.

## Sources

[1] https://www.formula1.com/en/racing/2026/united-states
[2] https://circuitoftheamericas.com/event/f1/schedule
[3] https://www.formula1.com/en/racing/2026
[4] https://raw.githubusercontent.com/jolpica/jolpica-f1/main/docs/rate_limits.md
