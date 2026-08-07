# Skills: criar, refinar e testar

Escrever a skill é a parte curta. O que separa skill viva de skill morta é a
medição: validar o formato, medir se dispara, provar que o agente a carregou.
Cada etapa tem comando próprio — está tudo aqui.

## Antes de escrever

A peneira de cinco passos está nos [templates](../fluxos/templates.md): se o
oficial já faz, não escreva. Passou na peneira, siga.

## Os comandos, na ordem do trabalho

| Você quer                                                     | Comando                           | Vem de                   |
| ------------------------------------------------------------- | --------------------------------- | ------------------------ |
| Criar skill nova, melhorar ou refinar uma que existe          | `/skill-creator`                  | plugin `skill-creator`   |
| Medir se dispara: avaliações, benchmark, otimizar a descrição | `/skill-creator` (peça a medição) | plugin `skill-creator`   |
| Validar o formato contra o padrão Agent Skills                | `agentskills validate <pasta>`    | `pip install skills-ref` |

O `skill-creator` é o único que precisa ser ligado antes — é plugin, e o jeito
de ligar está nos [templates](../fluxos/templates.md), na seção "Ligar um
plugin". O validador tem pegadinha de nome: instala-se `skills-ref`, chama-se
`agentskills`.

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

## Quando a skill não dispara e precisa disparar

Dois caminhos, do mais simples ao mais firme: citar a skill pelo nome dentro do
prompt, ou prender com um gancho que a injeta sozinho — o contrato está em
[ganchos](ganchos.md).
