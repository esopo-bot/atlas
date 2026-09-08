# voz

Faz a sessão falar em voz alta nos marcos — execução parada, aprovação
pedida, verificação verde. Quem opera sai da frente da tela e volta quando é
chamado.

Um instrumento só, `falar`. Dois motores: `edge-tts` neural quando há rede,
reserva offline quando não há. O primeiro uso cria o venv sozinho.

```bash
python montar.py --modulo voz
cp .agents/voz/voz.exemplo.json .agents/voz/voz.json
python .agents/voz/falar.py "a verificação ficou verde"
```

**O mecanismo viaja, a configuração fica.** O `falar.py` não sabe o nome de
ninguém: a voz, o ritmo e o nome pelo qual chamar quem opera saem do
`voz.json` local, que não entra no git.

Instalar é ligar; `"ligada": false` cala sem desinstalar. Não instalar é
desligar — ele é conforto, não guarda: nada que precise valer sempre depende
de alguém ouvir.

Windows: medido em 07/09/2026, o motor roda e o tocador TAMBÉM — fala em voz
alta, com áudio audível, em texto curto e em parágrafo longo. A reserva
offline continua não existindo lá, e isso virou decisão em vez de lacuna: sem
rede a própria sessão de IA não funciona, então reserva offline resolveria
problema que não existe.
