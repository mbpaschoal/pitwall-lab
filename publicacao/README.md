# Receita de publicação / Publication recipe

Created by: MBPaschoal
Status: active
Type: publication templates

## Português

Esta pasta contém templates; a implementação compartilhada está em `pitwall/publishing/` e a receita em `exportar_dashboard.py`. Não copie a pasta inteira para hospedagem.

Exporte para destino novo: `./.venv/bin/python exportar_dashboard.py --destino /caminho/novo/pitwall-dashboard`. Valide com `verificar_pacote.py --pacote CAMINHO_ABSOLUTO`. Os nove artefatos científicos são conferidos contra `05eec0b70b24abf9a68dae45aac36730eefb5bc5`; código de apresentação tem hashes próprios. Destinos divergentes, symlinks, segredos e cópia recursiva do cofre são recusados. O inventário orienta a seleção explícita para Git.

[Fontes e dados](templates/FONTES_E_DADOS.md) · [Licença do código](templates/LICENCA_CODIGO.md) · [Hospedagem](templates/GUIA_HOSPEDAGEM.md)

## English

This directory contains templates; shared implementation lives in `pitwall/publishing/` and the recipe in `exportar_dashboard.py`. Do not copy this entire directory to hosting.

Export to a new destination: `./.venv/bin/python exportar_dashboard.py --destino /new/path/pitwall-dashboard`. Validate with `verificar_pacote.py --pacote ABSOLUTE_PATH`. The nine scientific artefacts are checked against `05eec0b70b24abf9a68dae45aac36730eefb5bc5`; presentation code has separate hashes. Divergent destinations, symlinks, secrets and recursive vault copying are rejected. The inventory guides explicit Git selection.

[Sources and data](templates/FONTES_E_DADOS.md) · [Code licensing](templates/LICENCA_CODIGO.md) · [Hosting](templates/GUIA_HOSPEDAGEM.md). All three documents contain PT/EN sections.
