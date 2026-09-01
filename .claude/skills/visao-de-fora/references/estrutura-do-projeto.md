# A pasta do caso — estrutura que não se redescobre

Todo caso de visão de fora mora numa pasta própria com git LOCAL, fora de
qualquer repositório público (ela guarda nome de cliente). O `git init`
vem antes do primeiro arquivo. Rodada nova não inventa estrutura: ela
encontra a pasta assim, ou a converge para isto na primeira visita.

```
consultoria-<nome>/
├── LEIAME.md        o mapa da pasta e as regras de trabalho do caso
├── perfil.md        o que toda rodada precisa saber sem redescobrir
├── dados/           brutos baixados e retratos datados (JSON com data no nome)
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
