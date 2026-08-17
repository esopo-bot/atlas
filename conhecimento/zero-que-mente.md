# Zero que mente

Resultado vazio parece resposta e não é: "não encontrei" e "não existe" são
coisas diferentes, e o instrumento raramente avisa qual das duas te entregou.
Vale para busca, consulta de registro, chamada de interface e verificação de
permissão — na tela, "sem acesso" e "não existe" também se parecem. As causas
abaixo explicam quase todos os casos — cada uma já custou horas.

## O bolso: causa → hábito

| # | Causa | O hábito que resolve |
| --- | --- | --- |
| 1 | Filtro ligado sem você saber | Ancore a busca dentro do repositório; teste-a com termo que você sabe que existe. |
| 2 | Vocabulário errado | Olhe uma linha real e copie o vocabulário dela; fixe o ambiente na consulta. |
| 3 | O terminal reescreveu o argumento | Resposta sem sentido? Imprima o que o programa recebeu (`MSYS_NO_PATHCONV=1` no Git Bash). |
| 4 | O filtro espera um fim que não vem | Processo longo escreve em arquivo; para esperar, use sonda que termina. |
| 5 | A interface não está no arquivo | Presença em interface se prova com clique, não com busca no HTML. |
| 6 | O ambiente não tem o dado | Antes de navegar, pergunte "o dado existe aqui?" com consulta direta. |
| 7 | A medição saiu de outro lugar | Ancore no caminho absoluto; imprima o `pwd` na mesma chamada que mede. |
| 8 | O seu próprio filtro | Exclua por arquivo, não por conteúdo; rode uma vez sem o filtro. |
| 9 | Quem perguntou não foi você | Pergunte quem está logado com a chamada que **usa** o token; quem trocou de conta, devolve. |

As seções abaixo são a prova de cada linha — leitura de consulta, para
quando a causa aparecer.

## Causa 1: um filtro que você não sabia que estava ligado

Ferramenta de busca sobre `ripgrep` — e é sobre ele que quase toda busca de
agente é construída — **respeita o `.gitignore` do repositório onde você
está**. Num workspace cujos repositórios de código moram numa pasta ignorada,
buscar da raiz devolve zero para termo que existe aos montes, e não diz que
ignorou nada.

Medido num workspace com `projetos/` ignorado, procurando um termo presente
em dezenas de arquivos:

| Onde se busca                                  | Resultado |
| ---------------------------------------------- | --------- |
| da raiz                                        | **zero**  |
| dentro do repositório                          | acha      |
| da raiz, com a trava desligada (`--no-ignore`) | acha      |

Três hábitos que resolvem:

- **Ancore a busca dentro do repositório**, não na raiz do workspace.
- **Desconfie de zero** para termo que deveria existir — teste a própria
  busca com algo que você tem certeza que está lá. Se esse também der zero, o
  problema é a busca, não o código.
- **`git log -S <termo>` dentro do repositório** é a contraprova barata: ele
  procura na história e não obedece ao ignore da pasta de cima.

Cuidado com a leitura fácil: `.gitignore` esconde do git e **também da
busca**; o que ele não esconde é a leitura direta de um arquivo cujo caminho
você já sabe. Por isso o agente abre o arquivo normalmente e mesmo assim
"não acha" nada — e as duas coisas são verdade ao mesmo tempo.

## Causa 2: você está procurando no vocabulário errado

O nome que o código escreve não é sempre o nome que fica gravado. Um registro
emitido como "crítico" pode ser gravado como "fatal" pela biblioteca de
registro; nível, categoria e nome de campo mudam de vocabulário no caminho
entre a aplicação e o coletor.

O hábito que resolve é anterior a qualquer filtro: **olhe uma linha real do
registro, inteira, e copie o vocabulário dela**. Uma linha verdadeira ensina
o formato; a documentação ensina o que deveria ser.

A mesma armadilha, com outra roupa: **ambiente com nome parecido**. Região,
conta, projeto ou grupo de registros com nomes quase idênticos entre produção
e homologação entregam zero perfeitamente honesto — do lugar errado. Fixe o
ambiente explicitamente na consulta, sempre, mesmo quando "é o padrão".

## Causa 3: o terminal reescreveu o que você digitou

No Windows, o Bash que acompanha o Git converte argumento que começa com
barra em caminho do sistema — sem avisar. O programa recebe outra coisa e
responde honestamente sobre a coisa errada: "não existe", "sem permissão",
vazio. Medido:

```bash
python -c "import sys; print(sys.argv[1])" /algum/caminho
# recebeu: C:/Program Files/Git/algum/caminho

MSYS_NO_PATHCONV=1 python -c "import sys; print(sys.argv[1])" /algum/caminho
# recebeu: /algum/caminho
```

Pega qualquer comando cujo argumento comece com barra: nome de recurso na
nuvem, caminho dentro de contêiner, tópico, fila. O conserto é desligar a
conversão (`MSYS_NO_PATHCONV=1`) ou usar um terminal que não converte.

O hábito que resolve o gênero, não só este caso: **quando a resposta não
fizer sentido, imprima o que o programa recebeu** antes de acreditar no que
ele respondeu.

## Causa 4: o filtro espera um fim que nunca chega

`servidor 2>&1 | tail -20`, com o servidor rodando ao fundo, devolve **nada,
para sempre** — e o nada se lê como "não subiu". Medido: seis segundos de
saída contínua, zero linhas na tela. O `tail` só escreve quando a entrada
fecha, e processo de longa duração não fecha. Assim se mata um serviço que
estava apenas compilando.

Vale para todo filtro que precisa do fim para responder: `tail` sem `-f`,
`sort`, `wc`, qualquer contagem. **Não** vale para `head -n N` nem
`grep -m N` — medido: eles imprimem e saem assim que a conta fecha; só ficam
presos enquanto o número não chega.

Dois hábitos:

- **Processo que não termina escreve saída crua num arquivo**, e você lê o
  arquivo. Nada de filtro no meio.
- **Para esperar, use uma sonda que termina**, não um filtro que espera:

  ```bash
  until curl -s -o /dev/null <endereço>; do sleep 2; done
  ```

  A sonda pergunta pelo serviço; o filtro só espera o processo morrer.

## Causa 5: a interface não está no arquivo que você buscou

Procurar um item de menu no HTML de um site estático dá falso negativo: o que
está dentro de componente colapsado — categoria, acordeão, aba — não nasce no
HTML, nasce no navegador quando alguém expande.

Medido num site de documentação: o **rótulo da categoria** aparece no HTML;
os **itens dentro dela**, não; e a rota de cada item existe e responde. Ou
seja, a página está publicada e a busca diz que não.

Busca em texto prova que a **rota** não foi gerada; nunca prova que o item
não está no menu. Presença em interface se prova com clique: sirva o
resultado e navegue **com o papel de quem vai usar** — o portão de acesso
é parte do caminho.

## Causa 6: o ambiente não tem o dado que a tela mostraria

Tela ou consulta zerada em ambiente sem massa não prova nada: o vazio pode
ser o defeito — ou pode ser só o ambiente. Numa mesma semana de trabalho,
três zeros acusaram a aplicação; a causa era dado que nunca existiu ali.

Antes de prometer prova por navegação, pergunte **"o dado existe aqui?"** —
custa uma consulta direta à fonte, e decide se a navegação vai provar
alguma coisa.

E quando o conserto é semear massa: remendo feito por fora morre na próxima
recriação do ambiente, e o zero mentiroso volta. O conserto durável mora no
que recria o ambiente.

A mesma armadilha com o tempo no lugar do dado: **conferência que depende de
evento não fecha em janela sem evento**. Registro consultado numa hora sem
movimento devolve zero honesto — e o zero se lê como "a correção não
funcionou", ou pior, como "funcionou". Antes de prometer a conferência, ache
o gatilho: provoque o evento você mesmo, ou ancore num que acontece sozinho e
tem hora marcada.

## Causa 7: a medição saiu de outro lugar

O diretório de trabalho de algumas ferramentas **persiste entre chamadas**.
Um `cd` numa chamada muda o chão de todas as seguintes, e nada avisa: a
medição seguinte responde honestamente — sobre outra pasta. Medido, três
chamadas seguidas na mesma sessão:

| Chamada | Comando | Onde rodou | Contagem |
| --- | --- | --- | --- |
| 1 | `cd <subpasta> && pwd` | a subpasta | — |
| 2 | `pwd; ls *.md \| wc -l` | ainda a subpasta | **11** |
| 3 | `cd <raiz> && pwd; ls *.md \| wc -l` | a raiz | **7** |

A perigosa é a chamada 2: número plausível, do lugar errado. Zero levantaria
suspeita; onze, não — e é assim que um relatório ganha um número que ninguém
consegue reproduzir.

Dois hábitos: **ancore no caminho absoluto** em vez de depender de onde a
sessão parou; e, quando o número importar, **imprima onde você está na mesma
chamada que mede** (`pwd; <a medição>`).

## Causa 8: o filtro que você mesmo escreveu esconde a resposta

Excluir um termo para tirar ruído esconde também **as linhas que citam o
termo**: `grep -rn "x" | grep -v "<caminho>"` some com toda linha cujo
conteúdo menciona o caminho — inclusive a citação viva que a busca existia
para achar. Medido duas vezes no mesmo dia, por leitores diferentes: a
única referência a uma pasta quase passou batida porque a linha citante
continha a própria string filtrada; e uma contagem de referências veio
menor porque o filtro do endereço novo comeu as linhas que apontavam para
ele.

Dois hábitos:

- **Exclua por arquivo, não por conteúdo**: ancore o filtro no campo do
  caminho (`grep -v "^caminho/"`) ou use o glob da ferramenta
  (`rg -g '!pasta/**'`) — o que se quer excluir é onde a linha mora, não o
  que ela diz.
- **Rode uma vez sem o filtro** quando o resultado decidir algo: a
  diferença entre as duas contagens é exatamente o que o filtro comeu.

E o primo da armadilha, no sentido contrário: **frase procurada em prosa
formatada dá zero falso**. Crase de código, quebra de linha e recuo entram
no meio do texto — a frase existe e o `grep` literal não a vê. Medido:
"develop saiu do caminho" deu zero num arquivo que dizia exatamente isso,
com o nome entre crases e a continuação na linha seguinte. Para conferir
presença de fato em página, normalize antes (`tr '\n' ' ' | tr -s ' '`) ou
procure um pedaço curto, sem formatação.

## Causa 9: quem perguntou não foi você

Ferramenta que guarda credencial responde pela identidade **ativa naquele
momento**, não pela que você tem em mente. Quem troca de conta para uma tarefa
e não volta passa a perguntar com a credencial errada — e a resposta é honesta
para aquela identidade: `404`, "não existe", "repositório não encontrado".

Medido no mesmo dia, com a conta de publicação ativa por engano:

| Comando                          | Resposta               | Verdade |
| -------------------------------- | ---------------------- | ------- |
| consultar o repositório pela API | `404`                  | existe  |
| trazer o que está no remoto      | `Repository not found` | existe  |
| os mesmos, com a conta certa     | funcionam              | —       |

A última linha é a contraprova que a regra 2 cobra, em
[as regras da camada](regras-da-camada.md): o instrumento sabe achar, só não
com aquela identidade.

O `404` é o pior dos vazios porque é **de propósito**. Responder "sem
permissão" confirmaria a existência do recurso a quem não deveria saber dela,
então a interface responde igual para "não existe" e para "você não enxerga" —
e a distinção de que você precisa é justamente a que ela se recusa a dar.

Vale para toda ferramenta com sessão ativa: cliente de repositório, interface
de nuvem, contexto de cluster, gerenciador de pacote privado.

Três hábitos:

- **Antes de acreditar no vazio, pergunte quem está logado.** É uma chamada, e
  ela desfaz o diagnóstico inteiro antes de ele começar.
- **Pergunte ao token, não ao rótulo.** O comando que lê a configuração
  guardada devolve o nome anotado ali, e o token em uso pode ser de outra
  conta — medido: o rótulo dizia uma conta e a chamada autenticada devolvia
  outra. Só a chamada que **usa** a credencial prova qual credencial está em
  uso.
- **Quem troca de identidade, devolve.** A troca serve a uma tarefa; a volta é
  parte dela. Sem isso o erro aparece horas depois, noutro comando, e o sintoma
  não aponta para a causa.

E o portão que confere identidade antes de uma operação séria tem três
exigências próprias, porque ele também é um instrumento que pode mentir. As
três saíram do mesmo incidente de provedor, medido:

- **Prova única é ponto único de falha.** A rota que devolve o usuário deu
  `503` enquanto o resto da interface ia bem, e o trabalho parou com tudo
  verde à volta. Uma segunda rota que pergunte ao **mesmo token** traz a mesma
  resposta e sobrevive à queda de um lado.
- **Uma tentativa só desperdiça a reserva.** Oito amostras por rota: a rota
  morta deu 0/8, e a reserva, 5/8 — viva, porém intermitente. O portão tentava
  cada prova uma vez, então parava em cerca de um terço das execuções dizendo
  "não consegui perguntar quem está logado" — que se lê como credencial
  quebrada, e não é. Rota degradada pede repetição, não substituta.
- **Qual das provas respondeu aparece na tela.** Prova trocada em silêncio não
  é prova.

A armadilha de leitura, no meio disso: amostra única mentiu duas vezes. O
mesmo comando falhou por um cliente e funcionou por outro no mesmo minuto, e a
conclusão fácil — "o cliente está com defeito" — morreu na repetição. **Quando
o resultado for intermitente, conte; não conclua da primeira.**

## A regra em uma linha

Antes de escrever "não existe" num relatório, prove que o seu instrumento
sabe achar: a mesma consulta, na mesma janela, tem de trazer alguma coisa.
Zero não provado é hipótese — e hipótese que anda como fato é o começo da
conclusão errada.
