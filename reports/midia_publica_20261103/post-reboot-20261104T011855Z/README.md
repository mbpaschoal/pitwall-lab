# Conferência após reinício informado

Português · [English](README.en.md)

Created by: MBPaschoal
Status: post-reboot public acceptance failed
Type: deployment verification

O proprietário respondeu “Feito” ao pedido de reinício administrativo. A [confirmação](context.json) registra quando foi anotada; não presume o horário exato do reboot. Nenhum código, dado ou pacote foi alterado nesta conferência da versão **0.8.28**.

**Resultado: 0/4 contextos aprovados**, PT/EN em 1440/390 px, com tentativas limitadas. Uma abertura mostrou a versão e a foto do México, mas não concluiu os controles; isso não constitui aceite. [Resultado consolidado e hashes](post-reboot-result.json), [todas as tentativas](publication.json), [captura com controles incompletos](1440-pt-1-failed.jpg).

Uma abertura focada de Como funciona chegou ao estado Python `notRunning`, mas manteve os controles como placeholders e depois exibiu `Failed to fetch dynamically imported module`. Foram observadas respostas **500 e HTML** para arquivos JavaScript/fontes nativos sob `/~/+/static/`. [Console, respostas e amostras do DOM](focused-diagnostic.json), [captura](focused-method.jpg), [script diagnóstico](focused-diagnostic.cjs).

Dois dos arquivos JavaScript consultados diretamente mais tarde retornaram 200/application-javascript. Os bytes, com e sem parâmetro de consulta, coincidem com a instalação fixada em Streamlit 1.50.0. Isso não demonstra importação bem-sucedida no navegador nem identifica a causa da falha intermitente. [Respostas diretas](native-resource-probe.json), [comparação correta](pinned-native-comparison.json). A primeira busca local omitiu um nível `static` e está preservada como tentativa inválida, sem ser usada como prova de ausência.

Uma comparação isolada com HTTP/1 também falhou: o módulo nativo principal recebeu 500 e a aplicação não inicializou. Não foi encontrada solução por essa alteração de conexão. [Diagnóstico HTTP/1](http1-diagnostic/focused-diagnostic.json), [script](http1-diagnostic.cjs).

A [ocorrência no repositório oficial do Streamlit](https://github.com/streamlit/streamlit/issues/10510) descreve erro semelhante, sem reprodução confirmada ou correção estabelecida ali. [Consulta preservada](streamlit-issue-10510.json). Ela não prova que a causa do Pitwall seja a mesma.

Foi perguntado ao proprietário se os controles funcionam no seu navegador, para distinguir a experiência observada por ele das sessões automatizadas. A causa permanece aberta. O próximo diagnóstico requer os logs do painel autenticado da hospedagem; a sessão pública disponível não oferece esse controle. Não se recomenda repetir reboot ou trocar dependências sem evidência adicional. As falhas anteriores permanecem preservadas no [relatório da entrega](../README.md).
