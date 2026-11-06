# Automação do Pitwall Lab

Português · [English](en/AUTOMATION.md)

A rotina principal fica no GitHub Actions, sem depender de o computador pessoal estar ligado. O cron solicita execução a cada 30 minutos; o GitHub pode atrasar o início. Fontes gratuitas, coleta serial, cache e `Retry-After` continuam obrigatórios. A interface só lê os arquivos publicados.

O prospectivo P1 acrescenta preparação e publicação imutável do par v1/Q, recibo externo, aceite real das 22 probabilidades em PT/EN e métricas posteriores separadas. O job segue a coleta existente, com tentativas limitadas e sem treino. [Operação P1 e bloqueios](AUTOMACAO_P1.md).

| Etapa | Situação e controle |
|---|---|
| Descobrir o próximo GP e ligar calendários | Automática pela identidade e data, nunca pelo número de rodada de outra fonte. |
| Coletar treinos, Q, corrida, voltas, pneus e paradas | Automática após encerramento observado e espera de acesso gratuito. |
| Clima durante a corrida | Sensores nos intervalos efetivos; qualidade e cobertura validadas. Previsão Open-Meteo fica separada. |
| Campeonatos completos | Consulta à rodada exata; sem reconstrução por soma parcial. |
| Atualizar comparativos de Pilotos | Automática depois da corrida, após conferir resultado, população, clima e circuito. |
| Referências das quatro pistas restantes de 2026 | Admitidas nesta entrega com mapas oficiais F1 de 2026, revisão visual e hashes. Altitude Open-Meteo é aproximação pontual. |
| Conferir referências futuras | Checagem offline com sete dias de antecedência; falta de referência gera ocorrência. |
| Preparar previsão de São Paulo | Nova rotina hospedada, condicionada a Q realmente encerrada. Não existe previsão de São Paulo nesta entrega. |
| Emitir e registrar v1 | Automático apenas para **2026/20/interlagos**, passando pelo CLI científico existente. Exige snapshot validado, 22 pilotos, fontes/UTC admitidas, código commitado e lista de pilotos compatível com as substituições revisadas. Sem treino ou ajuste do modelo. |
| Repetir uma tentativa de previsão | Até quatro tentativas, separadas por pelo menos duas horas. Depois, bloqueia e alerta; não consulta indefinidamente. |
| Recuperar publicação concorrente | Retoma os mesmos bytes da emissão e nova projeção em `main`; não recalcula probabilidades nem força push. |
| Versionar e publicar dados | Nova versão só quando existe mudança real; notas PT/EN, pacote, testes, fontes e push atômico. |
| Publicar previsão dentro do prazo | Reconfere antes do push; margem mínima de uma hora para a largada. Se a janela fechar, preserva a emissão sem publicá-la. |
| Conferir pacote, idiomas e navegação | O CI de código/versão roda as duas suítes completas (12 aceites: 11 anteriores e o ensaio do verificador público), além de sete contraprovas. A publicação automatizada de dados roda quatro aceites focais e as verificações do pacote. |
| Downloads CSV e SVG | Testes PT/EN em computador e celular verificam bytes, idioma e ausência de reexecução da página. |
| Alertar sobre falha ou atraso | Uma ocorrência PT/EN no GitHub; repetições não criam comentários. Recuperação saudável encerra a ocorrência. |
| Escolher `Latest` | Maior versão estável com ZIP completo e hash, limitada à versão de `main`. |

## Pilotos substitutos e artes opcionais

A revisão de São Paulo exige Rafael Câmara na Haas e rejeita uma classificação que ainda contenha Ocon. O nome é conferido literalmente no registro da fonte; não é usado para unir ou inventar IDs. O `driverId` original da classificação canônica permanece intacto. Na rota OpenF1, um piloto novo continua exigindo mapeamento literal revisado. A consulta de preparação de 03/11 ainda não identificava Câmara nas APIs; não é um snapshot de classificação.

A disponibilidade de cartas é registrada em `artwork_coverage`. Uma arte ausente ou não verificada gera indicação de indisponibilidade, sem emprestar o rosto de outro piloto nem impedir uma previsão válida. As barreiras científicas, a população de 22 pilotos e as regras de prazo permanecem obrigatórias. A falta de histórico próprio de um estreante conserva contadores zero, médias ausentes e os indicadores já previstos pelo v1; não recebe o histórico de quem substituiu. [Fontes, artes preparadas e verificações](../reports/camara_preparacao_20261103/README.md).

## O que continua exigindo revisão

Conflitos entre fontes, mudanças de piloto/equipe sem mapeamento literal, leituras anômalas e revisões de traçado não são decididos por média ou aproximação. O sistema preserva a última informação válida e sinaliza a pendência. Novas artes, uso/licença de imagens e alterações editoriais passam por revisão visual. Treinar, recalibrar ou promover outro modelo continua sendo uma pesquisa separada, sem promoção automática.

Os outros GPs podem receber coleta e comparações descritivas automaticamente. A permissão de emissão desta entrega cobre São Paulo; a política explícita evita liberar previsões para eventos não admitidos.

## Operação e evidência

- [Coleta e previsão](../.github/workflows/coletar-dados.yml), [política admitida](../operacao2026/forecast_policy.json) e [orquestrador](../operacao2026/post_qualifying.py).
- [Preparação de São Paulo](PREPARACAO_SAO_PAULO.md) e [atualização de Pilotos](PILOTOS_ATUALIZACAO.md).
- [Relatório desta entrega](../reports/automacao_saopaulo_20261103/README.md).

Erros da previsão não impedem publicar dados descritivos válidos. Tentativas preservam diagnósticos e arquivos no estado persistido; capturas de uma tentativa nova também vão para um artefato de execução por 30 dias. Emissões publicadas e seus raws entram no Git e no arquivo de fontes da release. Cache não é prova externa de publicação; CI, release e versão servida são conferências distintas.


Na conferência pública de 0.8.26, CSV e SVG em inglês foram baixados no Android emulado sem reexecução da página. Algumas outras entradas falharam ao carregar a hospedagem, módulos do Streamlit ou completar o download. Esses limites continuam registrados; não se declara a matriz pública inteira aprovada. [Recibos e tentativas](../reports/automacao_saopaulo_20261103/README.md).

## Confirmação automática da versão pública

Após publicar novos dados, o verificador abre quatro contextos novos: PT/EN em 390/1440 px. Confere Corridas e Como funciona, o GP efetivamente coletado, controles prontos, fontes de ícones, fotos decodificadas e SHA de originais/variantes admitidos, além do build do pacote. A versão visível sozinha não basta.

Cada caso admite duas tentativas, com prazo total de seis minutos para o conjunto. Falhas por integridade não são repetidas; falhas de inicialização mantêm as duas tentativas. JSON e capturas ficam em artefato por 30 dias, inclusive quando a conferência falha. A falha aparece no workflow e é acompanhada pelo monitor existente da coleta. Isso não exige nova coleta, mudança do modelo ou navegação com inferência. A confirmação pública após uma release manual continua sendo uma etapa separada, não substituída pelo CI local.

[Verificador](../tests/browser/verificar_publicacao.cjs), [contraprovas](../tests/browser/test_verificar_publicacao.cjs) e [evidências da revisão](../reports/midia_publica_20261103/README.md).


## Navegação e conferência pública — 0.8.29

O CI completo também roda nas branches `codex/**`, permitindo validar a correção antes de atualizar main. O grupo core acrescenta `aceite_resiliencia.cjs`: bloqueio dos módulos Radio/Button, seis destinos, PT/EN, teclado, contexto, alvos de toque e recuperação tardia sem perda de foco. Os 12 aceites anteriores permanecem.

O verificador público v2 registra o controle realmente utilizável (nativo/link/misto), clica alternativas e troca o idioma, conferindo URL externa e iframe. Mantém identidade, fotos decodificadas/hashes, build, ausência de transbordamento e erros visíveis não recuperados. Limites: duas tentativas por caso, 120 segundos por tentativa e oito minutos no conjunto; o step tem dez minutos. A evidência permanece por 30 dias. Esse aceite é posterior à publicação de dados, não monitoramento contínuo ou prova da causa de uma falha da hospedagem.

## Recuperação da projeção de previsões — 0.12.5

O registro novo precisa estar disponível para o leitor da projeção, mas não deve permanecer confirmado quando essa projeção falha. O orquestrador conserva os bytes anteriores do registro, gera o novo asset em uma pasta exclusiva `projection-*` junto à tentativa retida e exige um objeto JSON legível antes de substituir `frontend_assets/race_weekend.json` por renomeação.

Se a etapa falhar, o asset anterior permanece disponível e o registro retorna aos mesmos bytes anteriores; sem registro anterior, apenas o registro criado nessa tentativa é retirado. A saída parcial da projeção permanece como evidência no estado persistido. A retomada usa a emissão já retida e reexecuta a apresentação, sem nova coleta ou cálculo de probabilidades. As validações de fontes, população e prazo continuam obrigatórias.
