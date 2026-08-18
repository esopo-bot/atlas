<!-- GERADO de nucleo/regras.json e nucleo/vocabulario.json pelo `montar.py --sincronizar`. Editar aqui se perde. -->

# Instruções para agentes

Para qualquer agente de IA neste repositório.

## O repositório

- Camada genérica de skills e conhecimento para sessões de IA; `montar.py` a
  instala em outros repositórios.
- Pastas de conteúdo, que viajam para quem instala: `conhecimento/` e
  `.agents/skills/`.
- Fonte que instrumento lê: `nucleo/`. `modulos/` não viaja — chega por
  `--modulo <nome>`.
- Onde escrever cada coisa: `conhecimento/mapa-do-repositorio.md`.
- Rode `python montar.py --sincronizar` depois de editar página, skill, módulo
  ou `nucleo/`.

## Ordens desta casa

- Não commite, não empurre, não publique: deixe os arquivos para o dono
  conferir. O teto é o ensaio, que mostra o que subiria sem subir. Destrutivo é
  dele. Esta é a única casa desta regra: outro arquivo que disser diferente
  está errado.
- Repositório público: nada de nome de pessoa ou empresa, credencial ou caminho
  de máquina em arquivo, commit, branch ou issue. Na dúvida, pergunte.
- Não altere o que não foi pedido.
- Escreva em pt-BR: conclusão primeiro, frases curtas.

## As regras da camada

Citadas por número; os itens de cada uma: `conhecimento/regras-da-camada.md`.

1. Abra a sessão na raiz — a pasta que tem o `AGENTS.md`.
2. Só é pronto o que um instrumento provou.
3. Antes de criar, procure e cite.
4. A memória mora no disco, não no contexto.
5. Ao dar por pronto, faça a análise de promoção.
6. Trabalhe econômico.
7. Rede com cortesia.
8. Segredo não entra em git nenhum — e ler credencial localmente é livre.
9. Destrutivo é do dono; commit e push seguem o que a casa autorizou.
10. Texto na régua.
11. Não invente passo onde já existe receita.
12. Branch de longa duração e configuração de esteira não se tocam.
13. Publicar exige revisão semântica, não só varredura.
14. Conhecimento nasce na língua de quem vai lê-lo.

## Os nomes

O nome declara a responsabilidade da peça, em português puro. Os nomes
aprovados, que toda peça NOVA usa: executor de roteiros, roteiro, execução,
estágio, evidência, verificação, aprovação manual, catálogo, falso negativo,
repositório, repositório vizinho, painel de controle. Onde o código ainda usar
o nome velho, ele está esperando a renomeação — o par velho→novo, o sentido de
cada um e as exceções estão em `nucleo/vocabulario.json`.
