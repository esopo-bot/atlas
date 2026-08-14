# Zero que mente

Resultado vazio parece resposta e não é: "não encontrei" e "não existe" são
coisas diferentes, e o instrumento raramente avisa qual das duas te entregou.
Vale para busca, consulta de registro, chamada de interface e verificação de
permissão — na tela, "sem acesso" e "não existe" também se parecem. As causas
abaixo explicam quase todos os casos — cada uma já custou horas.

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

## A regra em uma linha

Antes de escrever "não existe" num relatório, prove que o seu instrumento
sabe achar: a mesma consulta, na mesma janela, tem de trazer alguma coisa.
Zero não provado é hipótese — e hipótese que anda como fato é o começo da
conclusão errada.
