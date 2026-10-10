# 🗳️ Painel de Inteligência Eleitoral de Pernambuco (2008–2026)
## Manual do Usuário & Guia Estratégico de Análise de Dados

---

## 📌 Sumário Executivo & Visão Geral

O **Painel de Inteligência Eleitoral de Pernambuco** é uma plataforma analítica avançada desenvolvida para transformar os microdados oficiais do Tribunal Regional Eleitoral de Pernambuco (TRE-PE) e do Tribunal Superior Eleitoral (TSE) em decisões políticas e eleitorais precisas.

A base histórica consolidada contempla pleitos de **2008 a 2026**, cobrindo todas as escalas territoriais do estado:
* **185 Municípios** (100% do estado de Pernambuco, incluindo Fernando de Noronha integrado à Região Metropolitana)
* **209 Zonas Eleitorais** (com recortes individualizados por município)
* **1.058 Bairros e Distritos** (georreferenciamento de áreas urbanas e sedes distritais rurais)
* **3.406 Colégios Eleitorais** (escolas públicas, privadas e pontos de votação cadastrados com coordenadas geográficas)
* **22.111 Seções Eleitorais** (nível atômico da apuração urna a urna)

---

## 🔐 1. Acesso ao Sistema e Segurança

### 1.1. Tela de Login & Acesso Restrito
Ao carregar a plataforma, o usuário é direcionado para a tela de autenticação:
* **Campos:** `Usuário` e `Senha`.
* **Segurança:** O painel valida as credenciais contra a base encriptada de usuários cadastrados nos *secrets* da aplicação.
* **Sessão:** A conexão permanece ativa no navegador enquanto a aba estiver aberta. Ao clicar em **"🚪 Sair"** no menu lateral, a sessão é encerrada com segurança.

### 1.2. Painel de Auditoria de Acessos (Exclusivo para o Perfil `admin`)
Quando o login for efetuado pelo usuário administrativo (`admin`):
* Aparece na barra lateral o bloco **"🛡️ Auditoria de Acessos"**.
* **O que exibe:** Tabela em tempo real com a data/hora exata (horário de Pernambuco/Brasília), o nome do usuário que conectou, a ação realizada (*Login com sucesso* ou *Tentativa incorreta*) e detalhes.
* **Exportação:** Botão **"📥 Baixar Logs (CSV)"** para descarregar o histórico de acessos das equipes e monitorar a utilização da ferramenta.

---

## 🎛️ 2. Barra Lateral (Sidebar): Filtros Mestres & Parâmetros de Foco

A barra lateral comanda a visualização de quase todas as abas do painel. Qualquer alteração feita aqui atualiza instantaneamente os gráficos e mapas.

### 2.1. Filtros Temporais e Institucionais
* **Ano da Eleição:** Selecione o pleito desejado (**2026, 2024, 2022, 2020, 2018, 2016, 2014, 2012, 2010 ou 2008**).
* **Cargo em Disputa:** Exibe apenas os cargos disputados naquele ano específico:
  * *Eleições Gerais:* Presidente, Governador, Senador, Deputado Federal, Deputado Estadual.
  * *Eleições Municipais:* Prefeito, Vereador.
* **Turno:** `1º Turno` ou `2º Turno` (o seletor ajusta-se automaticamente apenas aos cargos e anos onde houve segundo turno).

### 2.2. Foco da Análise: Candidato vs Partido
* **👤 Analisar por Candidato:**
  * Permite escolher um candidato específico no menu suspenso (ordenado pelos mais votados, com total de votos nominais e partido).
  * **Opção Especial:** `⭐ TODOS (Mapa de Vencedores / Mais Votados)`. Quando selecionada, o painel entra no modo *Consolidado*, mapeando quem foi o primeiro colocado em cada município, zona, bairro e colégio.
* **🚩 Analisar por Partido:**
  * Agrega todos os votos da legenda (votos nominais de todos os candidatos do partido somados aos votos de legenda).
  * Permite ver a força global da sigla partidária no estado.

---

## 📑 3. Guia Detalhado das 8 Abas Analíticas

---

### Aba 1: 🌍 Regiões de Desenvolvimento (12)

#### O que a tela apresenta:
* **Mapa Coroplético Macrorregional:** O mapa de Pernambuco dividido em suas 12 Regiões de Desenvolvimento oficiais (*Metropolitana, Mata Norte, Mata Sul, Agreste Central, Agreste Setentrional, Agreste Meridional, Sertão do Moxotó, Sertão do Pajeú, Sertão Central, Sertão de Itaparica, Sertão do Araripe e Sertão do São Francisco*).
* **Métricas por Região:** Volume de votos nominais, percentual sobre os votos válidos regionais e índice **QL (Quociente Locacional)**.
* **Placar Territorial de Conquistas (no modo Partido):** Destaque visual dos partidos que lideram em cada macro-região.
* **Tabela Completa:** Lista ordenada com total de votos, válidos e percentuais para download.

#### Análises Estratégicas Possíveis:
1. **Identificação da Base Geográfica Central:** Descobrir com clareza em qual região o candidato é hegemônico (ex: "Político da Zona da Mata" vs "Líder no Sertão").
2. **Análise de Desbalanceamento (QL):** Um $QL > 1,0$ indica que o candidato é desproporcionalmente mais forte naquela região do que na média do estado. Um $QL < 0,5$ aponta áreas onde a campanha não conseguiu penetração.
3. **Estratégia para Eleições Majoritárias (Governador/Senador):** Ninguém vence uma eleição estadual sem equilibrar a Região Metropolitana (que concentra mais de 40% dos votos) com as duas maiores regiões do interior (Agreste Central e Sertão do São Francisco).

---

### Aba 2: 🏛️ Municípios (185)

#### O que a tela apresenta:
* **Mapa de Calor dos 185 Municípios de PE:** Cada cidade colorida pela intensidade de votação do candidato selecionado ou pela cor oficial do partido do vencedor.
* **No Modo Mapa de Vencedores:**
  * Mostra o 1º colocado de cada cidade, com o partido, votos, percentual e a **Margem de Vitória** (vantagem em p.p. sobre o 2º colocado).
  * **Placar de Prefeituras / Cidades Conquistadas:** Ranking dos partidos que mais venceram municípios no pleito.
* **No Modo Candidato Individual:**
  * Top 10 cidades onde mais pontuou em votos absolutos (volume).
  * Top 10 cidades onde obteve a maior porcentagem de votos válidos (fidelidade).
* **Filtros Contextuais:** Permite filtrar os municípios por Região de Desenvolvimento ou pesquisar uma cidade diretamente.

#### Análises Estratégicas Possíveis:
1. **Mapeamento de Cidades "Fortaleza" vs Cidades "Disputadas":** Identifica municípios onde a vitória ocorreu com margens folgadas (> 20 p.p.) versus cidades onde a disputa foi decidida por poucas centenas de votos (< 5 p.p.), que exigem atenção redobrada em reeleições.
2. **Cobrança de Alianças e Apoios Locais:** Deputados federais e estaduais conseguem auditar com precisão cirúrgica se o prefeito ou liderança aliada de um município entregou a votação prometida.
3. **Detecção de Vácuos Eleitorais:** Aponta municípios populosos onde nenhum candidato consolidou liderança absoluta, servindo como alvo prioritário para expansão de campanha.

---

### Aba 3: 🗳️ Zonas Eleitorais (209)

#### O que a tela apresenta:
* **Mapa Territorial das 209 Zonas:** Segmentação político-administrativa da Justiça Eleitoral.
* **Foco Específico por Município:** Permite selecionar um município (com padrão automático no **Recife**, que possui 11 Zonas Eleitorais: 1ª, 2ª, 3ª, 4ª, 5ª, 6ª, 7ª, 8ª, 9ª, 149ª e 150ª) ou inspecionar municípios de zona única no interior.
* **Gráficos e Indicadores por Zona:** Votos válidos, abstenção eleitoral, votos brancos/nulos e total de eleitores aptos.

#### Análises Estratégicas Possíveis:
1. **Segmentação Sociopolítica em Grandes Cidades:** Nas cidades de grande porte (Recife, Jaboatão, Olinda, Caruaru, Petrolina), cada zona eleitoral agrupa bairros com realidades de renda e demandas distintas. Esta tela revela onde a mensagem de um candidato conversa melhor com a classe média versus áreas de periferia/morros.
2. **Monitoramento de Abstenção por Zona:** Descobrir zonas eleitorais onde a abstenção foi historicamente elevada (> 20%), indicando locais onde operações de "transporte e incentivo ao comparecimento" podem virar uma eleição apertada.

---

### Aba 4: 🏘️ Bairros & Distritos (1.058)

#### O que a tela apresenta:
* **Mosaico Territorial dos Bairros:** A malha geográfica mais detalhada do estado, cruzando as seções eleitorais com os perímetros oficiais de bairros urbanos e distritos municipais.
* **No Recife (94 Bairros):** Visualização completa de Boa Viagem, Casa Amarela, Madalena, Várzea, Santo Amaro, Afogados, Ibura, Pina, etc.
* **Barra de Pesquisa de Bairros:** Localização instantânea digitando o nome do bairro ou distrito.
* **Tabela de Classificação de Bairros:** Ranking do 1º ao último colocado em votos e percentual no bairro.

#### Análises Estratégicas Possíveis:
1. **Micropolítica para Vereadores e Prefeitos:** Indispensável para campanhas municipais. Mostra exatamente em quais quarteirões e comunidades o candidato é preferido.
2. **Roteirização de Atos de Rua:** Planejamento eficiente de caminhadas, carreatas, comícios e panfletagens, direcionando a militância e o tempo do candidato exatamente para os bairros com maior densidade eleitoral favorável ou bairros indefinidos com grande número de indecisos.

---

### Aba 5: 🏫 Colégios Eleitorais (3.406)

#### O que a tela apresenta:
* **Mapa de Pontos Interativo (Pins Georreferenciados):** Cada escola, faculdade ou prédio público onde funcionam seções eleitorais em Pernambuco.
* **Detalhes por Colégio:** Nome da escola, endereço completo, bairro, zona eleitoral, lista de seções ativas e total de eleitores aptos a votar no local.
* **Modo Vencedores Urna a Urna:** Identifica visualmente o candidato ou partido que venceu dentro de cada colégio eleitoral.
* **Busca Inteligente:** Encontre colégios pelo nome da escola (ex: *"Paulo Freire"*, *"FBV"*), pela zona ou pela seção.

#### Análises Estratégicas Possíveis:
1. **Foco nos "Mega-Colégios":** Uma única escola em bairros populosos pode abrigar de 5.000 a 10.000 eleitores. Vencer com folga em 5 ou 6 megacolégios pode garantir a eleição de um vereador ou deputado.
2. **Mobilização de Fiscais de Seção e Dia da Eleição (D-Day):** Planejar a alocação de delegados partidários, fiscais de urna e equipes de boca de urna exatamente nos colégios estratégicos onde o candidato tem potencial de crescimento ou risco de assédio por adversários.

---

### Aba 6: 🔗 Cruzamentos & Dobradinhas

#### O que a tela apresenta:
* **Configuração Cruzada (Opção A vs Opção B):** Permite selecionar dois candidatos ou legendas, inclusive de pleitos ou cargos diferentes (ex: *Deputado Federal A em 2022* vs *Governador B em 2022*, ou *Deputado Federal A* vs *Deputado Estadual B*).
* **Gráfico de Dispersão (Scatter Plot):** Eixo X representando a força do Candidato A e Eixo Y representando a força do Candidato B em cada município.
* **Coeficiente de Correlação de Pearson ($r$):**
  * $r > +0,7$: Altíssima correlação positiva (caminham juntos).
  * $r \approx 0,0$: Votações independentes (sem influência mútua).
  * $r < -0,5$: Correlação negativa (polarização ou canibalismo eleitoral).
* **Matriz Estratégica dos 4 Quadrantes Políticos:**
  * **Q1 (Dobradinha de Ouro - Ambos Fortes):** Municípios onde A e B lideram juntos acima da média.
  * **Q2 (Território de Herança - B Forte, A Fraco):** Redutos do aliado B onde o candidato A tem espaço para crescer e herdar votos.
  * **Q3 (Deserto Político - Ambos Fracos):** Áreas neutras sem relevância eleitoral imediata para a dupla.
  * **Q4 (Base Própria - A Forte, B Fraco):** Redutos consolidados de A onde ele tem potencial de puxar votos para o parceiro B.

#### Análises Estratégicas Possíveis:
1. **Planejamento de Dobradinhas Parlamentares:** Avaliar com dados empíricos se a parceria entre um Deputado Federal e um Deputado Estadual é complementar ou se eles estão disputando os mesmos eleitores na mesma base.
2. **Auditoria de Transferência de Votos Majoritários:** Verificar se o apoio de um candidato a Governador ou Presidente efetivamente puxou votos para a bancada legislativa de sua coligação no interior.

---

### Aba 7: 🎯 Matching Recife (3 Níveis)

#### O que a tela apresenta:
* **Painel Especializado na Capital do Estado:** O Recife representa quase 20% do eleitorado de Pernambuco. Esta tela foi construída especificamente para analisar a capital em 3 níveis correlacionados:
  1. *Nível 1:* Consolidado Geral do Recife (Métricas macro e abstenção).
  2. *Nível 2:* As 11 Zonas Eleitorais do Recife.
  3. *Nível 3:* Os 94 Bairros Oficiais do Recife.
* **Geometria Insular Otimizada:** Fernando de Noronha é contabilizado administrativamente na 4ª Zona Eleitoral continental conforme as regras do TRE, mas sua geometria marítima é filtrada no mapa para não afastar ou distorcer a malha urbana da capital.

#### Análises Estratégicas Possíveis:
1. **Inteligência para Campanhas na Capital:** Diagnosticar em poucos segundos como a votação migra entre as zonas centrais, a orla (Boa Viagem/Pina) e a Zona Norte/Noroeste (Casa Amarela, Nova Descoberta, Dois Irmãos).
2. **Conexão entre Zonas e Bairros:** Entender exatamente quais bairros puxam o resultado de cada zona eleitoral recifense.

---

### Aba 8: ⚖️ Comparativo de Desempenho entre Eleições

#### O que a tela apresenta:
* **Comparação Temporal Parametrizável (Até 4 Pleitos):**
  * **👤 Candidato A:** Selecione a *Eleição 1 (Base/Passado)* e a *Eleição 2 (Comparação/Recente)*. Permite escolher tanto o **mesmo candidato** (ex: *João Campos 2020* vs *João Campos 2024*) quanto **sucessores do mesmo grupo político** (ex: *Danilo Cabral 2022* vs *João Campos 2026*).
  * **👥 Candidato B (Opcional):** Checkbox para habilitar a comparação simultânea com um adversário ou concorrente (ex: *Marília Arraes 2020* vs *Gilson Machado 2024*).
* **Seletor de Granularidade Territorial:**
  * 🌍 *Regiões de Desenvolvimento (12)*
  * 🏛️ *Municípios (185)*
  * 🗳️ *Zonas Eleitorais (com filtro de município, padrão Recife)*
  * 🏘️ *Bairros & Distritos (com filtro de município, padrão Recife)*
  * 🏫 *Colégios Eleitorais (com barra de busca)*
* **Gráfico de Barras Agrupadas por Território:** As barras de todos os pleitos selecionados ficam **agrupadas lado a lado em cada unidade territorial** (ex: na Zona 1 ficam [A 2020] [A 2024] [B 2020] [B 2024]), permitindo comparação visual imediata.
* **4 Alternadores de Métrica no Gráfico:**
  1. *Votos Nominais (Volume absoluto)*
  2. *% Votos Válidos (Desempenho relativo)*
  3. *Δ Saldo de Votos (Pleito 2 - Pleito 1)*
  4. *Δ Variação % em p.p. (Pleito 2 - Pleito 1)*
* **Cards de KPIs Resumo:** Destaque para o crescimento total de votos, variação em pontos percentuais e saldo de vantagem entre A e B no pleito recente.
* **Tabela Analítica Completa & Download em CSV:** Tabela com todos os territórios ordenados pelo maior volume ou maior delta de crescimento, pronta para exportação.

#### Análises Estratégicas Possíveis:
1. **Medição do Crescimento Real de Mandato:** Avaliar onde o titular mais ganhou votos da primeira eleição para a reeleição (ex: descobrir em quais zonas do Recife a aprovação da gestão municipal mais se converteu em novos votos entre 2020 e 2024).
2. **Auditoria de Espólio Político:** Comparar se o candidato de continuidade manteve, ampliou ou encolheu os votos do titular anterior no interior do estado.
3. **Análise de Fuga de Votos para a Oposição:** Confrontando A e B, identificar se a perda de votos de um partido em determinada região migrou diretamente para o opositor ou se converteu em abstenção/brancos/nulos.

---

## 🎯 4. Matriz de Casos de Uso por Perfil Político

| Perfil do Usuário | Abas Mais Recomendadas | Principal Pergunta Respondida |
|---|---|---|
| **Candidato a Prefeito / Vereador** | Abas 4 (Bairros), 5 (Colégios) e 8 (Comparativo) | *Onde estão meus votos bairro a bairro e qual colégio eleitoral tem mais eleitores indecisos?* |
| **Candidato a Deputado Federal / Estadual** | Abas 1 (Regiões), 2 (Municípios) e 6 (Cruzamentos) | *Quais municípios meus prefeitos aliados controlam e com qual parceiro de chapa devo fazer dobradinha?* |
| **Candidato a Governador / Senador** | Abas 1 (Regiões), 2 (Municípios) e 8 (Comparativo) | *Qual o equilíbrio de forças entre a RMR, o Agreste e o Sertão, e onde o governo mais cresceu?* |
| **Coordenador de Campanha / Marqueteiro** | Abas 3 (Zonas), 6 (Cruzamentos) e 8 (Comparativo) | *Onde concentrar recursos de publicidade, carreatas e qual narrativa precisa ser calibrada por região?* |
| **Presidente de Partido / Analista Político** | Abas 2 (Municípios - Vencedores) e 8 (Comparativo) | *Quantos municípios o partido conquistou e qual a taxa de retenção de votos da legenda ao longo dos anos?* |

---

## 📖 5. Glossário de Indicadores Eleitorais

* **Votos Nominais:** Votos atribuídos diretamente a um candidato individual.
* **Votos Válidos:** Votos nominais somados aos votos de legenda partidária (exclui votos brancos e nulos). Todos os percentuais oficiais do TSE consideram a base de válidos.
* **Quociente Locacional (QL):** Mede a concentração relativa de votos:
  $$\text{QL} = \frac{\% \text{ de Votos do Candidato na Região}}{\% \text{ de Votos do Candidato no Estado}}$$
  * $\text{QL} > 1$: O candidato tem hiper-representação positiva na região (reduto eleitoral).
  * $\text{QL} < 1$: O candidato tem sub-representação na região.
* **Pontos Percentuais (p.p.):** A diferença aritmética entre dois percentuais (ex: crescer de 25% para 30% representa um ganho de $+5\text{ p.p.}$, embora represente $+20\%$ de crescimento relativo).
* **Margem de Vitória:** Diferença percentual ou nominal entre o primeiro e o segundo colocado em uma unidade territorial.
* **Abstenção:** Percentual de eleitores aptos cadastrados que não compareceram às urnas no dia da votação.
