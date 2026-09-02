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
- **A coleta é do negócio, nunca da pessoa.** O que entra é vitrine
  comercial: ficha, perfil de negócio, avaliação, cadastro público de
  empresa. Nome, telefone e rosto de cliente que aparecem em comentário
  ou avaliação não são coletados, contados nem citados — nem em anexo.
  A ANPD trata raspagem como tratamento de dado pessoal mesmo quando o
  dado é público (Radar Tecnológico nº 3, nov/2024), e o princípio da
  necessidade é o que reprova coleta indiscriminada. O relatório fala de
  quantos avaliaram, nunca de quem avaliou.

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

**Quando o geocodificador não fecha, a coordenada sai do Plus Code da
ficha.** O OSM pode conhecer a via com outro tipo e outro bairro, e não
ter nó nenhum com o número da porta; a ficha do Google publica um Plus
Code, e ele decodifica sem chave nenhuma:

```bash
python3 scripts/plus_code.py --decodificar '<codigo curto da ficha>' \
  --referencia <lat> <lon>
```

O código curto da ficha (`XXXX+XX Cidade`) recompõe o inteiro a partir de
uma referência a menos de 50 km — o centro do município que o Nominatim
devolveu serve. A saída traz o centro da célula e o raio dela em metros,
que é a precisão declarada no relatório. O `--testar` é a ida-e-volta —
codifica, decodifica e cobra erro abaixo de 5 m — mais os vetores públicos
do padrão, porque ida-e-volta fecha em qualquer orientação da grade e só o
vetor de fora acusa a grade invertida.

**O ViaCEP é a terceira via da confirmação do endereço e a origem do
código IBGE do município.** Uma chamada devolve logradouro, bairro e o
campo `ibge` — a Fase 3 precisa desse código, e quando site, ficha e OSM
discordam sobre o tipo da via ou o bairro, é o ViaCEP que arbitra:

```bash
curl -s https://viacep.com.br/ws/<cep>/json/
```

## Fase 3 — o terreno em números oficiais

Três instrumentos de território em `scripts/`, todos com `--testar`. As
entradas dos três são base pública genérica: baixe **uma vez, fora das
pastas de caso**, e aponte cada caso para lá por link — o porquê e o como
estão em `references/estrutura-do-projeto.md`.

- `raio_demografico.py` — população, domicílios, densidade e faixas
  etárias por raio, e a razão de cada faixa sobre a mesma faixa do
  município, do Censo 2022 (agregados por setor censitário).
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

**O raio sozinho não é achado — o achado é o raio CONTRA a cidade.** Esta
fase exige a comparação, não só a contagem: a fatia de uma faixa etária
no raio não diz nada ao dono até encostar na fatia da mesma faixa no
município inteiro, e é essa razão que muda a leitura do relatório (um
bairro de avós não é um bairro de festa infantil). O `raio_demografico.py`
imprime, ao lado de cada raio, `razao_sobre_municipio` por faixa — soma
os setores do município pelo mesmo método, da mesma base, sem download
novo. Contagem sem a razão não entra no relatório.

## Fase 4 — a vizinhança

Overpass API (OSM), três consultas: concorrentes da categoria, prédios
residenciais (`building=apartments`), comércio e serviços por tipo.
Grave cada consulta executada. **OSM é piso, não teto** — escreva isso
no relatório, senão o número mente por omissão.

## Fase 5 — a vitrine digital e a captura da marca

A curadoria de fontes — o que cada uma responde, como se chama e a
armadilha dela — mora em `references/fontes.md`; fonte nova só entra lá
depois de medida em rodada real.

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

Tudo vira o retrato datado (JSON) da regra de ouro, e **o caminho padrão
do retrato é o instrumento** `scripts/retrato.py`:

```bash
python3 scripts/retrato.py --alvos alvos.json --caso <caso>
```

Ele lê site, ficha do Google, Instagram, Facebook, domínios (RDAP e
Wayback, com contraprova positiva na mesma rodada) e agregadores por HTTP,
sem sessão de navegador, e grava `dados/retrato-<caso>-<data>.json`. O
`alvos.json` (negócio, site, google, instagram, instagram_homonimos,
facebook, dominios, agregadores) é dado de cliente e mora na pasta do
caso. O instrumento obedece à regra 7 — uma requisição por alvo,
`User-Agent` declarado, espera entre chamadas, nada de repetir em cima de
429 — e **confessa `nao-medido`** onde não leu: CAPTCHA, casca com HTTP
200, página que pediu login. `nao-medido` é a senha da reserva: ali, e
só ali, a coleta manual no navegador de perfil persistente completa o
retrato, lida da página renderizada — e o campo `leitura` diz de onde
cada número veio. `--forma` imprime só as chaves de um retrato, para
comparar com a rodada anterior sem expor valor. E **HTTP 200 não prova
página viva em rede social** — o código vem da casca; abra a página no
navegador e leia o que ela diz.

### O mergulho no Instagram — três páginas, três datasets

O perfil rende muito mais que seguidores e último post, sem abrir post
nenhum:

1. **A aba Reels mostra as visualizações públicas de cada reel** — o
   dataset de alcance que o grid de posts esconde, numa página só.
   Alcance não é seguidor: reel viaja além da base, e o contraste entre
   a base recente e os picos diz qual formato funciona. Date os reels
   pelo cruzamento com o grid de posts e confesse o "aprox" no retrato.
2. **As legendas do grid são o mix de conteúdo inteiro**: o snapshot do
   perfil traz legenda por legenda — classifique tema, formato e CTA, e
   procure o formato que a própria conta já provou (o que os fixados e
   os picos têm em comum). Recomendação de pauta nasce daí, não de
   opinião.
3. **Fixado tem data**: fixado antigo com números altos é músculo
   provado E vitrine parada — as duas leituras entram.
4. **Cace os hubs de link da era anterior** (Linktree, biolink, beacons…)
   na busca da marca: hub órfão continua indexado, e cada botão dele se
   verifica no navegador, um a um — agendamento antigo, handle apagado e
   formulário ainda vivo são três achados diferentes.

### Imprensa — a pauta ocupada e a não ocupada

Busque a marca + praça; depois busque o SEGMENTO no veículo da praça. A
segunda busca é a contraprova positiva: zero da marca num veículo que
cobre o setor é pauta não ocupada — item do plano de captação, não
passivo. Homônimo de outra praça vence busca: confira a cidade antes de
atribuir qualquer matéria.

### Registro público — o que se mede e o que espera o CNPJ

- **RDAP do domínio** e **Wayback (CDX)**: receitas abaixo — datam a
  presença web e dizem em nome de quem ela está (CPF ou CNPJ — marca em
  CPF é achado).
- **Com o CNPJ em mãos**: dados abertos da Receita (quadro societário,
  endereço cadastral, situação), diário oficial e NFS-e da praça.
- **Sem o CNPJ**: essas consultas viram pergunta da última página, não
  achado. Diário oficial via buscador é melhor-esforço e se confessa;
  transparência municipal/federal rende para prospecto B2B (vende ao
  poder público?), quase nada para B2C pequeno — diga isso em vez de
  imprimir zero.

### O domínio e o passado do site — dois comandos, achado grande

A vitrine de hoje não conta o que já existiu. Dois registros públicos
gratuitos contam, e ambos devolvem prova citável:

- **O domínio, no RDAP do `registro.br`** — 200 é registrado, 404 é
  livre. `curl -s -w '\nHTTP=%{http_code}\n'
  https://rdap.registro.br/domain/<dominio>`. A resposta traz `entities`
  (o titular), `events` (criação e expiração) e os `nameservers`: dá para
  ver se o domínio da marca está com o dono, com um terceiro, ou
  abandonado. Cada consulta roda com **contraprova positiva** — um
  domínio sabidamente vivo na mesma execução, senão o 404 não prova nada.
- **O passado do site, no Wayback Machine** —
  `https://archive.org/wayback/available?url=<dominio>` devolve o último
  retrato, e `https://web.archive.org/cdx/search/cdx?url=<dominio>&output=json`
  devolve a linha do tempo inteira, com data e código HTTP de cada
  captura. É a única forma barata de datar quando o site morreu.

Site fora do ar **com o domínio livre** é o achado mais caro que esta
fase produz: a marca perdeu o endereço dela e qualquer um pode registrar.
Entra no relatório com as duas saídas coladas, e vira a primeira pergunta
da página do dono.

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

**A régua do setor mede a lacuna do mapa antes de medir a lacuna do
mercado.** Quando a régua projeta N estabelecimentos do ramo no raio e o
OpenStreetMap acha uma fração disso, a leitura tentadora é "faltam
concorrentes, mercado aberto"; a leitura certa é "o OSM cadastra uma
fração do que existe". OSM é piso (Fase 4): a distância entre a projeção
e a contagem é primeiro o tamanho da lacuna do mapa, e só o que sobrar
depois de contar em fonte melhor — Maps, cadastro oficial — fala de
mercado. O relatório escreve a leitura certa, com as duas contas lado a
lado, porque o leitor faz a errada sozinho.

**A régua do município sai de graça, e é oficial.** A API de agregados do
IBGE (a mesma que alimenta o SIDRA) responde sem chave nenhuma e devolve
o número já com nome de tabela e unidade — dá para comparar o município
com o estado sem baixar base:

```bash
curl -s 'https://servicodados.ibge.gov.br/api/v3/agregados/5938/periodos/2021/variaveis/37?localidades=N6%5B<codigo_ibge>%5D'
```

`5938` é o PIB dos municípios e `37` o PIB a preços correntes;
`/agregados/<n>/metadados` diz o que cada tabela mede, e
`/api/v3/agregados` lista todas. **Codifique os colchetes** (`%5B` e
`%5D`): sem isso a API devolve corpo vazio com HTTP 200 — parece "não
tem dado" e é erro de chamada.

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

**Transbordo se mede antes de olhar**: o número de seções do HTML tem de
ser igual ao número de páginas do PDF (`pdfinfo` ou `pdftoppm` contando
as imagens). Seção que virou duas páginas é texto que vazou da folha, e a
contagem acha isso em segundos; a inspeção visual fica para depois, só
onde a conta bater.

**A rodada seguinte compara com a anterior por instrumento**, nunca de
memória: `scripts/comparar_retratos.py` lê dois retratos datados do mesmo
caso e devolve o delta folha a folha — seguidores, avaliações, razões de
renda, links vivos ou mortos — em JSON
(`dados/delta-<caso>-<de>-<ate>.json`) e em tabela Markdown, pronta para
a seção de evolução do relatório:

```bash
python3 scripts/comparar_retratos.py --antes dados/retrato-<caso>-<data-anterior>.json \
  --depois dados/retrato-<caso>-<data>.json --caso <caso>
```

Vale para qualquer par de JSONs datados de `dados/` com a mesma forma —
o `renda-bairros-<data>.json` inclusive. Campo ausente ou `nao-medido`
num dos lados sai `nao-comparavel`, nunca zero; código HTTP e RDAP mudam,
não somam; lista de concorrentes ou de bairros se alinha pelo nome, então
a ordem entre rodadas não importa. Só número entra na conta: número contra
texto é `nao-comparavel`, porque a leitura mudou, não o valor.

## Fase 10 — o cético, obrigatório

Antes de dar por pronto, rode o cético (a skill `cetico` é o rito):

- **Re-rode todo instrumento citado** e confira os números do relatório
  um a um contra a saída nova.
- **Re-meça todo link** no navegador — não por código HTTP.
- **Zero só vale com contraprova positiva**: o instrumento que devolve
  vazio tem que provar que acha algo onde algo existe.
- **Todo número do relatório tem endereço**: releia o PDF caçando
  número por número e aponte cada um ao arquivo datado de `dados/` ou
  ao print que o produziu. Número sem endereço sai — essa releitura é a
  que pega o valor digitado de memória.
- **Fragilidade se confessa no texto**, no mesmo volume da evidência:
  amostra fina, fonte de 2010, OSM incompleto, premissa nacional, data
  "aprox" de reel.

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
- **Cinza de contexto reprova no validador como categoria**: o dado de
  fundo (a cidade inteira, a média do setor) não é uma série a colorir. A
  leitura certa é des-ênfase com rótulo direto no gráfico — o neutro não
  ganha cor, ganha nome.
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
- **Domínio que não resolve não devolve HTTP nenhum**: `curl` sai com
  código `000` e a tentação é ler isso como "site fora do ar hoje". Não
  é: NXDOMAIN quer dizer que o endereço deixou de existir. Confirme com
  `host <dominio>` e com o RDAP antes de escrever a frase.
- **API oficial devolve 200 com o corpo vazio**: colchete não codificado
  na chamada do IBGE, período inexistente, localidade errada. Vazio de
  fonte oficial é erro de chamada até prova em contrário — repita com
  um parâmetro sabidamente bom antes de imprimir "sem dado".
- **Agregador de CNPJ costuma estar atrás de Cloudflare**: a resposta
  vem `Just a moment...` com HTTP 200, e código nenhum acusa. Quem lê o
  status em vez do corpo registra dado que nunca chegou — e o desafio
  não se contorna. O caminho legítimo é a base de dados abertos da
  Receita ou a consulta oficial, um CNPJ por vez.
- **Na paginação do PDF, a leitura vem antes do print**: figura sozinha
  na página seguinte parece intencional; a nota de leitura órfã parece
  descuido. Confira as quebras com o PDF convertido em imagem.
- **Snapshot de página pesada colhido cedo demais vem quase vazio**: a
  rede social ainda está montando o DOM e o snapshot sai com meia dúzia
  de nós. Vazio ali não é página vazia — recolha depois que ela carregar.
- **Ferramenta de fetch que recusa um domínio não é "sem dado"**: o
  harness pode bloquear o endereço (o Wayback, por exemplo) e o mesmo
  `curl` responde na hora. Troque o instrumento antes de declarar a
  fonte indisponível.
- **O hub de links da era anterior não morre sozinho**: continua
  indexado, vence busca da marca e aponta para agendamento desativado e
  handle apagado. Verifique cada botão no navegador — e o que ainda
  estiver VIVO ali (um formulário, um número) é achado tanto quanto o
  que morreu.
- **Contar na tela não é contar**: "sete lojas de uma rede" lidas da
  listagem impressa eram seis no arquivo gravado. Toda contagem que entra
  no relatório se produz com código sobre o arquivo gravado (`jq`, um
  `len()` em Python), nunca com o olho sobre a saída.
