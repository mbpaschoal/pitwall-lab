# Publicação da avaliação prospectiva do México

Created by: MBPaschoal
Status: published and verified
Type: publication receipt

A implementação da avaliação está preservada na tag 0.8.7. O aceite CI dessa tag incluiu por engano testes legados que dependem de capturas locais ausentes do checkout público. A tag não foi reescrita. A correção **0.8.8**, commit `aae764db7145c287587136fcc870177593593994`, conserva a mesma avaliação e mantém no CI os testes públicos de vínculo, leitor/UI e pacote isolado.

O site público serviu **0.8.8**, build `43755f64207769d1a49fa50bd0148155d0967841e0f1aee5a786db9409302485`, em sessão limpa em 2026-11-02T04:17:51.578Z. [Conferência da versão e build](../deploy-check.json).

México: Lab 2/3, classificação 1/3, 22 alvos conhecidos, zero exclusões; cinco abandonos preservam posição ausente. As probabilidades exibidas são 68,2%, 61,9% e 57,5% (PT), ou 68.2%, 61.9% and 57.5% (EN). Duas corridas prospectivas avaliáveis não demonstram superioridade.

Validação local: suíte principal de 242 testes, 91 testes focais de UI/leitor em combinações parcialmente sobrepostas, 5 testes de vínculo e 141 testes portáteis. O aceite local das seis telas passou 24 cenários. O aceite público passou **32 cenários**: [8 focais de México](../browser-public-088/acceptance.json) e [24 das seis telas](../browser-public-six-088/acceptance.json). As sessões confirmaram versão, idiomas, cliques nativos, ausência de transbordamento e os valores congelados. A integridade do ZIP tem recibo próprio.

614 artefatos científicos, 27 arquivos da emissão e o registro de emissões permanecem idênticos. [Recibo final de preservação](../preservation-final.json).

Celular significa viewport de 390 px e interação por toque emulados. Não houve teste em aparelho físico nem com leitor de tela. Originais privados da FIA permanecem locais; os documentos são referenciados por URL/hash e fatos normalizados.

English: version 0.8.8 corrects public-checkout test selection while preserving tag 0.8.7 and the frozen Mexico evaluation. Fresh public sessions verified the served build and passed eight focused cases plus 24 six-screen scenarios. Release ZIP integrity is checked separately against the complete canonical package. Mobile checks are emulated; private original documents are not redistributed.

CI da tag e de main aprovados. [Recibo CI fixado na 0.8.8](ci-088.json). O [ZIP público](https://github.com/mbpaschoal/pitwall-lab/releases/tag/v0.8.8), publicado em 2026-11-02T04:27:03Z, possui 665821985 bytes e SHA-256 `dd28af172eeb02be5c78ac413465ec2b8ee2142addcacfbb21351f942321de1e`, igual ao digest informado pelo GitHub. Todos os **473 membros** coincidem com o manifesto da tag **v0.8.8**, sem gravar uma cópia binária local. [Recibo da conferência](release-zip.json).

A versão 0.8.9 foi preparada por outro fluxo enquanto esta conferência terminava. Este recibo é especificamente da 0.8.8: não atribui testes dessa versão às alterações posteriores nem compara o ZIP antigo ao working tree novo.

English: both pinned 0.8.8 workflow runs and all tag jobs passed. The public ZIP digest and all 473 members match the immutable v0.8.8 manifest. Another workflow advanced the shared checkout to 0.8.9; this receipt remains pinned to 0.8.8.
