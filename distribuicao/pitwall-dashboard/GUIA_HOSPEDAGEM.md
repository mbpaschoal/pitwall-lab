# Hospedagem / Hosting

## Português

O app público usa o repositório `mbpaschoal/pitwall-lab`, branch `main`, entrypoint `distribuicao/pitwall-dashboard/app.py`, com Python 3.12 selecionado no Streamlit Community Cloud. `requirements.txt` fica junto ao entrypoint. Não são necessários secrets para navegar no dashboard.

Para homologar uma alteração, exporte primeiro para uma pasta **nova** fora do cofre:

```bash
./.venv/bin/python exportar_dashboard.py --destino /caminho/novo/pitwall-dashboard
./.venv/bin/python verificar_pacote.py --pacote /caminho/novo/pitwall-dashboard
```

O exportador recusa destinos divergentes e symlinks. Preserve a distribuição anterior antes de substituir a versão canônica autorizada. Selecione somente arquivos de `ARQUIVOS_PUBLICACAO.txt` para Git; não publique todo o cofre. Faça testes PT/EN desktop/mobile, confira os nove artefatos científicos e o manifesto. Após push, abra uma sessão pública limpa e compare versão/build servido: push não comprova deploy.

Para executar só o pacote exportado:

```bash
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501
```

Essa `.venv` pertence ao pacote; não substitui a científica. Endereço/porta são locais. A plataforma Cloud controla sua rede. O arquivo `.python-version` é informativo; a escolha no Cloud fica em Advanced settings. A configuração pede `gatherUsageStats=false`; a plataforma pode sobrepor essa opção. A licença do código continua separada das condições dos dados.

## English

The public app uses repository `mbpaschoal/pitwall-lab`, branch `main`, entry point `distribuicao/pitwall-dashboard/app.py`, with Python 3.12 selected in Streamlit Community Cloud. `requirements.txt` is next to the entry point. No secrets are needed to browse the dashboard.

Export to a **new** directory outside the vault before verification:

```bash
./.venv/bin/python exportar_dashboard.py --destino /new/path/pitwall-dashboard
./.venv/bin/python verificar_pacote.py --pacote /new/path/pitwall-dashboard
```

The exporter rejects divergent destinations and symlinks. Preserve the previous package before an authorised canonical update. Select inventory files for Git; do not publish the entire vault. Check PT/EN desktop/mobile, the nine scientific artefacts and the manifest. After pushing, open a clean public session and compare the served version/build: a push does not prove deployment.

To run the exported package alone, create a Python 3.12 virtual environment, install its `requirements.txt` and run its `app.py` using the commands above. This environment belongs to the package, not the scientific environment. Address/port are local choices; Cloud manages its own network. `.python-version` is informational; Cloud's version is selected in Advanced settings. Configuration requests `gatherUsageStats=false`, but the platform may override it. Code licensing remains separate from data conditions.

## Referências / References

- [Deploy](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy)
- [Dependencies](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies)
- [Troubleshooting](https://docs.streamlit.io/deploy/streamlit-community-cloud/troubleshooting)
