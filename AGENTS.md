<!-- GERADO de nucleo/regras.json pelo `montar.py --sincronizar`. Editar aqui se perde. -->

# Instruções para agentes

Para qualquer agente de IA neste repositório.

## Antes de qualquer pedido

- O checklist de partida, `.agents/prompts/partida.md`, roda sob demanda, em
  qualquer agente: quando o dono pedir, ou quando o `--abertura` acusar peça em
  falta. Ele custa minutos e muitos tokens por sessão, então não é o primeiro
  ato de toda sessão. No Claude Code ele é `/partida`.
- Leia `.agents/prompts/bootstart.md` INTEIRO antes de escolher skill, abrir
  arquivo ou responder: é o briefing da camada para qualquer agente — o que a
  sessão vai encontrar, o que os ganchos recusam, e a tabela que diz o que
  atende cada tipo de pedido. Pedido que já nomeia uma skill, um vizinho ou uma
  issue não dispensa a leitura.
- Depois rode `python .agents/camada/camada.py --abertura`, com `--raiz` e o
  caminho por extenso, e relate na primeira resposta o que ele acusou em falta
  — instrução, servidor de contexto, endereço do quadro ou índice. Sessão que
  abre sem eles trabalha com menos do que pensa ter.

## O repositório

- Camada genérica de skills e conhecimento para sessões de IA; `montar.py` a
  instala em outros repositórios.
- Viaja para quem instala: regras (`nucleo/`,
  `conhecimento/regras-da-camada.md`), skills, instrumentos, ganchos e módulos
  ligados; as outras páginas de `conhecimento/` ficam aqui.
- Fonte que instrumento lê: `nucleo/`.
- Onde escrever cada coisa: `conhecimento/mapa-do-repositorio.md`. Os vizinhos
  clonados moram em `projetos/<nome>` — `ls projetos/` lista o que existe; a
  wiki deles, `conhecimento/projetos/`, é perfil, não prova.
- Rode `python montar.py --sincronizar` depois de editar página, skill, módulo
  ou `nucleo/`.
- Onde as issues nascem: `nucleo/configuracao.json`, campo
  `repositorio_das_issues`, que aponta o arquivo local com o endereço. Toda
  issue nasce lá, mesmo quando o código mora em outro repositório — procurar no
  repositório de código devolve zero, e zero parece resposta.

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
18. Número não mora em prosa.
19. Não pare sem necessidade.
20. Decisão do dono não se reabre sem citar a data e o motivo.

## Os nomes

O nome de uma peça declara a responsabilidade dela, em português comum. Use o
nome que este repositório já usa para a coisa; não invente jargão nem sinônimo
novo para o que já tem nome. Quem lê o nome tem de saber o que a peça faz sem
abrir o arquivo.
