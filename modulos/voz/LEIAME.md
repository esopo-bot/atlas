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

Windows é lacuna confessada, e a página diz onde: o motor roda, o tocador
nunca foi medido lá, e a reserva offline não existe.
