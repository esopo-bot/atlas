# Windows com Git Bash: as armadilhas e o conserto de cada uma

Onde o WSL e o PowerShell não estão à mão, a régua é Git Bash e Python.
Estas são as armadilhas que as medições acharam nos comandos das sessões, e
o conserto de cada uma. Nenhuma pede programa novo.

## O interpretador é `python`

`python3` pode ser o atalho da loja de aplicativos: está no `PATH`, o `which`
o acha, e ele não roda. Julgue executando, nunca pelo nome:

```bash
python -c "import sys; print(sys.version_info[0])"
```

Os ganchos da camada chamam o interpretador pelo nome que a instalação
mediu, e só voltam ao lançador `.claude/hooks/interpretador.sh` quando
nenhum respondeu.

## O Git Bash converte o que parece caminho

Argumento com barra e dois-pontos vira caminho do Windows antes de chegar ao
programa. `git show origin/main:pasta/arquivo` chega ao git como
`origin\main;pasta\arquivo` e falha. No comando que precisa do texto cru,
desligue a conversão só para ele:

```bash
MSYS_NO_PATHCONV=1 git show origin/main:pasta/arquivo
```

Não desligue para a sessão inteira: muito comando depende de `/c/...` virar
`C:\...`.

## Heredoc come contrabarra

Em heredoc sem aspas, o shell interpreta `\` e `$`. Use `<<'EOF'`, com
aspas. Roteiro Python com expressão regular ou caminho do Windows vai para
um arquivo na pasta de rascunho e roda com `python arquivo.py`.

## Fim de linha

Com `core.autocrlf` ligado, o arquivo no disco tem CRLF e o git guarda LF.
Diff que mostra o arquivo inteiro mudado é fim de linha: desfaça, não
normalize. Texto que sobe pelo `stdin`, como corpo de issue, sai limpo se for
montado em Python com `\n`; o `gh` guarda o que recebe, `\r` incluído.

## Codificação: cp1252 sem o modo UTF-8

Sem o modo UTF-8 do Python, a saída para um cano sai em cp1252. Quem lê em
UTF-8 vê letra trocada, e caractere fora do cp1252 derruba o `print`. Os
instrumentos e os ganchos da camada forçam UTF-8 na entrada e na saída, e
`python .agents/camada/camada.py provar` roda cada bancada com o modo
desligado, para acusar quem esquecer. Num roteiro seu:

```bash
python -X utf8 roteiro.py
```

ou `sys.stdout.reconfigure(encoding="utf-8")` no começo dele. Máquina que
liga `PYTHONUTF8=1` esconde o defeito: prove com `env -u PYTHONUTF8`.

## `/dev/null` é o `NUL`

No Git Bash, `< /dev/null` vira o dispositivo `NUL`, que o Python toma por
terminal: `sys.stdin.isatty()` responde verdadeiro. Programa que pergunta
quando há terminal pergunta, e lê fim de entrada.

## Caminho absoluto, não `cd`

O agente volta ao diretório de trabalho depois de cada comando, e
`cd pasta && comando` pode parar para pedir permissão. Use `git -C <pasta>`
e o caminho por extenso; `cd` só para instrumento que mede o diretório
atual.

## Processo se para pelo número

```bash
taskkill /PID <número> /T /F
```

Nunca pelo nome: `/IM python.exe` derruba as sessões e os servidores de
todo mundo que usa a máquina.

## E um `.sh` padrão?

Não. Medido sobre os comandos de uma semana, um lançador `.sh` evitaria uma
fração pequena dos erros de shell, e desligar a conversão de caminho para
todos quebraria mais comandos do que consertaria. Python faz o mesmo com
menos risco.
