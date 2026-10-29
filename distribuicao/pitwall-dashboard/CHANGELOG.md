# Evolução do Pitwall Lab

Português · [English](CHANGELOG.en.md)

Versões descrevem entregas do produto. O modelo científico v1 permanece congelado. Não foram atribuídas versões retroativas aos commits anteriores.

## 0.1.2 — 2026-10-29

### Interface

Move as bandeiras BR/GB para o canto superior direito após o uso público mostrar sobreposição com a marca e os controles do Streamlit/GitHub no rodapé. Uma faixa reservada abaixo da barra nativa evita cobrir busca, perfil e título do GP em desktop e celular. Idioma, GP, aba e filtros permanecem preservados.

O aceite verifica a posição superior, as bandeiras lado a lado e a ausência de interseção com os controles da aplicação. Dados, modelo e probabilidades não mudaram.

## 0.1.1 — 2026-10-29

### Publicação e verificação

O GitHub e o CI da versão 0.1.0 estavam atualizados, mas uma sessão pública limpa ainda recebeu a interface anterior. Reexecutar a página não sincronizou o código. O arquivo de dependências da apresentação recebeu um marcador da entrega para solicitar um build novo ao Community Cloud, mantendo exatamente as mesmas versões de pacotes. A confirmação pública continua separada do push e do CI.

O teste de versões passou a usar changelogs sintéticos, para não depender de quais versões já existem no histórico real. Nenhum dado, modelo, probabilidade ou artefato científico foi alterado.

Aprendizado: uma release e testes aprovados não comprovam que o serviço de hospedagem já executa esse código. [Mecanismo documentado pelo Streamlit](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app/upgrade-streamlit).

## 0.1.0 — 2026-10-29

Primeira versão sob a política explícita de versionamento do produto.

### Dados e correções

- 75 itens resolvidos na fila de dados: 71 conflitos de classificação documentados, complemento FIA para Baku/Q, dois estados de qualidade corrigidos e origem do archive identificada. Seis ausências confirmadas; 31 limitações de pneus permanecem.
- Histórico passou da corrida atual para até cinco edições anteriores na mesma pista, inclusive para GPs futuros sem acervo próprio.
- Fichas de 26 circuitos com altitude aproximada, recorde e contexto de DRS por temporada/referência.

### Produto e manutenção

- Bandeiras BR/GB com navegação, tabelas, gráficos, mensagens e documentos PT/EN; idioma preservado nos links.
- Código organizado por responsabilidade em `pitwall/`, com pontos de entrada compatíveis e fontes congeladas preservadas.
- README, aprendizados, arquitetura, contribuição e política de versões bilíngues.
- Cada nova entrega de dados ou melhoria exige incremento de versão e registro do problema, mudança, validação e aprendizado.

### Aprendizado e limites

A correção do Histórico mostrou que ter dados não garante responder à pergunta do usuário. A revisão dos stints distinguiu aviso de qualidade de lacuna real. O registro de origem do archive não inventa seu horário original de aquisição. Tradução altera apresentação, não evidência científica. Uma entrega local só passa a ser considerada pública após conferência do build servido.

## Antes da política de versões

Marcos anteriores são identificados por commits reais no [diário de aprendizado](https://github.com/mbpaschoal/pitwall-lab/blob/main/docs/APRENDIZADOS.md). Datas e mensagens originais foram preservadas.
