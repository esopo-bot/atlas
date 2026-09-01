# Curadoria de fontes — onde a visão de fora consulta

Cada fonte com o que ela responde, como se chama e a armadilha dela.
Tudo aqui foi usado em rodada real; fonte nova entra depois de medida,
com a armadilha que cobrou. A regra que atravessa todas: **zero só vale
com contraprova positiva na mesma sessão.**

## Território e demografia (oficial)

| Fonte | Responde | Como | Armadilha |
|---|---|---|---|
| Censo 2022 (FTP do IBGE) | população, domicílios, idade por setor censitário | `scripts/raio_demografico.py` | download por UF, uma vez |
| Censo 2010 (FTP do IBGE) | renda relativa por setor | `scripts/renda_por_raio.py` e `renda_por_bairro.py` | valor nominal envelheceu; use a razão sobre o município |
| API de agregados do IBGE | régua do município (PIB, população) sem baixar base | `curl` na `servicodados.ibge.gov.br/api/v3/agregados` | colchete sem codificar devolve 200 com corpo vazio |
| Nominatim (OSM) | endereço → lat/lon; centroide de bairro | `curl` com User-Agent identificado, 1 req/s | centroide se confirma por segunda consulta independente |
| Overpass (OSM) | concorrentes, prédios, comércio por raio | consulta gravada na pasta do caso | OSM é piso, não teto — escreva isso no relatório |

## Registro público de empresa

| Fonte | Responde | Como | Armadilha |
|---|---|---|---|
| RDAP do registro.br | titular do domínio (CPF ou CNPJ), datas de registro e expiração, nameservers | `curl -s https://rdap.registro.br/domain/<dominio>` | rode contraprova com domínio vivo; CPF vem mascarado e mesmo assim NÃO se copia |
| Wayback Machine (CDX) | linha do tempo do site: quando nasceu, quando morreu | `curl -s 'https://web.archive.org/cdx/search/cdx?url=<alvo>&output=json'` | vazio precisa de contraprova (URL sabidamente arquivada na mesma chamada); se a ferramenta de fetch do harness recusar o domínio, o `curl` responde |
| Dados abertos do CNPJ (Receita) | razão social, quadro societário, endereço cadastral, situação | precisa do NÚMERO do CNPJ; sem ele, vira pergunta ao dono | agregadores (cnpj.biz etc.) vivem atrás de Cloudflare — "Just a moment..." com HTTP 200 |
| Diário oficial do município | alvará, licença, notificação, licitação | busca pelo nome fantasia no índice público do diário da praça (o JusBrasil indexa muitos) | via buscador é melhor-esforço: zero indexado ≠ zero publicado; a busca definitiva pede CNPJ |
| Portal de transparência (municipal e federal) | se o negócio VENDE ao poder público ou recebe repasse | portal da prefeitura da praça; portaldatransparencia.gov.br | para negócio B2C pequeno o rendimento esperado é zero — a lente vale para prospecto B2B; consulta de alvará/NFS-e exige CNPJ |

## Imprensa

| Fonte | Responde | Como | Armadilha |
|---|---|---|---|
| Jornal da praça | aparições, prêmios, pauta do segmento | busca pela marca + cidade; depois busca do SEGMENTO no mesmo veículo | a segunda busca é a contraprova: prove que o veículo cobre o setor antes de dizer que o zero da marca significa algo |
| Portais regionais (G1 da região etc.) | cobertura fora do jornal principal | busca pela marca + praça | homônimo de outra praça vence a busca — confira cidade antes de atribuir |

A leitura que a lente de imprensa entrega: zero aparição em veículo que
cobre o segmento não é passivo — é pauta não ocupada, e vira item do
plano de captação.

## Redes e vitrine

| Fonte | Responde | Como | Armadilha |
|---|---|---|---|
| Perfil público no navegador persistente | seguidores, cadência, bio, links | leitura da página renderizada, nunca do HTTP | meta e cabeçalho divergem (cache): registre qual foi lido |
| **Aba Reels do Instagram** | visualizações públicas POR REEL — o dataset de alcance que o grid de posts esconde | uma página só; grade com View Count | data do reel não aparece no grid: date pelo cruzamento com a leitura do grid de posts e confesse o "aprox" |
| Legendas do grid | mix de conteúdo, formatos, CTA, temas | o snapshot do perfil já traz as legendas — analise formato a formato | snapshot colhido antes da página carregar vem quase vazio: recolha |
| Busca da marca | hubs de link (Linktree, biolink, beacons…) ANTIGOS ainda indexados | busca pela marca em mais de um buscador | hub órfão vivo aponta para sistema morto e handle apagado — cada botão dele se verifica no navegador, um a um |

## Reputação e passivo

| Fonte | Responde | Como | Armadilha |
|---|---|---|---|
| Ficha do Google + Maps | nota, volume, recência, resposta do proprietário | perfil persistente (anônimo cai em CAPTCHA) | volume e recência contam mais que nota; compare com o par do segmento |
| Reclame Aqui | reclamações e cadastro | busca pelo nome | serviço local costuma dar zero — e zero aqui é saúde, não lacuna |
| JusBrasil | processos vinculados ao nome | busca pelo nome/praça | homônimo com processo em outra praça contamina a marca — registre como risco de confusão, nunca como fato |

## Régua do setor

| Fonte | Responde | Como | Armadilha |
|---|---|---|---|
| Associação setorial / Sebrae / relatório anual | penetração, benchmark de consumo | citar fonte nomeada + ano | premissa nacional em território acima da média é piso — diga isso; idade da fonte se confessa no relatório |
