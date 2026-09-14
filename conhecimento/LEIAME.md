# conhecimento

Saber genérico: técnicas, ferramentas e processos passo a passo. O que existe
hoje está nos links desta página — e só.

## O mínimo para começar

Acabou de instalar a camada? São **quatro passos**, e nenhum deles é ler tudo.

1. **Leia o `AGENTS.md` da raiz.** É o único arquivo que toda sessão carrega
   sozinha. Ele já diz o essencial das regras; a lista numerada inteira mora
   em [as regras da camada](regras-da-camada.md), e só se lê quando for
   propor procedimento ou mexer em branch de longa duração.
2. **Preencha o `nucleo/configuracao.json`.** Enquanto houver `${...}` sem
   valor, a camada não sabe onde sua issue nasce nem o que você autorizou —
   e, sem autorização escrita, ela não commita e não empurra. É o único
   arquivo que você precisa editar para a camada funcionar.
3. **Prove que ela está de pé**, com o comando que viaja junto:

   ```bash
   python .agents/camada/camada.py medir provar
   ```

   `medir` diz quanto a camada cobra de contexto em toda sessão; `provar`
   roda o teste de cada gancho e instrumento.
4. **Veja o que você ganhou em skills**: elas se listam sozinhas na
   sessão, pela `description` de cada uma. Para escrever a sua e fazê-la
   disparar, [a skill que dispara](skill-que-dispara.md) traz a receita
   medida.

Sessão nova abre pelo briefing da camada, `.agents/prompts/bootstart.md`:
o comando de barra `/bootstart` o carrega, e o `AGENTS.md` aponta para ele.

Pronto. **O resto desta página é sob demanda**: são páginas que se abrem
quando o assunto aparece, não leitura de largada. E a máquina precisa de
coisas que o instalador não traz — isso está em
[o estado que não viaja](estado-que-nao-viaja.md).

## As páginas, uma a uma

Outras páginas foram escritas e saíram para serem refeitas uma a uma;
enquanto não voltarem, elas não são citadas aqui, porque sumário que nomeia
página inexistente manda procurar o que ninguém escreveu.

- [investigação de incidente](investigacao-de-incidente.md) — a ordem dos nove
  passos, e as armadilhas de medição que fazem conclusão errada passar por
  prova.
- [o estado que não viaja](estado-que-nao-viaja.md) — o que a máquina precisa
  ter e o instalador não traz.
- [um navegador por projeto](navegador-por-projeto.md) — como a sessão ganha
  navegação assistida.
- [a rotina que abre issue só para erro novo](rotina-de-erros-novos.md).
- [a guarda mecânica das regras](guarda-mecanica-das-regras.md) — o que cobra
  cada regra na prática: gancho, rotina, ou nada.
- [o auditor](auditor.md) — por que quem verifica a execução lê a evidência
  gravada, e não o comportamento da sessão.
- [a verificação pós-atualização](verificacao-pos-atualizacao.md) — a
  camada foi atualizada aqui: prove a instalação e cace o resto da versão
  anterior.
- [a prova de leitura do agente](prova-de-leitura-do-agente.md) — o agente
  mostra, com saída colada, que enxerga as instruções e as skills.
- [organizar conhecimento e projetos](organizar-conhecimento-e-projetos.md)
  — as duas pastas do workspace na forma que as regras pedem, sem perder
  uma linha do dono.
- [medir o prompt de abertura](medir-o-prompt-de-abertura.md) — a bancada
  que troca opinião por nota: árvores isoladas, problemas fixos e a régua
  que separa o que instrumento mede do que juiz julga.
- [a auditoria externa da camada](auditoria-externa-da-camada.md) — a
  sessão de fora que existe para derrubar: medir antes de afirmar.

Duas receitas que a camada manda usar e por muito tempo não ensinou: montar
[um navegador por projeto](navegador-por-projeto.md), para a sessão ganhar
navegação assistida, e
[a rotina que abre issue só para erro novo](rotina-de-erros-novos.md).

O que segura cada regra na prática — gancho, rotina ou nada:
[a guarda mecânica das regras](guarda-mecanica-das-regras.md).
