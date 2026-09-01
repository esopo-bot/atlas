---
name: visao-de-fora
description: Gera o relatório de visão externa de um negócio local — o que a internet e os dados públicos mostram sem nenhum acesso interno - demografia por raio de 1/2/3 km (Censo/IBGE), renda do território e por bairro, vizinhança e concorrência (OpenStreetMap), fichas do Google e captura da marca nos canais, retrato datado das redes, régua do setor e plano de captação premium, em PDF com a identidade do cliente onde cada achado carrega a prova. Use quando pedirem análise, diagnóstico, raio-x, pesquisa de mercado ou relatório sobre uma empresa, loja, estúdio ou negócio (de amigo, cliente ou prospecto), quando perguntarem "o que a IA enxerga do meu negócio", ou quando quiserem população, renda ou concorrência num raio a partir de um endereço.
metadata:
  pedidos-de-exemplo:
    - "faz aquele relatório de visão externa para a loja do meu amigo, o site é tal e o instagram é tal"
    - "quero saber quanta gente mora num raio de 2 km da minha loja e qual a renda média"
    - "analisa o que aparece na internet sobre esse estúdio, sem contexto nenhum, como se você não conhecesse"
    - "roda a visão de fora de novo nessa empresa e compara com a rodada passada"
---

# Visão de fora

O relatório mostra ao dono de um negócio o que qualquer pessoa — e a IA —
enxerga de fora. O valor está nas regras, não na prosa:

- **Nada de dentro.** Nenhum acesso interno, nenhuma conta criada. O que
  pedir login que o dono não autorizou vira pergunta na última página.
- **Cada achado carrega a prova** — o comando, a fonte ou o print datado
  que o produziu. Informação sem prova NÃO entra: achado sem instrumento
  é opinião, e opinião não sustenta conversa comercial.
- **Retrato datado.** Números de rede social entram num JSON com data:
  crescimento não tem API pública gratuita, então a série histórica é
  construída por retratos sucessivos — e as entregas datadas ficam lado a
  lado na pasta para comparar períodos.
- **Exemplo comercial não carrega preço.** Se o relatório é isca ou
  cortesia, nenhum valor de quem assina entra nele — e nenhuma promessa
  de resultado em número.

## Fase 0 — enquadramento e a pasta do caso

Feche com quem pediu antes de coletar: o que o dono do negócio autorizou
(navegação logada nas redes? qual conta?), o que fica de fora, e onde o
trabalho mora. A pasta do caso guarda nome de cliente — ela vive **fora de
repositório público**, com git próprio, nunca na camada.

A estrutura da pasta, o `perfil.md` e a issue fixa do caso são padrão e
não se redescobrem: `references/estrutura-do-projeto.md`. Caso novo nasce
com a estrutura inteira; caso antigo converge para ela na primeira rodada.

## Fase 1 — a identidade visual do cliente

O relatório veste a marca do cliente, não a nossa:

1. **Cores computadas, não a olho**: extraia do site ou da rede as cores
   reais — `getComputedStyle` na página via navegador, ou os valores do
   CSS baixado. Baixe também o logo (a pasta `pecas/marca/`).
2. **A paleta dos gráficos passa pelo validador da skill `dataviz`**
   (`scripts/validate_palette.py` dela; o caminho muda por versão —
   localize com `find`). Cor de marca crua costuma reprovar em contraste
   (≥3:1), croma ou banda de luminosidade: ajuste a cor até passar, sem
   descaracterizar a marca.
3. **Registre no `perfil.md`** a cor crua e a cor aprovada, com a saída do
   validador. Rodada futura usa a aprovada direto.

## Fase 2 — a âncora geográfica

Transforme o endereço em lat/lon (Nominatim/OSM resolve de graça; um
`curl` com User-Agent identificado, 1 requisição por segundo). Confira o
ponto contra a ficha do Google Maps — endereço de site e de ficha divergem
com frequência, e a divergência já é achado.

## Fase 3 — o terreno em números oficiais

Três instrumentos prontos em `scripts/`, todos com `--testar`:

- `raio_demografico.py` — população, domicílios, densidade e faixas
  etárias por raio, do Censo 2022 (agregados por setor censitário).
  Entradas, baixadas uma vez por UF de `ftp.ibge.gov.br`, caminho base
  `Censos/Censo_Demografico_2022/Agregados_por_Setores_Censitarios/`:
  malha em `malha_com_atributos/setores/gpkg/UF/<UF>/<UF>_setores_CD2022.gpkg`
  e demografia em `Agregados_por_Setor_csv/Agregados_por_setores_demografia_BR.zip`.
- `renda_por_raio.py` — renda relativa do território. O Censo 2022 não
  publica renda por setor; o de 2010 publica (Básico: `V005` = renda
  média mensal do responsável pelo domicílio em R$ de 2010, `V001` =
  domicílios), então o produto principal é a **razão** entre a renda
  média do raio e a média do município — o mapa relativo envelhece bem,
  o valor nominal não. Rotule sempre a fonte. Entradas: malha 2010
  (SHP+DBF) de `geoftp.ibge.gov.br`, caminho
  `organizacao_do_territorio/malhas_territoriais/malhas_de_setores_censitarios__divisoes_intramunicipais/censo_2010/setores_censitarios_shp/<uf>/`,
  e o CSV do Básico de `ftp.ibge.gov.br`, caminho
  `Censos/Censo_Demografico_2010/Resultados_do_Universo/Agregados_por_Setores_Censitarios/`.
- `renda_por_bairro.py` — a mesma régua, bairro a bairro: recebe um JSON
  de centroides (`{bairro, lat, lon}`) e devolve a razão de cada bairro
  sobre a média do município. Os centroides vêm do Nominatim
  (User-Agent identificado, 1 req/s) e **cada um se confirma por segunda
  consulta independente** antes de entrar no JSON. Bairro com 1–2
  setores no raio é amostra fina: a ferramenta avisa na saída, e o
  gráfico do relatório confessa a fragilidade no próprio rótulo.

Some setores pelo centro (envelope/bbox): para setor urbano o erro é
muito menor que a banda do raio — e declare o método no relatório.

## Fase 4 — a vizinhança

Overpass API (OSM), três consultas: concorrentes da categoria, prédios
residenciais (`building=apartments`), comércio e serviços por tipo.
Grave cada consulta executada. **OSM é piso, não teto** — escreva isso
no relatório, senão o número mente por omissão.

## Fase 5 — a vitrine digital e a captura da marca

Na ordem, porque uma alimenta a outra:

1. **Site**: título, meta, para onde apontam os CTAs (número existe?),
   indícios de plano gratuito (banner de construtor de site).
2. **Google**: a ficha própria E o que a busca pelo nome da marca
   devolve — quem vence a busca? Volume e idade das avaliações contam
   mais que a nota; compare com os concorrentes diretos, não com a média.
3. **Redes**: seguidores, seguindo, frequência real de posts, conteúdo
   próprio versus repost, engajamento dos últimos posts, post fixado
   (data!), e os **links entre canais** — canal ativo apontando para
   perfil morto é vazamento de tráfego diário.
4. **Captura da marca, canal por canal**: procure homônimos, fichas e
   handles duplicados em TODOS os canais onde o segmento vive — Maps,
   busca orgânica, redes, convênios e agregadores do setor. Para cada
   ficha rival, meça a **renda do território dela** com
   `renda_por_bairro.py`: o contraste dimensiona quanto do desvio dói.
5. **Concorrência em prova social**: tabela nota × volume de avaliações
   no Google, separando os pares premium das redes de volume DO segmento
   — a briga do boutique é com boutique, e a régua é o maior volume da
   cidade, não a média.

Tudo vira o retrato datado (JSON) da regra de ouro. E **HTTP 200 não
prova página viva em rede social** — o código vem da casca; abra a
página no navegador e leia o que ela diz.

### Prints datados — evidência de primeira classe

Print de navegador é prova tanto quanto comando: ficha do Maps (a própria
E a que a busca da marca devolve), o cartão da marca na busca do Google,
perfis das redes, páginas de convênio/agregador, site. Sempre com data no
nome ou na legenda. O navegador de perfil persistente salva na raiz de
onde a sessão abriu — mova para `pecas/prints/` e gere a versão do PDF em
`pecas/prints/otimizados/` (JPEG, ~1100px de largura), para o PDF final
ficar em torno de 1–2 MB.

## Fase 6 — a régua do setor

Busque o número de penetração/benchmark do setor em fonte nomeável
(associação setorial, Sebrae, relatório anual) e aplique à população do
raio. Premissa nacional em território acima da média é piso — diga isso.

## Fase 7 — o plano de captação premium

O relatório fecha com caminho, não com promessa:

- **Parceiros-âncora NOMEADOS**, com nota e endereço — e do tipo certo
  para o segmento, descoberto com dado (Overpass e Maps mostram que
  vizinhança de fato existe e pontua), nunca por analogia com outro caso.
- **Mídia geolocalizada** nos bairros que a Fase 3 provou serem de alta
  renda — o gráfico de razão por bairro é o argumento.
- **Convênios e agregadores do segmento**, quando existirem — inclusive
  para consertar a captura de marca que a Fase 5 achou.
- **Sem prometer números.** Potencial é conta declarada com premissa; meta
  é conversa do dono com o cliente.

## Fase 8 — o mock de redesign do site

Uma página HTML (`pecas/mock-site/`) com a identidade aprovada na Fase 1,
para o relatório mostrar o método, não vender template. O print se tira
com a página servida em `localhost` (`python3 -m http.server`) — `file://`
é bloqueado no navegador — e entra DENTRO do relatório como exemplo.

## Fase 9 — o relatório

Molde pronto em `references/molde-relatorio.html` (placeholders
`${...}`): uma seção por página A4, cada seção fecha com a leitura ("o
que este número significa para este negócio"), última página lista fonte
por fonte, e a penúltima faz as **perguntas que só o dono responde**.
A capa carrega o logo e as cores da Fase 1; os gráficos usam a paleta
aprovada pelo validador. O relatório é UM PDF com tudo dentro — prints
inclusive. Gere com navegador headless e confira com `pdfinfo`. A entrega
datada fica em `pecas/entregas/`, ao lado das anteriores.

## Fase 10 — o cético, obrigatório

Antes de dar por pronto, rode o cético (a skill `cetico` é o rito):

- **Re-rode todo instrumento citado** e confira os números do relatório
  um a um contra a saída nova.
- **Re-meça todo link** no navegador — não por código HTTP.
- **Zero só vale com contraprova positiva**: o instrumento que devolve
  vazio tem que provar que acha algo onde algo existe.
- **Fragilidade se confessa no texto**, no mesmo volume da evidência:
  amostra fina, fonte de 2010, OSM incompleto, premissa nacional.

O que não passar sai do relatório — não se reescreve mais bonito.

## O fechamento — a rodada devolve para a skill

Toda rodada termina com a análise de promoção (a skill
`analise-de-promocao`): o que o caso ensinou de genérico volta para ESTA
skill — pelas barreiras de entrada da camada, em issue de camada. Ferramenta nova do caso é
candidata a `scripts/`; armadilha nova é candidata à lista abaixo. O que
é do cliente fica no `perfil.md` dele.

## Armadilhas que já custaram achado

Medidas em uso real — não são hipóteses:

- **Ficha homônima** pode vencer a busca pelo nome do negócio e prender a
  reputação no lugar errado. Registre como "a confirmar com o dono",
  nunca como fato.
- **Volume vence nota**: 5,0 com 6 avaliações antigas perde de 5,0 com 58
  recentes. É o critério de quem pesquisa online antes de comprar.
- **Máquina de conteúdo fora do negócio**: canal que publica todo dia mas
  fala com o público errado (e com links quebrados) parece saúde e é
  vazamento.
- **Silêncio de dado não é fato**: campo de bairro vazio no IBGE, OSM
  incompleto — confesse a lacuna em vez de imprimir zero.
- **Cor de marca crua reprova no validador**: contraste e croma de site
  raramente servem para gráfico. Valide antes de desenhar, não depois.
- **`curl` 200 em rede social não é instrumento**: a casca responde 200
  com a página morta dentro. Só o navegador lê a verdade.
- **Print nasce fora da pasta do caso**: o navegador salva na raiz da
  sessão; quem não move para `pecas/prints/` perde a prova no dia
  seguinte.
- **Google barra navegador anônimo com CAPTCHA**: busca e Maps saem do
  perfil persistente (com cookies), nunca de headless limpo — e CAPTCHA
  não se contorna. Headless limpo serve para site do cliente e mock.
- **Meta e página discordam na rede social**: o `meta description` vem de
  cache e o cabeçalho renderizado é o vivo — números levemente
  diferentes na mesma tela. Registre no retrato qual dos dois foi lido;
  a diferença é banda de ruído, não erro.
- **Na paginação do PDF, a leitura vem antes do print**: figura sozinha
  na página seguinte parece intencional; a nota de leitura órfã parece
  descuido. Confira as quebras com o PDF convertido em imagem.
