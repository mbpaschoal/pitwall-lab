# Rafael Câmara e preparação de São Paulo

Português · [English](README.en.md)

Created by: MBPaschoal
Status: implementation under validation; canonical driver identity pending
Type: delivery evidence

A F1 anunciou Rafael Câmara na Haas para São Paulo em 03/11/2026 às 20h30 UTC. A conferência posterior encontrou 35 pilotos no endpoint da temporada Jolpica e 22 na consulta de identificação OpenF1 da classificação de São Paulo, sem Câmara; a segunda ainda listava Ocon e Bearman na Haas. Esses dados preparatórios não são uma lista homologada de inscritos nem um snapshot preditivo. Número e identificador de Câmara continuam desconhecidos; não foi escolhido o número desejado para 2027 nem reutilizado o ID de outro piloto.

## O que muda na operação

- A política revisada de São Paulo exige um registro literal de Rafael Camara/Câmara na Haas e rejeita a presença de Ocon, antes de chamar a inferência. O ID canônico vem intacto da classificação recebida. Não há união por semelhança de nome. Uma divergência bloqueia a tentativa e conserva diagnóstico e capturas.
- A rota OpenF1 preserva seu requisito de mapeamento literal. Enquanto a nova identidade não estiver conferida, não se fabrica ID ou número para destravá-la. A rota canônica pode admitir o ID que a própria classificação validada fornecer.
- Cartas são opcionais: o relatório `artwork_coverage` registra faltas, equipe e poses. Sua ausência não impede registrar uma previsão válida. A população científica continua exigindo 22 IDs únicos; não se remove piloto por falta de arte. A interface já dispõe de indicação de ilustração indisponível, sem trocar o rosto.
- A receita v1 já suporta estreantes com indicadores de pouco histórico. O novo teste confirma médias ausentes e contadores próprios zero, sem transferir o histórico de Ocon. Dados anteriores da equipe continuam sendo apenas dados da equipe. Sem alteração de pesos, entradas ou probabilidades registradas.

## Foto e três artes preparadas

O [retrato oficial original](sources/camara-f1-3392.webp) tem **1920 × 1080 pixels efetivos**. O parâmetro 3392 da URL não muda a resolução entregue. Bytes originais preservados, sem ampliar ou recortar o arquivo. Direitos pertencem aos titulares; não se presume licença aberta.

As três ilustrações de **1024 × 1536 pixels** usam esse rosto como referência, com óculos, e os exemplos já aprovados como referência de estilo. Destacam vermelho, branco e preto da Haas, sem percentuais ou número não confirmado. Foram conferidas visualmente: nome e acento corretos, moldura completa, mãos naturais e poses diferentes.

| Variação | Composição | Arquivo |
|---|---|---|
| 1 | Em pé com capacete sob o braço | [Carta 1](drafts/rafael-camara-haas-pose-0.png) |
| 2 | Sentado nos pneus, mãos sobre as pernas | [Carta 2](drafts/rafael-camara-haas-pose-1.png) |
| 3 | Apoiado nos pneus, uma mão no bolso | [Carta 3](drafts/rafael-camara-haas-pose-2.png) |

Geradas pela ferramenta nativa `image_gen`. [Prompts e referências](prompts.json), [hashes e dimensões](artwork-receipt.json). Os arquivos são rascunhos de apresentação, fora do catálogo ativo, aguardando revisão e ID canônico conferido. Uma ilustração não anuncia favoritos nem constitui previsão.

## Fontes e verificações

- [Anúncio F1](https://www.formula1.com/en/latest/article/f2-racer-camara-to-make-f1-debut-at-sao-paulo-grand-prix-as-haas-confirm-ocon-will-not-return.12Qa0tpaMZ9kgnEuGJBKFp), [captura original](sources/f1-camara-announcement.html), [URL, UTC e SHA](sources/announcement-receipt.json).
- [Consulta de identidades, feita em série](sources/identity-receipts.json); [Jolpica original](sources/jolpica-drivers-2026.json), [OpenF1 original](sources/openf1-saopaulo-q-drivers.json). Sem resultados futuros ou uso como entrada.
- [Origem e direitos da fotografia](sources/portrait-receipt.json).

Testes de operação cobrem substituição, equipe incorreta, nome semelhante rejeitado, GP divergente, adulteração da fonte, falta de artes, população incompleta, recuperação sem recalcular e estreante sem histórico emprestado. Resultados locais, publicação no GitHub e versão servida terão recibos próprios; esta seção não antecipa aprovação de CI ou deploy.

## Aprendizado

Ter três artes para cada piloto do catálogo não prova que todos os inscritos de um evento estejam cobertos. A mudança anunciada expôs duas responsabilidades diferentes: conferir a população real da classificação e medir a cobertura visual. A primeira permanece obrigatória; a segunda deve acompanhar a previsão sem impedir sua publicação. Preservar essa distinção evita tanto uma previsão com piloto substituído quanto o bloqueio por um adorno opcional.

## Validação local desta revisão

Passaram **401 testes de código**, incluindo os 27 casos da operação pós-Q. A conferência byte a byte preservou **533 arquivos científicos e fontes anteriores**, sem diferenças; nenhuma previsão real foi emitida. [Resultado dos testes](source-tests.json), [saída completa](source-tests.txt) e [integridade](protected-integrity.json). Pacote, CI e versão pública serão conferidos separadamente após o commit.

Pacote portátil: **144 testes aprovados** e 481 arquivos conferidos. Navegador Chrome local: **24/24 casos**, seis destinos em PT/EN e larguras 390/1440 px, sem erro de página ou transbordamento. [Pacote, build e ZIP](package-validation.json), [aceite de navegador](browser-local/controls.json). Isso não certifica a hospedagem pública.
