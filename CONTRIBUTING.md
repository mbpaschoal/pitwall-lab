# Contribuição

Português · [English](CONTRIBUTING.en.md)

Comece por [arquitetura](docs/ARQUITETURA.md) e [blueprint](docs/BLUEPRINT.md). Preserve alterações existentes, dados originais, IDs e corte temporal. A interface não executa coletores ou modelos. Não substitua ausências por zero nem use resultados da própria corrida como entrada.

Trabalhe em uma branch `codex/descricao` ou outra branch de tarefa. Faça mudanças pequenas e revise o diff, inclusive arquivos novos. Nunca adicione todo o cofre com `git add .` ou `git add -A`: selecione arquivos do escopo. Dados brutos, material pessoal, sessões, caches, ambientes e repositórios de referência não pertencem ao pacote público.

Edite implementações em `pitwall/`; arquivos equivalentes da raiz são compatibilidade. Atualize textos PT/EN juntos. IDs e CSVs científicos não são traduzidos; forneça definições no dicionário. Documente limitações de fonte e comportamento anterior sem fabricar uma causa.

Para apresentação, execute módulos focais, por exemplo:

```bash
./.venv/bin/python -B -m unittest tests.test_i18n tests.test_dashboard_app tests.test_dashboard_acervo_app
./.venv/bin/python -B -m pitwall.publishing.releases check
```

O pacote deve ser exportado para destino novo e verificado com `verificar_pacote.py --pacote CAMINHO_ABSOLUTO`. Confira navegador PT/EN em desktop/mobile quando a interface mudar. A suíte científica completa pode treinar modelos; não a use como verificação automática de texto/CSS.

Cada entrega de dados ou melhoria exige versão e notas bilíngues conforme a [política](docs/VERSOES.md). Assunto de commit concreto; corpo PT/EN com problema, correção, verificação e limitações. Não reescreva commits históricos para padronizar idioma ou esconder erros. O código original está sob a licença MIT; condições das fontes permanecem separadas.
