# Menu e idiomas disponíveis durante falha de carregamento

Português · [English](README.en.md)

Created by: MBPaschoal
Status: local interaction verified; complete branch CI pending
Type: implementation and deployment evidence

## Problema e mudança

O proprietário confirmou que menu e bandeiras travavam mesmo após reboot. A [conferência anterior](../midia_publica_20261103/post-reboot-20261104T011855Z/README.md) preserva os erros nativos 500 e de importação dinâmica. Agora o menu e as bandeiras também oferecem links normais enquanto seus componentes não carregam. Os links preservam destino, GP, idioma, filtros aplicáveis e teclado. Quando os controles nativos chegam, os links somem sem duplicar a navegação ou retirar o foco de quem os está usando.

As cores, fontes e seis ícones aprovados permanecem. A comparação final teve **zero diferença** nas posições e dimensões de cabeçalho, bandeiras, menu e capa, nos modos nativo/links e em 390/1440 px. [Geometria e capturas](geometry-proof/geometry.json). As primeiras comparações incluíram uma contagem incorreta de botões ocultos e foram preservadas; a prova final usa apenas controles utilizáveis.

## O que os logs demonstram

O trecho enviado mostra Python 3.12.16, instalação concluída e recebimento de main, sem traceback naquele trecho. Isso não prova ausência de erro em execução. [Fatos selecionados do log do proprietário](owner-log-extract.json). As dez dependências de runtime comparadas coincidem com o CI aprovado da 0.8.28; o Cloud acrescenta rich para logs. Não se concluiu igualdade completa de hosts nem se trocou dependência por tentativa. [Comparação](dependency-comparison.json), [linha original do CI](ci-package-lines.json).

A nova abertura pública chegou ao fim do Python, com dois seletores e o menu ainda incompleto. Encontrou 404 em rotas internas da hospedagem, sem reproduzir novo 500 nesse intervalo. Esses sinais não estabelecem a causa dos 500 anteriores. [Respostas, corpos limitados e DOM](browser-transport.json). O link legado de referência do repositório oficial não abriu uma aplicação comparável; [ensaio inconclusivo](reference-app.json), sem generalizar uma indisponibilidade da plataforma.

## Verificação da correção

- [Quatro contextos com Radio/Button bloqueados](local-resilience-hydration/resilience.json): seis destinos por teclado e troca de idioma em cada caso, GP/ano preservados, alvos >=44 px e sem transbordamento. O mesmo recibo comprova chegada tardia dos módulos, restauração dos controles nativos e preservação de foco.
- [24 verificações dos controles nativos](local-native-controls/controls.json), anteriores ao ajuste final de hidratação; a geometria final e o ensaio seguinte registram os controles finais separadamente.
- [Ensaio completo local do aceite](local-publication-final/publication.json): quatro fluxos aprovados, fotos decodificadas e hashes/build, documentação e troca real de idioma. O hash do pacote testado está no recibo; a receita final também será reconstruída independentemente pelo CI.
- Nove contraprovas do verificador incluem links ocultos, destinos externos e idiomas duplicados. Uma fixture inicial estava sem charset UTF-8 e foi corrigida; não se mudou a produção para acomodá-la.

O verificador público v2 registra modo nativo/link/misto, exige controles utilizáveis, clica alternativas e troca idioma de fato, comparando também URL externa/iframe. Erros visíveis não recuperados continuam reprovando o aceite. Duas tentativas por caso, até 120 segundos cada e oito minutos totais. A correção não certifica que outros recursos nativos nunca falharão nem estabelece a causa da hospedagem.

## Limite local e entrega

A suíte local ampla encontrou ENOSPC ao copiar fixtures temporárias: 94 testes executados, 39 erros de ambiente. A suíte portátil também foi interrompida por falta de espaço. Isso não é aprovação dessas suítes. [Limitação](local-limitations.json), [saída portátil](package-validation.txt). O pacote anterior e os artefatos originais foram preservados. O candidato local usa cópia por escrita e a receita canônica inalterada; não gerou outro ZIP local. [Materialização](candidate-materialization.json), [receita final](candidate-final.json).

O CI completo passa a rodar em `codex/**` antes de main e mantém os 12 aceites anteriores, acrescentando a suíte de resiliência. Deve reconstruir o pacote pelo exportador canônico, conferir os 481 arquivos e executar as suítes Python/portátil/navegador em Python 3.12 antes da publicação. Release e novo aceite público terão recibos próprios. Dados, modelo v1, probabilidades e fontes originais não foram alterados.
