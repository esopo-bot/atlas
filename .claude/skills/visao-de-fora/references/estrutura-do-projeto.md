# A pasta do caso — estrutura que não se redescobre

Todo caso de visão de fora mora numa pasta própria com git LOCAL, fora de
qualquer repositório público (ela guarda nome de cliente). O `git init`
vem antes do primeiro arquivo. Rodada nova não inventa estrutura: ela
encontra a pasta assim, ou a converge para isto na primeira visita.

```
consultoria-<nome>/
├── LEIAME.md        o mapa da pasta e as regras de trabalho do caso
├── perfil.md        o que toda rodada precisa saber sem redescobrir
├── dados/           retratos datados (JSON com data no nome) — o recorte do caso
│   └── brutos      LINK para a base pública compartilhada, nunca uma cópia
├── ferramentas/     cópias dos scripts da skill usadas nesta rodada
├── pecas/
│   ├── entregas/    HTML + PDF datados, lado a lado — comparar períodos
│   ├── prints/      PNGs originais datados; otimizados/ = JPEG ~1100px do PDF
│   ├── marca/       logo e material de identidade baixados
│   └── mock-site/   o mock de redesign (Fase 8)
```

A fonte das ferramentas é a skill: copie de `scripts/` para
`ferramentas/` (o caso fica reproduzível sozinho) e, se a rodada melhorar
uma ferramenta, a melhoria volta para a skill — pelas barreiras de
entrada da camada, em issue de camada — e nunca fica só no caso.

## A base pública não mora na pasta do caso

Censo, malha territorial, tabela nacional: é a mesma base para todo caso e
pesa centenas de megabytes. Copiada para dentro de cada pasta, ela multiplica
o peso — e, pior, faz a pasta de **um** cliente virar dependência dos outros,
que passam a ler de lá.

A regra tem duas metades:

- **Base pública mora uma vez, fora das pastas de caso**, em lugar que não é
  de cliente nenhum. Cada caso chega nela por link em `dados/brutos`, e o link
  fica fora do git do caso, como o diretório ficava.
- **O recorte fica dentro do caso.** Extrato feito em volta do endereço do
  cliente — raio, bairro, concorrência — é dado do cliente, não base pública,
  e nunca vai para o lugar compartilhado. De lá se compartilha a **receita**
  da consulta, com a coordenada em branco.

O lugar compartilhado carrega um mapa: o que cada base é, o comando que a
re-baixa e quem a consome. Base sem proveniência é arquivo órfão que ninguém
vai citar como prova daqui a um ano. Os arquivos pesados ficam fora do git; o
mapa entra.

Mudar base que já está em uso é mover, nunca copiar: reaponte os links antes
de fechar e prove rodando os instrumentos do caso — saída idêntica à que já
estava guardada, ou a mudança quebrou alguma coisa.

## O `perfil.md`

Uma página, atualizada a cada rodada. Seções fixas:

- **O negócio** — segmento, endereço, lat/lon confirmada, código IBGE do
  município.
- **Identidade visual** — cor crua extraída, cor APROVADA pelo validador
  da `dataviz` (com a saída do validador colada), fonte do logo.
- **Canais** — handles e URLs oficiais, um por linha, com estado na
  última rodada (vivo/morto/homônimo).
- **Concorrentes e homônimos** — quem apareceu nas rodadas, com endereço
  e território.
- **Parceiros-âncora** — os nomeados no plano de captação, com nota e
  endereço na data.
- **Decisões do dono** — o que ele autorizou, recusou ou respondeu; com
  data.

## A issue fixa do caso

`consultoria-<nome>_fixa - quadro do projeto` — aberta pela conta de
automação, **nunca fecha**. O corpo guarda: onde o projeto mora, as
regras do caso (sem valores, sem contato com cliente, tudo termina em
commit local e linha na issue), as pendências com dono marcado, e o
ponto de retomada (estado, faça agora, primeiro comando, leia só).
Estado de trabalho mora na issue; a pasta guarda a prova.
