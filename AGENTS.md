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
- Onde escrever cada coisa: `conhecimento/mapa-do-repositorio.md`; a wiki dos
  vizinhos, `conhecimento/projetos/`.
- Rode `python montar.py --sincronizar` depois de editar página, skill, módulo
  ou `nucleo/`.

## Ordens deste repositório

- Publicar é do dono, sempre: publicação não se desfaz, e o teto da sessão é o
  ensaio, que mostra o que subiria sem subir. Commit e push seguem
  `autorizacoes` em `nucleo/configuracao.json`, que é a mesma fonte que o
  gancho lê — omissão não é permissão, e sem declaração ninguém commita.
  Destrutivo é do dono. Este é o único lugar desta regra: outro arquivo que
  disser diferente está errado.
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
8. Segredo não entra em git nenhum — em texto rastreado vai `${VARIAVEL}`,
   nunca o valor; ler credencial localmente é livre.
9. Destrutivo é do dono; commit e push seguem o que o repositório autorizou.
10. Texto na régua.
11. Não invente passo onde já existe receita.
12. Branch de longa duração e configuração de integração contínua não se tocam.
13. Publicar exige revisão semântica, não só varredura.
14. Conhecimento nasce na língua de quem vai lê-lo.
15. Editou a fonte, regenere a cópia e prove — antes de entregar.
16. Ao dar por entregue, prove que nada ficou sem destino — nem commit fora da
    branch, nem entrega sem o passo seguinte.
17. Explique na altura de quem lê, começando por júnior.

## Os nomes

O nome declara a responsabilidade da peça, em português puro. Os nomes
aprovados, que toda peça NOVA usa: executor de roteiros, roteiro, evidência,
verificação, aprovação manual, repositório, repositório vizinho, painel de
controle. Onde o código ainda usar o nome velho, ele está esperando a
renomeação — o par velho→novo, o sentido de cada um e as exceções estão em
`nucleo/vocabulario.json`.
