# Limites e exclusões do fechamento local

O pacote inclui somente os caminhos explícitos de `payload_local.json` e os artefatos permitidos deste fechamento. Não foram incluídos `projects/`, notas pessoais, cofre, credenciais, `.env`, caches, locks, `__pycache__`, os snapshots `cache-verificado-20261019`, `coleta-20261020T020130Z` e `coleta-20261020T095226Z`, nem logs/prompts/runtime ou resultado bruto redundante da R4.

Relatórios históricos podem apontar para snapshots excluídos. Essa referência histórica não os incorpora ao pacote nem reduz a limitação: a reprodução rastreável usa exclusivamente o snapshot original incluído `coleta-20261019T164713Z` e o ensaio anterior incluído.

Os 54 testes e o ensaio de 22 linhas são evidências reaproveitadas da validação integrada; não foram repetidos neste fechamento. A R4 aprova somente as três correções R3, não uma certificação integral do projeto. `operacao2026/__init__.py` é novo, contém apenas uma docstring e não tem baseline em `hashes_pre_revisao.json`; não se afirma uma comparação histórica inexistente.
