# A camada foi atualizada — verifique e limpe antes de trabalhar

Prompt para o repositório que INSTALA o atlas. Cole numa sessão aberta na
raiz do repositório logo depois de uma atualização da camada (o
`montar.py` novo já rodou aqui). O objetivo: provar que a instalação está
íntegra e que nada da versão anterior ficou para trás.

## O que aconteceu

A camada instalada neste repositório foi atualizada e
`python3 montar.py --sincronizar` já foi executado. Atualização regrava
as cópias — nunca se edita cópia à mão — mas ela não remove sozinha o que
a versão nova deixou de escrever: skill renomeada, gancho aposentado,
página movida. Isso é a sujeira que esta sessão caça.

## Faça, nesta ordem, colando a saída de cada passo

1. **A carga bate com o disco:** `python3 montar.py --verificar` — tem de
   sair zero. Divergência aqui é cópia editada à mão ou atualização pela
   metade: pare e mostre ao dono antes de qualquer outra coisa.
2. **Os instrumentos respondem:** rode o `--testar` de cada instrumento
   instalado em `.agents/` (todo instrumento da camada tem o seu). Um
   vermelho aqui é defeito de instalação, não do seu repositório.
3. **A sujeira, pelo instrumento:**
   `python3 .agents/limpeza/limpeza.py rodar --workspace .` — sem
   `--aplicar`, ele só LISTA o que removeria. Leia a lista e separe:
   o que é resto da camada antiga (candidato a sair) e o que é arquivo
   seu que só parece órfão (não sai). Aplique com `--aplicar` somente o
   que você separou como resto — e o que tiver dúvida, pergunte ao dono
   antes: remover é destrutivo, e destrutivo é do dono.
4. **Referência quebrada:** procure no seu repositório citações a
   caminhos da camada que a versão nova moveu ou renomeou (grep pelos
   nomes que a lista do passo 3 apontou). Cite o que achou; corrija só o
   que for apontador para a camada, nunca conteúdo seu.
5. **Relate:** o que foi verificado (com as saídas), o que saiu, o que
   ficou por decisão e o que ficou por dúvida. Sem lista de removidos não
   houve limpeza — houve fé.

## O par de settings: o que é da camada e o que é seu

O Claude Code lê DOIS arquivos em `.claude/`, e a atualização trata cada
um de um jeito:

- **`settings.json`** é DA CAMADA: rastreado, viaja, e a atualização o
  regrava. Nunca edite — edição aqui morre na próxima atualização, e
  valor pessoal aqui vaza para o git.
- **`settings.local.json`** é SEU: fora do git, sobrevive a toda
  atualização. É o lugar certo de tudo que é desta máquina e desta
  pessoa: permissões liberadas (`permissions.allow`), servidores MCP
  habilitados (`enabledMcpjsonServers`), ganchos pessoais (`hooks`),
  variáveis de ambiente. Os dois se somam na leitura; o local acrescenta
  sem tocar no da camada.

Depois de atualizar, faça a triagem dos valores:

1. Abra os dois e compare. Valor PESSOAL que esteja no `settings.json`
   (permissão da sua máquina, gancho seu, caminho local) está no lugar
   errado: leve-o para o `settings.local.json` — a atualização não o
   levaria, e a próxima o apagaria.
2. Procure valor perdido: permissão que você tinha e sumiu, servidor MCP
   que parou de aparecer, gancho pessoal que deixou de disparar — tudo
   isso se recoloca no `settings.local.json`, nunca no da camada.
3. Segredo não entra em NENHUM dos dois por valor: em arquivo rastreado
   vai `${VARIAVEL}`; no local, prefira apontar para onde a credencial
   mora a colar o valor.
4. Prove que o resultado é legível:
   `python3 -m json.tool .claude/settings.local.json > /dev/null && echo legivel`
   — e lembre que gancho novo só carrega em sessão nova.

## O que esta sessão NÃO faz

Não edita cópia da camada (regra: fonte, nunca cópia — e a fonte mora no
repositório da camada, não aqui). Não apaga nada fora da lista do
instrumento sem perguntar. Não commita sem o repositório autorizar em
`nucleo/configuracao.json`, campo `autorizacoes` — omissão não é
permissão.
