# Voz: a camada fala, e o que ela fala é marco, não narração

A sessão fala em voz alta nos poucos pontos em que ficar olhando a tela é
desperdício: quando a execução para, quando ela pede aprovação, quando a
verificação fica verde. Quem opera sai da frente do computador e volta
quando é chamado.

O módulo instala um instrumento só, `falar`. Ele fala e cala — não decide
quando falar. Quem decide é quem o chama.

## O que instala, e onde

```bash
python montar.py --modulo voz
```

| Arquivo | O que é |
| --- | --- |
| `.agents/voz/falar.py` | o instrumento; fala um texto e bloqueia até acabar |
| `.agents/voz/voz.exemplo.json` | o molde da configuração, só com `${PLACEHOLDER}` |
| `.agents/voz/.gitignore` | tira do git o `venv/` e o `voz.json` |

```bash
cp .agents/voz/voz.exemplo.json .agents/voz/voz.json
python .agents/voz/falar.py "a verificação ficou verde"
python .agents/voz/falar.py --testar
```

## O mecanismo viaja, a configuração fica

A separação é a razão de o módulo existir. O `falar.py` é público e não sabe
o nome de ninguém; o `voz.json` é local, não entra no git, e é dele que sai
o nome pelo qual chamar quem opera.

| Chave | O que faz | Padrão |
| --- | --- | --- |
| `ligada` | `false` cala o instrumento sem desinstalar nada | `true` |
| `voz` | a voz do motor neural | `pt-BR-FranciscaNeural` |
| `ritmo` | o desvio de velocidade que o motor aceita | `-8%` |
| `tratamento` | como chamar quem opera; abre a frase | vazio |

**Valor com `${` dentro não é valor.** O instrumento trata o placeholder do
molde como chave não preenchida e cai no padrão. Sem isso, a primeira
sessão depois de instalar chamaria quem opera de `${COMO_CHAMAR_QUEM_OPERA}`.

## Os dois motores, e por que são dois

1. **Neural (`edge-tts`).** Voz de gente. Precisa de rede.
2. **Reserva offline (`spd-say` no Linux, `say` no macOS).** Voz robótica.
   Não precisa de rede.

O instrumento tenta o neural, e só cai na reserva se ele não falar. Falhar
em silêncio não é opção: quando nenhum dos dois responde, o `falar` sai
diferente de zero e diz que nada falou.

O primeiro uso cria o venv em `.agents/voz/venv/` e instala o `edge-tts`
ali. **Venv não se versiona, se regenera** — apagar a pasta é o conserto,
não o problema.

## A lacuna do Windows, confessada

O motor neural é `pip` puro e roda em qualquer plataforma. **O que muda é o
tocador**, e é aí que a prova falta:

| Parte | Linux | Windows |
| --- | --- | --- |
| motor neural | provado — `edge-tts` no venv | não medido |
| tocador | provado — `pw-play` | **não medido** — MCI por `ctypes` |
| reserva offline | provado — `spd-say` | **não existe** — nenhuma declarada |

O caminho do Windows está escrito: `mciSendStringW` da `winmm.dll`, sem
dependência nova. Ele **nunca rodou lá**. Enquanto ninguém rodar, isto é
hipótese, no mesmo padrão das lacunas de NTFS — e a reserva offline do
Windows nem hipótese tem: `comando_da_reserva` devolve lista vazia, e há um
caso de teste cravando isso, para a lacuna não sumir calada.

## Os dois usos declarados

### Narração de execução

Falar nos pontos em que o motor já posta na issue, e em nenhum outro:
parou, aguardando aprovação, execução completa, verificação verde.

**O gancho no encadeador não está neste módulo.** Ele ficou de fora de
propósito: mexer no executor de roteiros é mudança de outro tamanho, e vira
issue própria. Hoje quem quiser a narração chama o `falar` de fora.

### Homologação narrada

O teatro: o navegador abre na frente de quem assiste, e a sessão narra o
que está fazendo enquanto faz.

1. Playwright em modo `headed` — janela de verdade, não `headless`.
2. `bringToFront()` na página **antes** de cada passo que a pessoa precisa
   ver. Sem isso a janela abre atrás do terminal e o teatro acontece para
   ninguém.
3. `falar` antes de cada passo, não depois. O instrumento bloqueia até
   terminar de falar, então a fala e o passo não se atropelam.

## As quatro armadilhas, todas pagas

- **Venv em pasta de scratchpad morre com a sessão.** Por isso o venv mora
  em `.agents/voz/venv/`, dentro do repositório, e não numa pasta temporária.
- **`spd-say` fica mudo em máquina PipeWire** enquanto o
  `speech-dispatcher` não estiver com `AudioOutputMethod` em `alsa`. O
  sintoma é o pior possível: sai zero e não sai som.
- **`pkill -f falar` mata a própria sessão que o digitou** — o padrão bate
  com a linha de comando de quem procura. Feche pelo processo, não pelo
  padrão.
- **Janela sem `bringToFront` abre atrás.** Vale para o teatro inteiro, não
  só para o primeiro passo.

## O que ele não faz

- **Não tagarela.** Marco, não narração contínua. Voz que fala o tempo todo
  vira ruído, e ruído se ignora — o mesmo motivo pelo qual aviso que ninguém
  atende sai do ritual.
- **Não vira tela.** Voz é para quem não está olhando a tela.
- **Não roda da fonte.** O `falar.py` de `modulos/voz/` recusa falar: criar
  o venv ali faria o `montar.py` embutir o venv inteiro na carga do
  instalador. Instale primeiro, rode a cópia depois.
