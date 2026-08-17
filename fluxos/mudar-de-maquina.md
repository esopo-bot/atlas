# Mudar de máquina

O repositório viaja pelo git; o resto, não. Este fluxo existe porque a
perda é silenciosa: nada avisa na mudança — cada peça para dias depois, uma
por vez, com cara de defeito novo. O mapa do que sobrevive e do que morre
está em [o estado que não viaja](../conhecimento/estado-que-nao-viaja.md).

## Antes de mudar

1. **Feche o trabalho.** Commit do que é commitável, e o ponto de retomada
   escrito na nota de continuação da casa.
2. **Copie a pasta do workspace inteira**, não só o clone. Configuração
   local, notas e credenciais moram fora do git e só viajam com a pasta —
   é o território 2.
3. **Saiba o que vai morrer.** O estado da ferramenta (histórico,
   confiança, aprovações — território 3) e o perfil do sistema (variáveis,
   perfis de CLI, agendamentos — território 4) ficam para trás. Não tente
   levá-los: anote o que refazer.

## Depois de mudar

1. **Abra uma sessão na raiz.** O gancho `conferir-ambiente.py` acusa o que
   falta, com nome e endereço — se calar, os nomes estão no lugar.
2. **Siga a página de máquina nova da casa**, item por item, provando cada
   um pelo instrumento da própria linha.
3. **Refaça o que é do dono:** credencial, confiança de diretório,
   aprovação dos servidores MCP declarados no repositório.
4. **Só dê a máquina por pronta quando os instrumentos passarem** — o
   gancho calado e a conferência da casa verde. Sessão que "parece
   funcionar" numa máquina incompleta é o zero que mente.

## Os sintomas que denunciam migração malfeita

| Sintoma | Causa provável |
| --- | --- |
| "o agente esqueceu que sabia X" | a lição morava na memória da ferramenta (território 3), não em página |
| servidor MCP sumiu da lista | variável `${...}` sem valor, dependência ausente ou aprovação zerada |
| skill não carrega | sessão aberta fora da raiz — ou cópia parcial da pasta |
| comando "funcionava e parou" | perfil de CLI ou variável que ficou na máquina velha (território 4) |

Cada linha da esquerda parece um defeito diferente. As causas cabem numa
mão — e todas se conferem por instrumento antes de qualquer conserto.
