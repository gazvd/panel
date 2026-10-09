# 🗳️ Painel Eleitoral de Pernambuco (2008–2026)

Aplicação interativa de visualização, inteligência eleitoral e análise geoespacial de **Pernambuco** (eleições de 2008 a 2026), cobrindo todos os 185 municípios, 209 unidades zona-município, 1.058 bairros/distritos, 3.406 colégios eleitorais e 22.111 seções oficiais do TRE-PE e TSE.

---

## ✨ Funcionalidades do Dashboard

A aplicação conta com **6 abas modulares especializadas**:

1. **🌍 Macrorregiões (12 Regiões de Desenvolvimento):**
   - Agregação por macrorregiões econômicas e geográficas (com Fernando de Noronha na Metropolitana).
   - Alternância entre Votos Nominais e Percentual (%).
   - Busca inteligente por região ou município pertencente.

2. **🏛️ Municípios (185 Municípios):**
   - Distribuição de votos e ranking Top 10 em todo o estado.
   - Mapa coroplético interativo sobre OpenStreetMap (sem restrições de API).
   - Busca inteligente com zoom automático e card de ranking estadual do município.

3. **🗳️ Zonas Eleitorais (209 Unidades Zona-Município):**
   - Delimitação zonal que preserva estritamente os limites municipais e particiona os municípios multizonais.
   - Busca rápida por número de zona ou nome da cidade.

4. **🏘️ Bairros & Distritos (1.058 Unidades Territoriais):**
   - Mosaico contínuo 100% *gapless* cobrindo todo o estado: bairros oficiais (IBGE/PCR) e distritos contíguos para cidades sem bairros formais.
   - Cruzamento espacial (*spatial join*) de colégios eleitorais para alocação precisa de votos.

5. **🏫 Colégios Eleitorais & Seções (3.406 Colégios / 22.111 Seções):**
   - Mapeamento pontual dos locais de votação com círculos dinâmicos baseados nas cores de campanha do candidato.
   - **Busca por Seção Eleitoral:** Digite o número da seção (ex: `125`) para localizar a escola e aplicar super-zoom imediato no mapa.

6. **🔗 Cruzamentos & Dobradinhas (Análise Comparativa):**
   - Cruze **qualquer Candidato A** com **qualquer Candidato B** (mesmo cargo ou cargos diferentes, ex.: Deputado Federal x Governador, ou Lula x qualquer deputado).
   - Escolha o nível de agregação: Municípios, Regiões, Zonas ou Colégios Eleitorais.
   - Cálculo automático de **Correlação de Pearson ($r$)** e **Aderência ($R^2$)** com diagnóstico de aliança/dobradinha.
   - Gráfico de dispersão (*scatter plot*) com linha de regressão linear.
   - Destaques automáticos: Maior Casamento de Votos e Bastiões exclusivos.
   - Tabela comparativa e botão de exportação (.CSV).

---

## 🎨 Identidade Visual Inteligente
As cores dos mapas coropléticos, barras e marcadores refletem automaticamente a legenda ou candidato selecionado:
* **João Campos / PSB:** Amarelo oficial (`#FEC806`)
* **Raquel Lyra / PSD:** Roxo claro (`#9B59B6`)
* **PT / Lula:** Vermelho partidário (`#E31A1C`)
* **PL / Bolsonaro:** Azul marinho (`#002B7F`)
* Demais partidos mapeados conforme suas cores de convenção.

---

## 📁 Estrutura do Repositório

```text
projetoEleicoes/
├── app.py                                 # Ponto de entrada do Streamlit
├── config.py                              # Paletas de cores, caminhos e funções de formatação PT-BR
├── requirements.txt                       # Dependências do projeto
├── README.md                              # Documentação
│
├── modules/                               # Módulos modulares das 6 abas
│   ├── data_loader.py                     # Consultas DuckDB ultrarrápidas
│   ├── geo_loader.py                      # Carregamento otimizado de GeoDataFrames
│   ├── tab_macrorregioes.py               # Aba 1: 12 RDs
│   ├── tab_municipios.py                  # Aba 2: 185 Municípios
│   ├── tab_zonas.py                       # Aba 3: 209 Zonas
│   ├── tab_bairros.py                     # Aba 4: 1.058 Bairros/Distritos
│   ├── tab_locais.py                      # Aba 5: 3.406 Colégios e 22k Seções
│   └── tab_cruzamento.py                  # Aba 6: Cruzamento & Dobradinhas
│
├── data/
│   ├── resultados_eleicoes_pe.parquet     # Base histórica de votos (rastreada via Git LFS)
│   ├── locais_votacao_pe.parquet          # Locais de votação com coordenadas e seções
│   └── locais_votacao_pe.csv              # Versão CSV
│
└── layers/                                # Camadas geoespaciais em GeoParquet e GeoJSON
    ├── regioes/
    ├── municipios/
    ├── zonas/
    ├── distritos/
    └── bairros/
```

---

## 🚀 Como Rodar Localmente

1. **Clone o repositório:**
   ```bash
   git clone https://github.com/SEU_USUARIO/NOME_DO_REPO.git
   cd NOME_DO_REPO
   ```

2. **Crie e ative um ambiente virtual:**
   ```bash
   python -m venv .venv
   # Windows (PowerShell):
   .venv\Scripts\Activate.ps1
   # Linux / macOS:
   source .venv/bin/activate
   ```

3. **Instale as dependências:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Inicie o painel:**
   ```bash
   streamlit run app.py
   ```
   Acesse no navegador: `http://localhost:8501` ou `http://localhost:8502`.

---

## 📦 Observação sobre Arquivos Grandes (Git LFS)
O arquivo `data/resultados_eleicoes_pe.parquet` possui ~235 MB. Para subir ao GitHub, é necessário utilizar o **Git LFS**:
```bash
git lfs install
git lfs track "*.parquet"
git add .gitattributes
```
