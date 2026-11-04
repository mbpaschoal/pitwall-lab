# Confirmação pública de imagens e publicação

Português · [English](README.en.md)

Created by: MBPaschoal
Status: v0.8.28 released; public acceptance failed; authenticated reboot requested
Type: delivery evidence

O diagnóstico reconferiu a capa de Como funciona. O navegador decodificou o WebP servido pelo aplicativo, com MIME, resolução e SHA iguais ao catálogo. O caminho relativo `app/static/` está correto dentro do iframe do Streamlit; não foi necessário trocar a foto ou o layout. A [documentação oficial](https://docs.streamlit.io/develop/concepts/configuration/serving-static-files) descreve essa forma de servir arquivos locais. [Imagem observada](before-r2/observed.png), [decodificação e respostas](before-r2/diagnostic.json), [conferência HTTP](static-http.json).

As primeiras tentativas também encontraram respostas 404/HTML para arquivos nativos JS/CSS do Streamlit e inicialização incompleta. Um HTTP 200 da imagem ou a versão visível não demonstra que toda a página terminou de carregar. Não há causa única estabelecida para essas intermitências. Capturas anteriores com imagem/ícones pendentes continuam preservadas, sem serem tratadas como aceite visual.

## Melhoria implementada

O [verificador de publicação](../../tests/browser/verificar_publicacao.cjs) passa a conferir quatro contextos novos: PT/EN em 390/1440 px, com Corridas e Como funciona em cada um. Exige:

- GP da publicação presente no calendário **e no estado coletado** do pacote, sem transformar uma etapa futura em dados recebidos;
- versão, idioma, controles nativos, fonte dos ícones e ausência de exceção/transbordamento;
- fotos realmente decodificadas, dimensões positivas, origem admitida, MIME de imagem e hash do original ou da variante documentada;
- build exato do pacote, aberto pelo controle de documentação.

Cada caso admite uma repetição por carregamento, dentro de seis minutos no conjunto. Divergência de origem/hash/identidade não é repetida como se fosse instabilidade. JSON é gravado atomicamente com o hash do verificador; tentativas e capturas ficam preservadas. A coleta hospedada guarda a evidência por 30 dias, inclusive em falha. Esse é um aceite após publicação de dados, não um monitor contínuo de disponibilidade.

## Contraprovas e validação

[Sete contraprovas](../../tests/browser/test_verificar_publicacao.cjs) combinam cinco casos com navegador real e dois de metadados/validação prévia. Cobrem foto admitida, hash incorreto, imagem quebrada, idiomas/controles, origem externa e identidade/versão incompatível. Entram no grupo core do CI, junto com um ensaio completo local do verificador: 12 aceites, preservando os 11 anteriores. O verificador completo passou nos quatro fluxos locais, ambos os idiomas e tamanhos, com fotos e build reais do pacote anterior. [Quatro casos locais](local-027-r2/publication.json), [401 testes Python](source-tests.json).

O primeiro ensaio da nova condição de prontidão expôs uma passagem incorreta de argumentos no próprio teste Playwright. Foi corrigida e ganhou contraprova específica. Uma tentativa diagnóstica usou o GP futuro 20; o contrato agora rejeita esse evento quando não houver estado coletado correspondente. Esses ensaios ficam preservados; a validação de publicação usa o GP coletado 19. Isso não altera o calendário ou a expectativa futura de São Paulo.

As tentativas públicas anteriores à entrega permanecem em [public-027](public-027/publication.json) e [public-027-r2](public-027-r2/publication.json). Falhas reais de bootstrap/recursos não viram sucesso por existir uma captura ou por repetir consultas sem limite. A validação da release nova terá recibo próprio.

## Rafael Câmara

Nova consulta serial de identificação em 03/11 às 23h21 UTC: Jolpica trouxe 35 pilotos e OpenF1 22, ainda sem Câmara. [URLs, UTCs, hashes e respostas originais](sources/20261103T232125Z/receipts.json). Não são resultados de Q nem entradas do modelo. As três artes já aprovadas continuam preservadas e só serão vinculadas após a identidade canônica ser conferida. Não se fabricou ID/número ou histórico.

## Aprendizado

A verificação precisa responder se o fã consegue usar o conteúdo servido. Identificar a versão prova qual entrega respondeu; fotos decodificadas, controles prontos e arquivos conferidos acrescentam evidência do conteúdo que de fato chegou. Uma falha do teste e uma falha da hospedagem precisam permanecer distinguíveis.

## Pacote final local

A distribuição 0.8.28 passou em 144 testes e nos quatro fluxos completos do novo verificador, sem repetição. O conjunto de contraprovas totaliza sete testes: os seis iniciais e a preservação de recibo quando a validação prévia rejeita o pacote antes da rede. [Pacote e ZIP](package-validation.json), [recibo local final](local-028/publication.json), [sete contraprovas](browser-counterexamples-final.txt). Os 533 arquivos científicos conferidos e o original da foto permanecem idênticos. [Integridade](protected-integrity.json).

## Publicação e pendência pública

**0.8.28 publicada e Latest**, CIs main/tag aprovados. ZIP com 665.856.793 bytes e SHA `b0f9061dbb2a8f0f2aa6fe7d4044cb06b548b7e1beedaaeecfd3149cc633e2d9`, igual ao pacote local. A comparação de 481 arquivos com a receita canônica teve zero diferenças. [Release](https://github.com/mbpaschoal/pitwall-lab/releases/tag/v0.8.28), [recibo final](delivery-final.json), [comparação com a receita](source-package-comparison.json), [validação hospedada](ci-validation.json).

O aceite público completo **não passou**: os quatro contextos deste computador e os quatro de um executor independente do GitHub falharam na inicialização/controles dentro das tentativas limitadas. A captura independente mostra o carregador, sem a página concluída. O mesmo código passou nos quatro fluxos locais e nos 12 aceites do CI. Isso distingue código/pacote testados de funcionamento público; não estabelece a causa da falha pública.

[Conferência pública local](public-028/publication.json), [diagnóstico independente](hosted-public-028/publication.json), [cadeia de integridade do artefato](hosted-artifact.json), [execução independente](https://github.com/mbpaschoal/pitwall-lab/actions/runs/41745235515). Esse diagnóstico ficou isolado em `codex/public-probe-network-20261104`, sem mudar main ou o produto; seus arquivos de evidência estão preservados neste relatório, além do artefato temporário.

Foi solicitado ao proprietário **Manage app → Reboot app**, pois a sessão pública disponível não oferece o controle administrativo autenticado. Não há confirmação de reinício nem teste posterior a ele. Esse é o próximo passo operacional; após a confirmação, repetir o verificador 0.8.28 em pasta nova, preservando estas falhas. A identificação canônica de Câmara continua sendo uma pendência separada; suas três artes já estão aprovadas.
