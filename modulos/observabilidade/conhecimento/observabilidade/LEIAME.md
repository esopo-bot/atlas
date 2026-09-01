# Observabilidade — a memória do workspace

O que este copiloto aprendeu sobre as aplicações deste workspace. **Nada aqui
é da camada e nada aqui viaja**: a atualização escreve estes arquivos uma vez
e nunca mais toca neles.

| Arquivo | O que mora ali | Quem escreve |
| --- | --- | --- |
| `desenho.md` | quem chama quem — o mapa das aplicações | **você, à mão** |
| `consultas-datadog.md` | as consultas que funcionaram, e as que mentiram | a skill, quando você mandar |
| `aplicacao-<nome>.md` | uma por aplicação: o que quebra, onde se olha | a skill, ao investigar |
| `incidente-<data>-<slug>.md` | um por incidente: o que era, como se achou | a skill, ao encerrar |

`aplicacao-exemplo.md` e `incidente-exemplo.md` mostram a forma preenchida
dos dois últimos — é deles que a skill parte ao criar os seus.

Tudo plano, sem pasta dentro de pasta: o site publica um nível de subpasta e
para ali. O nome da ferramenta vai no arquivo (`consultas-datadog.md`), nunca
numa pasta — assim uma segunda ferramenta entra ao lado sem renomear nada.

O formato de cada peça, e o porquê de tudo ser tabela, está em
[observabilidade](../observabilidade.md).

## Antes de adicionar um remoto a este repositório, leia isto

Esta pasta acumula nome de aplicação, de serviço e de incidente. **Ela é
commitável enquanto este repositório não tiver remoto** — e o histórico vale
a pena, porque a skill apaga crença errada e sem histórico uma apagada
indevida não se recupera.

Confira antes de confiar nessa frase:

```bash
git remote -v
```

**Devolveu alguma linha?** Então esta pasta já tem para onde vazar. Resolva-a
antes de qualquer push — publicação não se desfaz: reescrever a história tira
das listagens, não do alcance de quem já copiou.

Não existe linha de `.gitignore` aqui de propósito. Ela resolveria o vazamento
e mataria o histórico, que é justamente o que torna a autocorreção segura.
