# Instruções para agentes

Instruções neutras para qualquer agente de IA (Claude, Devin ou outro)
trabalhando neste repositório.

## O que é este repositório

Camada abstrata e compartilhável de skills, fluxos e conhecimento para sessões
de IA. Todo o conteúdo é genérico e reutilizável por qualquer pessoa.

**As pastas de conteúdo são `fluxos/`, `conhecimento/` e `.agents/skills/`** —
nessa ordem: processo passo a passo, técnica e ferramenta, e skill que roda de
verdade. O que mora nelas viaja para todo repositório que montar a camada. O
mapa completo — o que existe, o que a atualização sobrescreve e onde escrever
cada coisa — está em `conhecimento/mapa-do-repositorio.md`. Este arquivo é o
centro neutro; `.claude/` e `.devin/` são adaptadores de ferramenta.

**`modulos/` é a parte opcional, e ela não viaja.** Cada subpasta é um módulo
que só chega onde alguém o pedir por nome. Conteúdo que serve a uma ferramenta
específica — e que seria peso morto para quem não a usa — nasce ali, nunca nas
três pastas acima. Como se escreve um está no `modulos/LEIAME.md`.

**Editou página ou skill? Rode `python montar.py --sincronizar`.** Ele embute
a cópia nova dentro do script e sobe a versão da camada. Sem isso, quem montar
a camada noutro repositório recebe a versão velha. Como instalar e atualizar
está no `README.md`.

## Regras de trabalho

- **Este repositório é público.** Nunca inclua em arquivo, mensagem de commit,
  nome de branch ou issue: dados pessoais, nomes de pessoas ou empresas,
  credenciais, chaves, tokens, caminhos de máquina. Na dúvida se algo é
  genérico o bastante: é pessoal — pergunte antes.
- **Não invente passo onde já existe receita.** Antes de propor como se faz
  algo que a casa já faz, procure o procedimento na documentação dela. Não
  achou? Peça o endereço — não improvise. Esteira improvisada onde já existe
  esteira quebra em produção e ninguém sabe por quê.
- Nunca abra arquivos de credencial (`.env*`, `appsettings*`, `.credenciais/`).
- Não altere nada que já exista sem que isso seja pedido.
- **Aqui a sessão não commita, não empurra e não publica.** Ela deixa os
  arquivos alterados para o dono conferir, commitar e sincronizar; o teto dela
  é o ensaio — o comando que mostra o que subiria sem subir. Destrutivo
  também é dele; o agente prepara e executa o não-destrutivo. **Esta é a única
  casa desta regra** — outro arquivo que disser diferente está errado.
- Só chame de pronto o que um instrumento provou (build, teste, listagem).

## Estilo

- Conteúdo e comunicação em pt-BR.
- Conclusão primeiro, frases curtas, uma ideia por frase, sem jargão.

## As regras desta camada

A lista numerada está em `conhecimento/regras-da-camada.md`. Leia antes de
propor procedimento, de mexer em branch de longa duração e de tocar em
configuração de esteira.
