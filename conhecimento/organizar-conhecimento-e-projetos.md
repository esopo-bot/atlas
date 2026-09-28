# Organize `conhecimento/` e `projetos/` pelas regras da camada

Receita para qualquer agente aberto na raiz de um repositório que instalou
a camada. As duas pastas passam a ter a forma que as regras pedem, sem
perder uma linha do que o dono escreveu.

## A cerca que vale acima de tudo

- Liste antes de mover; mover é `git mv` (o que não está no git vai com
  `mv` e entra no relato como "fora do git").
- Destino ocupado vira pergunta. Apagar é do dono: você propõe a lista com
  a razão de cada item.
- Anotação do dono não se toca: entra no relato como "do dono".
- Nada de nome de pessoa, empresa, máquina ou credencial em arquivo que a
  camada rastreie.

## Três origens de sujeira

1. **Resto da versão anterior da camada:** é da
   [verificação pós-atualização](verificacao-pos-atualizacao.md), com
   `python .agents/limpeza/limpeza.py rodar --workspace .`; rode-a primeiro.
2. **Resto de sessão** (saída de comando, `.err`, prompt colado, script de
   uma vez): vai para `tmp/`, fora do git; o que estava rastreado sai do git
   na mesma mudança.
3. **Material do dono fora de forma:** as regras abaixo.

## As regras que dão a forma

`conhecimento/`: um nível de subpasta, cada uma com `LEIAME.md` de uma
linha; nome minúsculo sem acento nem espaço (prefixo numérico vira pergunta
ao dono); um lugar por assunto, e sobrevive a página com prova; a língua de
quem lê (regra 14: dado estruturado para a sessão, prosa densa para a
pessoa); a wiki dos vizinhos em `conhecimento/projetos/`, um perfil por
repositório pela skill `perfil-de-repositorio`; trabalho em andamento mora
na issue, não em arquivo.

`projetos/`: uma pasta por repositório clonado com o nome dele, e nada mais;
`ls projetos/` é a lista do que existe (repositório sem perfil ganha um,
perfil sem repositório entra na lista de saída); repositório declarado
somente leitura não recebe escrita nenhuma.

Raiz: rascunho e gerado em `tmp/`; script de apoio deste repositório numa
pasta própria com `LEIAME.md`; credencial fica onde está e fora do git;
pasta nasce quando o material cansa a leitura, nunca por antecipação.

## O que você faz, nesta ordem

1. Inventário sem mover: `git ls-files conhecimento projetos` e `ls -la`
   das duas pastas e da raiz; cada item com a origem (1, 2 ou 3) e um
   destino: fica, move para X, funde com Y, sai (do dono), do dono, pergunta.
2. Plano ao dono; sem sim não se executa.
3. Só o aprovado, com `git mv`, `LEIAME.md` por subpasta nova e os links
   corrigidos (`grep -rn` pelo caminho antigo, antes e depois).
4. Prova: `git status --short` colado, nenhum arquivo apagado, a rotina de
   referências órfãs sem acusação nova.
5. Relato: o que moveu, fundiu, ficou por decisão, é do dono, e a lista de
   saída com a razão de cada item.

Não apaga, não edita cópia da camada, não toca em somente leitura, não
commita sem `autorizacoes` em `nucleo/configuracao.json`.
