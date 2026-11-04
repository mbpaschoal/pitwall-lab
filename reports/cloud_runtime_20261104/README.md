# Navegação e idiomas durante falha de carregamento

Português · [English](README.en.md)

Created by: MBPaschoal
Status: v0.8.29 published; public reliability not accepted
Type: implementation and deployment evidence

## Resultado

A correção está em main, commit `8235954`, e na [release 0.8.29](https://github.com/mbpaschoal/pitwall-lab/releases/tag/v0.8.29). Os CIs completos da branch, main e tag passaram. O ZIP da release foi reconstruído pelo exportador canônico no GitHub: **481 membros conferidos individualmente**, 665.858.928 bytes e SHA-256 `5b792ecc42e991e3af99b70eb653707531669f8dbf7443e7b2c8f4369b765538`. O digest e tamanho publicados pela API coincidem com o recibo do job. [CI e release](published-ci-release.json).

O build público `03691f8190da92ec913a1868175ebf0e236b74f7106177010c7eed0f542dcfab` foi observado, com fotos, controles e troca de idioma reais. **A estabilidade pública continua reprovada**: o aceite completo passou em apenas um dos quatro contextos, e todos os erros das demais tentativas estão preservados. [Aceite público](public-029/publication.json). O relatório adicional das seis páginas e o diagnóstico de camadas têm resultados próprios; não substituem esse aceite.

## Problema e mudança

O proprietário confirmou que menu e bandeiras travavam mesmo após reboot. A [conferência anterior](../midia_publica_20261103/post-reboot-20261104T011855Z/README.md) preserva os erros nativos 500 e de importação dinâmica. Agora o menu e as bandeiras também oferecem links normais enquanto seus componentes não carregam. Os links preservam destino, GP, idioma, filtros aplicáveis e teclado. Quando os controles nativos chegam, os links somem sem duplicar a navegação ou retirar o foco de quem os está usando. A alternativa exige que a aplicação tenha carregado seu HTML; não resolve o carregador vazio anterior à montagem.

As cores, fontes e seis ícones aprovados permanecem. A comparação final teve **zero diferença** nas posições e dimensões de cabeçalho, bandeiras, menu e capa, nos modos nativo/links e em 390/1440 px. [Geometria e capturas](geometry-proof/geometry.json). As primeiras comparações incluíram uma contagem incorreta de botões ocultos e foram preservadas; a prova final usa apenas controles utilizáveis.

## O que os logs demonstram

O trecho enviado mostra Python 3.12.16, instalação concluída e recebimento de main, sem traceback naquele trecho. Isso não prova ausência de erro em execução. [Fatos selecionados do log do proprietário](owner-log-extract.json). As dez dependências de runtime comparadas coincidem com o CI aprovado da 0.8.28; o Cloud acrescenta rich para logs. Não se concluiu igualdade completa de hosts nem se trocou dependência por tentativa. [Comparação](dependency-comparison.json), [linha original do CI](ci-package-lines.json).

A nova abertura pública anterior à correção chegou ao fim do Python, com dois seletores e o menu ainda incompleto. Encontrou 404 em rotas internas da hospedagem, sem reproduzir novo 500 nesse intervalo. Esses sinais não estabelecem a causa dos 500 anteriores. [Respostas, corpos limitados e DOM](browser-transport.json). O link legado de referência do repositório oficial não abriu uma aplicação comparável; [ensaio inconclusivo](reference-app.json), sem generalizar uma indisponibilidade da plataforma.

## Verificação da correção

- [CI completo da branch](branch-ci.json): 405 testes de código, 144 do pacote reconstruído, nove contraprovas e 13 suítes de navegador, incluindo Chromium/WebKit PT/EN e celular. Main e tag repetiram as verificações com sucesso.
- [Quatro contextos com Radio/Button bloqueados](local-resilience-hydration/resilience.json): seis destinos por teclado e troca de idioma em cada caso, GP/ano preservados, alvos >=44 px e sem transbordamento. O mesmo recibo comprova chegada tardia dos módulos, restauração dos controles nativos e preservação de foco.
- [24 verificações dos controles nativos](local-native-controls/controls.json), anteriores ao ajuste final de hidratação; a geometria final e o CI registram os controles finais separadamente.
- [Ensaio completo local do aceite](local-publication-final/publication.json): quatro fluxos aprovados, fotos decodificadas e hashes/build, documentação e troca real de idioma. Esse recibo identifica o build de sua fase; o build final foi reconstruído e testado independentemente no CI.
- Nove contraprovas incluem links ocultos, destinos externos e idiomas duplicados. Uma fixture inicial estava sem charset UTF-8 e foi corrigida; não se mudou a produção para acomodá-la.

O verificador público v2 registra modo nativo/link/misto, exige controles utilizáveis, clica alternativas e troca idioma de fato, comparando também URL externa/iframe. Erros visíveis não recuperados continuam reprovando o aceite. Duas tentativas por caso, até 120 segundos cada e oito minutos totais. A correção não certifica que outros recursos nativos nunca falharão nem estabelece a causa da hospedagem.

## Erros encontrados e preservação

No primeiro CI da branch, os testes novos passaram, mas o core parou depois em um teste antigo: seu seletor textual encontrou o controle nativo visível e o link alternativo oculto. Os dois testes afetados passaram a selecionar o controle visível, sem retirar a verificação de clique/GP. O foco também mantém o controle substituído fora da leitura assistiva durante a transição. [Primeiro CI e falha preservada](ci-first-attempt.json). A branch passou novamente antes do envio a main.

A suíte local ampla encontrou ENOSPC ao copiar fixtures temporárias: 94 testes executados, 39 erros de ambiente. A suíte portátil também foi interrompida por falta de espaço. Isso não é aprovação dessas suítes locais; a validação completa ocorreu no GitHub. [Limitação](local-limitations.json), [saída portátil](package-validation.txt). Pacotes anteriores e artefatos originais foram preservados. A recuperação de espaço substituiu apenas cópias temporárias idênticas por clones APFS, mantendo bytes, permissões e datas. [Recibo](storage-recovery.json). O candidato local usou a receita canônica inalterada e não gerou outro ZIP local. [Materialização](candidate-materialization.json), [receita final](candidate-final.json).

O CI completo agora roda em `codex/**` antes de main e mantém os 12 aceites anteriores, acrescentando resiliência. A verificação membro a membro do ZIP também passou na release real, separada do [ensaio somente leitura do ZIP anterior](zip-verifier-rehearsal.json). **681 arquivos protegidos e os seis ícones permaneceram idênticos**. [Integridade](protected-integrity.json). Dados, modelo v1, probabilidades e fontes originais não foram alterados.

## Próxima comparação da hospedagem

Se o carregamento público permanecer incompleto, a comparação proposta é uma segunda instância, com o mesmo código aprovado e Python 3.12, sem substituir a atual. A criação depende do painel autenticado do proprietário, ausente nesta sessão. [Configuração concreta PT/EN](HOSTING-COMPARISON.md). É uma proposta de diagnóstico, não uma migração executada nem uma causa demonstrada.

## Conferência pública das seis páginas

A execução adicional terminou com nove verificações aprovadas, dez tentativas com falha e cinco destinos sem execução porque o limite global de oito minutos foi atingido. Não são 24 aprovações nem 24 falhas observadas da interface. As transições aprovadas usaram cliques nativos e preservaram GP/ano/idioma; várias aberturas diretas pararam no carregador ou em controles incompletos. [Recibo completo e capturas](public-navigation-029/navigation.json). Uma única execução adicional por camada compara abertura normal, iframe observado e o [modo embed documentado](https://docs.streamlit.io/deploy/streamlit-community-cloud/share-your-app/embed-your-app); é diagnóstico de carregamento, sem aceite funcional ou causa presumida. [Resultado](hosting-layers-029/hosting.json).

Resultado da comparação final: abertura normal, acesso ao iframe observado e modo embed terminaram com carregamento incompleto. No acesso ao iframe, o Python chegou a terminar, com seis links alternativos presentes e foto ainda sem pixels; na abertura normal não houve montagem do produto na janela observada. Esses resultados não estabelecem uma causa única nem demonstram indisponibilidade geral do Streamlit. Não foram feitas novas trocas de dependências, remoção de proteções ou novo reboot.
