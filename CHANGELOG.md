# Evolução do Pitwall Lab

Português · [English](CHANGELOG.en.md)

Versões descrevem entregas do produto. O modelo científico v1 permanece congelado. Não foram atribuídas versões retroativas aos commits anteriores.

## 0.4.0 — 2026-10-30

No Resumo, foto e traçado da pista passam a aparecer antes do pódio, dando destaque ao circuito.

Preparação do México com cinco sessões identificadas, coleta serial após encerramento observado, cache auditável e espera persistida em limites da API. Tempos, voltas, pneus, paradas, previsão meteorológica separada dos sensores da corrida e campeonatos da rodada própria. Admissão explícita de Q OpenF1 para o México; código commitado e publicação antes da largada continuam obrigatórios. Acertos de 2026 inclui somente previsões registradas e resultados posteriores validados. A corrida e a classificação ainda não aconteceram; não há previsão prospectiva do México nesta entrega.

## 0.3.1 — 2026-10-30

Corrige a sincronização do teste de favorito: o aceite passa a localizar o iframe atual após recarregar e aguardar o valor persistido, em vez de guardar uma referência que pode ser removida pelo Streamlit. A instabilidade foi observada no CI da branch principal; a release 0.3.0 e a aplicação pública haviam passado. Dados, regras de comparação e modelo científico permanecem iguais. O CI também regenera a distribuição e compara com a cópia publicada. Validação: jornada completa do navegador contra o pacote servido e conferência de integridade.

## 0.3.0 — 2026-10-29

- Navegação para fãs: campeonato completo em uma tela própria, resultados primeiro e explicações técnicas em segundo nível.
- Pilotos: duelos nos mesmos GPs, favorito no navegador, histórico recente, filtros preservados e cartões SVG para compartilhar.
- Correções: vento usa média circular; comparação individual usa os mesmos GPs; clima do resumo corresponde à corrida quando disponível.
- Leitura e celular: contraste, parágrafos, abas visíveis e imagens de apresentação menores, preservando os originais.
- Entrega: licença MIT para código original, verificação do pacote real em CI e documentação PT/EN.
- Limites: análise histórica não mede habilidade isolada. 17 compostos de treinos/classificação continuam ausentes. Modelo v1 e emissões preservados.

## 0.2.0 — 2026-10-29

### Pilotos: comparar resultados com condições reais de corrida

Novo menu com capacete, visão geral por condição e perfil individual, em português e inglês. Os seis destaques mostram chuva registrada, temperaturas da pista, sentido, curvas e altitude. Há filtros de temporadas, métrica e mínimo de largadas, classificação completa da coorte, mapa de todos os pilotos, confronto com o companheiro e evidências exportáveis com links para cada GP. Empates permanecem explícitos; ausência de amostra não vira desempenho zero.

A base descritiva reúne 66 corridas principais, 1.354 resultados e 1.340 largadas. Controle de corrida delimita os intervalos realmente disputados e exclui pausas: oito provas tiveram chuva registrada. Open-Meteo fornece 70 amostras atmosféricas horárias dentro desses intervalos, identificadas como reconstrução em grade. Foram conferidos 66 mapas FIA da edição: Suzuka tem traçado em oito; Spielberg e Marina Bay respeitam seus comprimentos por ano.

A [auditoria](reports/pilotos_condicoes_20261029/README.md) registra 295 verificações. Dos 50 limites de stint inválidos, 30 foram reconstruídos com voltas observadas; os demais correspondem a zero voltas completadas ou DNS. Nove compostos foram recuperados. Os 17 compostos ainda indisponíveis pertencem a treinos/classificação e ficam ausentes, excluídos destes cruzamentos. Corridas recebeu 11 sequências observadas de estratégias e oito preenchimentos pontuais de compostos; o nono composto recuperado já está numa dessas sequências.

Aprendizado: tipo de sessão não basta para separar Sprint e corrida; horário agendado não define tempo efetivo de prova; concordância entre feeds não garante independência. Na Austrália/2026, a seleção de voltas considera piloto, UTC e duração, preservando uma divergência de numeração entre fontes. Taxas usam largadas como oportunidades, inclusive abandonos e DSQ; não largadas são excluídas. As comparações são associações históricas, sem estimar habilidade isolada. Os 614 arquivos protegidos, o modelo v1 e as probabilidades registradas permanecem inalterados.

## 0.1.4 — 2026-10-29

### Imagens de São Paulo e Madrid

A imagem de Interlagos tinha apenas 349 × 197 pixels. Ela foi substituída por uma fotografia de 5000 × 3333 pixels do S do Senna durante o GP de São Paulo de 2022, com carros de Fórmula 1 e pista em destaque. Crédito Beto Issa/Fórmula 1 e Governo do Estado de São Paulo, CC BY 2.0.

Em Madrid, o recorte de uma foto vertical destacava o céu e escondia a pista. A nova foto oficial mostra a reta principal, boxes e arquibancadas em setembro de 2026. O enquadramento lateral da interface prioriza o circuito e mantém a pessoa retratada fora da área visível. Crédito Comunidad de Madrid, CC BY-NC-SA 4.0; a restrição não comercial é específica desse arquivo e permanece no catálogo.

A revisão confere resolução original e assunto visível no tamanho real do card em desktop e celular. As imagens originais permanecem sem edição; os recortes de apresentação, fontes, créditos e textos alternativos PT/EN estão registrados. Mapas, dados e previsões não mudaram.

## 0.1.3 — 2026-10-29

### Fotografia de Miami

Substitui a fotografia da Porsche Sprint Challenge, selecionada por ocorrer no mesmo circuito, por uma foto real de Sergio Pérez no Red Bull RB18 de Fórmula 1 no GP de Miami de 2022. A correção surgiu do uso público: o local correto não garante que a categoria mostrada seja a correta. A seleção visual agora confere circuito, categoria e identificação do carro.

Crédito: Dcmaradiaga (David Castro), Wikimedia Commons, CC BY-SA 4.0. Arquivo original preservado; texto alternativo PT/EN e catálogo com hash e origem atualizados. A foto é ilustrativa e datada de 2022, sem representar a temporada selecionada. Dados e previsões permanecem preservados.

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

Marcos anteriores são identificados por commits reais no [diário de aprendizado](docs/APRENDIZADOS.md). Datas e mensagens originais foram preservadas.
