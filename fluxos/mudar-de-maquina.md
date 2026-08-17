# Mudar de máquina

O repositório viaja pelo git; o resto, não — e a perda é silenciosa. O
mapa do que morre:
[o estado que não viaja](../conhecimento/estado-que-nao-viaja.md).

## Antes de mudar

1. **Feche o trabalho**: commit do commitável, ponto de retomada na nota de
   continuação da casa.
2. **Copie a pasta do workspace inteira**, não só o clone — configuração
   local, notas e credenciais só viajam com a pasta (território 2).
3. **Anote o que vai morrer**: estado da ferramenta (território 3) e perfil
   do sistema (território 4) ficam. Não tente levá-los.

## Depois de mudar

1. **Abra uma sessão na raiz** — o `conferir-ambiente.py` acusa o que
   falta; se calar, os nomes estão no lugar.
2. **Siga a página de máquina nova da casa**, provando cada item pelo
   instrumento da própria linha.
3. **Refaça o que é do dono**: credencial, confiança de diretório,
   aprovação dos servidores MCP.
4. **Pronto só com os instrumentos verdes** — gancho calado e conferência
   da casa passando.

## Os sintomas de migração malfeita

| Sintoma | Causa provável |
| --- | --- |
| "o agente esqueceu que sabia X" | a lição morava na memória da ferramenta, não em página |
| servidor MCP sumiu da lista | variável sem valor, dependência ausente ou aprovação zerada |
| skill não carrega | sessão fora da raiz — ou cópia parcial da pasta |
| comando "funcionava e parou" | perfil de CLI ou variável que ficou na máquina velha |

Cada causa se confere por instrumento antes de qualquer conserto.
