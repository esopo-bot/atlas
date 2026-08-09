# Skills: criar, refinar e testar

Escrever a skill é a parte curta. O que separa skill viva de skill morta é a
medição: validar o formato, medir se dispara, provar que o agente a carregou.
Cada etapa tem comando próprio — está tudo aqui.

## A peneira: cinco perguntas antes de escrever

Skill que já existe é trabalho jogado fora. Corra a peneira, e pare no
primeiro "sim":

1. **Já vem de fábrica?** A lista dos comandos que existem sem instalar nada
   está no [canivete](skills-da-camada.md).
2. **Tem plugin oficial?** São poucos e a lista é fechada. O critério para ler
   o catálogo está em [plugins](plugins-oficiais-do-claude-code.md).
3. **Resolve com uma frase no `AGENTS.md`?** Instrução curta vence skill nova:
   ela vale em toda sessão, e skill depende de disparar.
4. **Sobrou o quê?** Só o que ninguém poderia ter escrito por você: a regra do
   seu negócio, o seu dado, o jeito da sua casa.
5. **Passou nos quatro?** Escreva — com o plugin `skill-creator`, que existe
   justamente para isso.

O corte do passo 4 é o que importa: **o oficial cobre técnica; você só escreve
domínio.** Uma skill chamada "corrigir bug" morre na peneira. Uma que conhece a
sua planilha, não.

## Os comandos, na ordem do trabalho

| Você quer                                                     | Comando                           | Vem de                   |
| ------------------------------------------------------------- | --------------------------------- | ------------------------ |
| Criar skill nova, melhorar ou refinar uma que existe          | `/skill-creator`                  | plugin `skill-creator`   |
| Medir se dispara: avaliações, benchmark, otimizar a descrição | `/skill-creator` (peça a medição) | plugin `skill-creator`   |
| Validar o formato contra o padrão Agent Skills                | `agentskills validate <pasta>`    | `pip install skills-ref` |

O `skill-creator` é o único que precisa ser ligado antes — é plugin, e as duas
chaves que ligam um estão no [canivete](skills-da-camada.md). O validador tem
pegadinha de nome: instala-se `skills-ref`, chama-se `agentskills`.

## Medir o disparo, sem se enganar

Descrição boa não garante disparo. Skill de método dispara pela palavra que
você escreve no pedido; skill de padrão de código não dispara nunca — medido:
zero em 160 tentativas. Por isso o teste tem três regras:

1. **Meça com variação.** O otimizador do `skill-creator` reescreve o mesmo
   pedido de vários jeitos e conta os disparos. Um teste só não é medida.
2. **Desligue a leitura no teste por linha de comando:**

   ```bash
   claude -p "<a pergunta>" --disallowed-tools Read,Glob,Grep,Bash,WebFetch,WebSearch
   ```

   Com leitura ligada, o agente abre o arquivo e responde certo sem ter
   carregado skill nenhuma — falso positivo que engana qualquer um.
3. **Faça o controle negativo.** Um pedido que NÃO deve disparar a skill.
   Teste que nunca falha não prova nada.

E quando não dispara e precisa disparar: cite pelo nome ou prenda com gancho —
os caminhos estão no
[canivete](skills-da-camada.md#como-uma-skill-entra-na-conversa).
