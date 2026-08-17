# Instruções para agentes

Instruções neutras para qualquer agente de IA (Claude, Devin ou outro)
trabalhando neste repositório.

## O que é este repositório

Camada abstrata e compartilhável de skills, fluxos e conhecimento para
sessões de IA. Todo o conteúdo é genérico e reutilizável.

- **Pastas de conteúdo:** `fluxos/` (processo), `conhecimento/` (técnica e
  ferramenta), `.agents/skills/` (skill que roda). O que mora nelas viaja
  para toda casa que montar a camada.
- **Mapa completo** — o que existe, o que a atualização sobrescreve, onde
  escrever cada coisa: `conhecimento/mapa-do-repositorio.md`. Este arquivo é
  o centro neutro; `.claude/` e `.devin/` são adaptadores.
- **`modulos/` é opcional e não viaja**: só chega por `--modulo <nome>`.
  Como escrever um: `modulos/LEIAME.md`.
- **Editou página ou skill? Rode `python montar.py --sincronizar`.** Sem
  isso, quem montar noutro repositório recebe a versão velha.

## Regras de trabalho

- **Este repositório é público.** Nada pessoal em arquivo, commit, branch ou
  issue: nome de pessoa ou empresa, credencial, caminho de máquina. Na
  dúvida: é pessoal — pergunte antes.
- **Não invente passo onde já existe receita.** Procure o procedimento na
  documentação da casa; não achou, peça o endereço — não improvise.
- **Ler credencial localmente é livre. Segredo não entra em git nenhum** —
  público ou privado: em texto rastreado, sempre `${VARIAVEL}`, nunca o
  valor. Usou credencial para configurar algo? Avise o dono para tirá-la de
  vista — o backup é dele.
- Não altere o que existe sem que isso seja pedido.
- **Aqui a sessão não commita, não empurra e não publica.** Deixa os
  arquivos para o dono conferir; o teto é o ensaio — o comando que mostra o
  que subiria sem subir. Destrutivo também é dele. **Esta é a única casa
  desta regra** — outro arquivo que disser diferente está errado.
- Só chame de pronto o que um instrumento provou (build, teste, listagem).

## Estilo

- Conteúdo e comunicação em pt-BR.
- Conclusão primeiro, frases curtas, uma ideia por frase, sem jargão.

## As regras desta camada

A lista numerada está em `conhecimento/regras-da-camada.md`. Leia antes de
propor procedimento, de mexer em branch de longa duração e de tocar em
configuração de esteira.
