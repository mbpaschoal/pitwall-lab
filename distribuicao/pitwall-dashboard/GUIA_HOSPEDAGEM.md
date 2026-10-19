# Guia de hospedagem futura — Streamlit Community Cloud

Este guia prepara uma publicação futura; ele não publica, não cria repositório e
não afirma que uma execução em nuvem já ocorreu.

## Preparar um repositório público separado

Todos os comandos desta seção são instruções futuras: não os execute no cofre
privado atual. Escolha uma pasta de destino nova e externa ao cofre, por exemplo
`$HOME/Projetos/pitwall-dashboard-publico`. No repositório privado, gere o
pacote para essa pasta:

```bash
DESTINO="$HOME/Projetos/pitwall-dashboard-publico"
python3 exportar_dashboard.py --destino "$DESTINO"
cd "$DESTINO"
```

O exportador preserva um destino já existente somente se ele for byte a byte
idêntico ao pacote esperado. Se houver conflito, use outro diretório novo; não
sobrescreva nem misture arquivos manualmente.

Antes de iniciar Git, confirme que a pasta não pertence a outro repositório:

```bash
if git rev-parse --show-toplevel >/dev/null 2>&1; then
  echo "ERRO: o destino já pertence a um repositório Git; escolha outro diretório novo."
  exit 1
fi
git init -b main
python3 -c 'from pathlib import Path; import subprocess; caminhos = Path("ARQUIVOS_PUBLICACAO.txt").read_text(encoding="utf-8").splitlines(); subprocess.run(["git", "add", "--", *caminhos], check=True)'
git diff --cached --check
git status
git commit -m "Publica demonstracao retrospectiva do Pitwall Lab"
```

O comando Python passa a lista de `ARQUIVOS_PUBLICACAO.txt` como argumentos
explícitos de `git add`; não use `git add -A`, `git add .` nem publique o
histórico deste cofre.

No GitHub pela interface web, crie um repositório **público separado**, vazio e
sem inicializar README, `.gitignore` ou licença. Copie a URL real fornecida pelo
GitHub e use-a apenas na variável abaixo; não há URL pública predefinida:

```bash
URL_NOVA="COLE_AQUI_A_URL_REAL_FORNECIDA_PELO_GITHUB"
git remote add origin "$URL_NOVA"
git push -u origin main
```

Alternativamente, `gh repo create` pode criar o repositório, mas exige que o
GitHub CLI esteja instalado e autenticado na conta correta.

Antes de qualquer publicação, obtenha autorização para revisão de código, das
licenças e das condições não comerciais dos dados. O código ainda não tem uma
licença definida: não atribua automaticamente licença MIT ao pacote; a licença
do código depende da escolha expressa do autor, e os dados continuam CC BY-NC-SA.

## Configurar o deploy

Na tela de criação de aplicativo do Streamlit Community Cloud, escolha **Create
app**, confirme **Yup, I have an app**, selecione o repositório novo, a branch
`main` e o arquivo de entrada `app.py`. Em **Advanced settings**, selecione
Python 3.12. Este pacote não exige secrets.

`requirements.txt` fica na raiz e é o único arquivo de dependências do pacote.
Não adicione outro gerenciador de dependências sem uma decisão explícita. O
arquivo `.python-version` é apenas informativo: a escolha efetiva de Python no
Community Cloud é feita em Advanced settings.

A documentação consultada em 18 de outubro de 2026 indicava Python 3.12 como
padrão, `requirements.txt` na raiz ou junto do entrypoint e ambiente baseado em
Debian Linux. Esta distribuição foi preparada para revisão local em macOS; ela
não afirma execução já verificada em Linux ou no Community Cloud.

O `config.toml` local pede `gatherUsageStats = false`, mas o Community Cloud
documenta que pode sobrepor essa opção para `true`. Portanto, a desativação não
pode ser garantida na nuvem.

Documentação oficial:

- https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy
- https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies
- https://docs.streamlit.io/deploy/streamlit-community-cloud/troubleshooting

## Executar localmente

```bash
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501
```

A `.venv` acima pertence somente ao pacote público novo e não modifica o ambiente
científico original. A porta e o endereço são locais. A plataforma de nuvem
gerencia sua própria rede e não deve receber endereço público ou porta fixa neste
arquivo de configuração.
