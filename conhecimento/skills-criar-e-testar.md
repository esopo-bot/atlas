# Skills: criar, refinar e testar

## A peneira: pare no primeiro "sim"

1. **Já vem de fábrica?** [Canivete](skills-da-camada.md).
2. **Tem plugin oficial?** [Plugins](skills-da-camada.md#os-plugins-que-se-pagam).
3. **Resolve com uma frase no `AGENTS.md`?** Instrução curta vence skill:
   vale em toda sessão, sem depender de disparo.
4. **Sobrou o quê?** Só o que ninguém escreveria por você: a regra do seu
   negócio, o seu dado, o jeito da sua casa.
5. **Passou nos quatro?** Escreva — com o plugin `skill-creator`.

## Os comandos, na ordem do trabalho

| Você quer                                | Comando                           | Vem de                   |
| ---------------------------------------- | --------------------------------- | ------------------------ |
| Criar, melhorar ou refinar uma skill     | `/skill-creator`                  | plugin `skill-creator`   |
| Medir disparo, benchmark, otimizar descrição | `/skill-creator` (peça a medição) | plugin `skill-creator`   |
| Validar o formato Agent Skills           | `skills-ref validate <pasta>`     | `pip install skills-ref` |

O upstream renomeou a CLI do validador: a spec manda `skills-ref validate`;
o release atual do PyPI ainda instala o executável antigo `agentskills` —
se um nome falhar, use o outro.

## Medir o disparo, sem se enganar

1. **Meça com variação** — o otimizador do `skill-creator` reescreve o
   pedido de vários jeitos e conta os disparos. Um teste só não é medida.
2. **Desligue a leitura no teste**:

   ```bash
   claude -p "<a pergunta>" --disallowed-tools Read,Glob,Grep,Bash,WebFetch,WebSearch
   ```

   Com leitura ligada, o agente abre o arquivo e responde certo sem skill
   nenhuma — falso positivo.
3. **Faça o controle negativo** — um pedido que NÃO deve disparar. Teste
   que nunca falha não prova nada.

Skill de padrão de código não dispara por descrição. Quando precisa
disparar: cite pelo nome ou prenda com gancho —
[canivete](skills-da-camada.md#as-skills-da-camada).
