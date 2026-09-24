# Motores auxiliares — quando a sessão despacha, e para quem

Motor auxiliar é outro agente de linha de comando que esta sessão chama para
fazer um pedaço do trabalho. Ele não é subagente: roda fora deste processo,
gasta a cota dele, e do contexto desta sessão ocupa só o resultado. É por
isso que despachar é economia. E é por isso que o que ele devolve não se
aceita sem conferir.

Esta página é a decisão de despachar. Quem prova que um motor serve é a
bancada, na seção "A bancada dos motores auxiliares" do
[mapa do repositório](mapa-do-repositorio.md).

## A sessão não descobre motor por tentativa

Na abertura, um aviso diz o que ESTA máquina tem: os motores cadastrados, os
papéis de cada um, a forma de cobrança e a disponibilidade. Nada disso é
genérico, então nada disso mora aqui — mora no cadastro local, e o aviso o
lê. Máquina sem motor cadastrado abre calada.

Duas leituras do aviso mudam o que você faz:

- **NÃO PROVADO** é motor que não passou a bancada, ou passou sem data.
  Sonde antes de despachar.
- **saldo só se descobre despachando** é motor que cobra por uso e não grava
  limite em disco. Estourá-lo custa dinheiro, não espera.

## Os três papéis, e o que qualifica um motor para cada um

| Papel | O que o motor precisa provar | O que o chamador faz |
| --- | --- | --- |
| crítico | trava de escrita | confere cada achado na árvore antes de agir |
| pesquisa | responder rápido | trata o achado como pista, não como fato |
| tarefa somente leitura | trava que seja parede do sistema | lê o resultado, nunca o código de saída |

Papel é do par motor mais modelo, não do motor sozinho: motor que deixa
escolher o modelo é uma porta para vários, e a prova vale para o par que foi
sondado.

O papel de crítico rende porque o motor não viu o seu raciocínio — ele acha o
que você não acharia. Medido nesta casa, numa revisão de gancho: zero
sobreposição entre os achados do motor e os da sessão. Mas crítico é lento
por natureza, e revisar um arquivo pode custar minutos; só compensa no que
vale esperar.

## Como se despacha

```bash
python .agents/motores/motores.py --despachar crítico \
  --prompt <arquivo do pedido> --cwd <pasta que o motor lê> --commit <hash>
```

`--commit` junta ao pedido o diff do commit, tirado com `git show` no
repositório de onde se despacha. O motor pode não rodar `git`: o Devin sem
cabeça só lê e busca arquivo, e a cópia por `git archive` não tem `.git`.

O instrumento chama o motor em somente leitura e devolve **todas** as falas
dele, não só a última. A última costuma ser a resposta do motor a um gancho
de parada, e quem guarda só ela perde o parecer, com código de saída zero.
Ele monta os argumentos sozinho e não repassa nenhum de quem chama: bandeira
que abre a escrita não entra. Motor que sai sem fala, que estoura o teto, que
não fecha o turno ou que sai com erro dá despacho NÃO MEDIDO, e o que ele
disse antes disso fica no resultado, marcado como parecer incompleto. Também
é incompleto o parecer de quem recusou uma ferramenta no meio do trabalho: o
Devin sem cabeça deixa `rejected a tool call` no canal de erro e sai zero.
Turno que o motor declara falhado traz o motivo que ele deu, para separar
congestionamento de defeito.

O que a guarda defende é o TEXTO do pedido: motor que recebe o pedido como
argumento por um atalho do interpretador de comandos não se despacha, porque
o atalho executaria o que o texto mandasse. O Devin recebe o pedido por
arquivo (`--prompt-file`), fora da linha de comando. O que ela não defende é quem
chama: `--binario` aponta o executável que você quiser, e apontar um
interpretador é escolha sua, não injeção.

Duas regras de quem despacha, as duas medidas nesta casa:

- **Enquanto um motor lê a árvore, a árvore não se mexe.** Trocar de branch
  ou sincronizar cópia no meio da leitura tira o código de baixo dele.
- **O crítico se despacha depois do commit, citando o hash.** Ele ancora num
  objeto que não muda, em vez de em arquivo vivo. Despachado antes do commit,
  o parecer pode sair sobre código que não era o revisado, sem aviso nenhum.

Antes de um lote de despachos, `--credito <motor>` diz quanto da janela já
foi, sem gastar chamada.

O modelo também é do par. O cadastro local pode declarar, por motor, um
`modelo_por_papel`; o despacho pelo papel o usa, e `--modelo` de quem chama
vence os dois. Sem nenhum, vale o padrão do motor. Motor sem bandeira de
modelo provada recusa `--modelo` em vez de ignorá-lo calado.

## Quando o motor esgota

Papel que mais de um motor serve se resolve pela cobrança: assinatura antes de
pré-pago, porque estourar a primeira custa espera e o segundo custa dinheiro.
Motor que não está instalado na máquina é pulado. A resposta do despacho diz
o motor escolhido, a ordem e por que pulou os outros.

Motor que responde falta de crédito fica ESGOTADO pelo resto da sessão, num
estado que mora na pasta temporária da máquina, fora do cadastro, porque é
volátil. Ele não é tentado de novo, nem pelo nome, e o despacho pelo papel cai
para o próximo motor. Falha que o instrumento não sabe interpretar deixa o
motor suspeito só naquele despacho, e também cai para o próximo. Sem motor
livre, o despacho não chama ninguém e manda avisar o dono: a sessão segue
sozinha. `--listar` mostra o que está esgotado e o arquivo que o libera.

## O que não vai para motor nenhum

- **O que decide.** Publicar, apagar, mesclar na branch de publicação, mexer
  em política: é do dono, e continua sendo quando um motor se oferece.
- **O que pede segredo.** Nenhum despacho leva credencial, nem o caminho de
  onde ela mora.
- **Escrita no repositório.** Nenhum motor tem garantia de escrita que sirva
  para isso. Despache leitura e crítica; a mão que escreve é a sua.
- **A prova.** Motor que afirma ter reproduzido um defeito estando em modo
  somente leitura não reproduziu nada: simulou de cabeça. Prova é comando
  rodado aqui, com a saída vista (regra 2).
- **A pergunta ao dono.** Ela é da sessão.

## O freio

Despachar é barato em contexto e caro em tempo. E a cerca que conta
subagentes não vê motor chamado pelo shell: o teto de agentes da sessão fica
cego a esses disparos. Um motor por papel e por pedido; dois no mesmo pedido
só quando você vai comparar as duas respostas.
