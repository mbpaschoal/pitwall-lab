# Ilustrações dos GPs

A coleção `frontend_assets/destination_illustrations.json` contém 26 cenas em guache editorial. Sepang é a referência visual aprovada; as demais cenas foram geradas individualmente com elementos locais e revisadas em imagem completa. São interpretações artísticas, não fotografias ou mapas técnicos. Os créditos informam a geração com IA e as referências de cada destino.

Os PNGs originais de 1536 × 1024 estão em `static/pitwall-art/gouache`, com identificador do circuito e prefixo SHA-256 no nome. O catálogo registra o hash completo, as dimensões, o texto alternativo PT/EN e as URLs consultadas. O leitor verifica identidade, caminho, bytes e dimensões; ausência ou corrupção resulta em aviso, sem trocar pelo cenário de outro GP.

A imagem usa proporção 3:2, `object-fit: contain`, cantos de 12 px e sombra discreta. Texto, data e créditos ficam fora da pintura. No celular, a composição passa para uma coluna. Fotografias documentadas continuam disponíveis na seção própria do circuito.

Para preparar outra coleção, preserve as gerações e comprovantes fora do pacote, revise cada imagem completa, registre a seleção e execute `scripts/build_gouache_art.py --selection-dir CAMINHO`. O modo incompleto é exclusivo de prévia local e não é aceito na publicação. A lista de arquivos da distribuição é explícita em `exportar_dashboard.py`.

O aceite automatizado verifica as 26 identidades e o enquadramento em tela larga e estreita. Capturas e revisão visual complementam as métricas. CI, integridade do pacote e confirmação na hospedagem pública são etapas distintas.
