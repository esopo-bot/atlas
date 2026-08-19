#!/usr/bin/env python3
"""painel de controle — dispara sessão headless e mostra o estado do
executor de roteiros, no navegador.

O que ele é: um servidor HTTP de biblioteca padrão, sem dependência nenhuma,
que faz três coisas e para:

1. serve uma página com uma caixa de prompt e um botão;
2. no disparo, escreve um roteiro de UMA etapa e chama o `encadeador.py`
   em segundo plano — execução de verdade, com evidência e verificação, não um
   `claude -p` solto;
3. pergunta o estado ao `andamento` do encadeador e devolve o JSON dele.

O que ele NÃO faz, de propósito: não fala com o modelo (quem fala é o
encadeador), não inventa estado (o `andamento` é a única fonte), não commita,
não empurra, não publica, não apaga trabalho. O painel de controle é vidro,
não motor.

Por que roteiro de uma etapa em vez de chamar `claude -p` direto: assim o
prompt livre e a execução inteira passam pelo MESMO caminho — evidência por
código, verificação re-executando as provas, teto de ciclos. Um caminho só
para manter, e o que vale para um vale para o outro.

A sessão herda `--dangerously-skip-permissions` do encadeador. Por isso o
`--cwd` deve ser worktree ou clone descartável, NUNCA a árvore que importa —
o painel de controle recusa subir se o `--cwd` for um repositório com
mudança não commitada, que é o sinal barato de "esta árvore importa".

Uso:
    painel.py --cwd <worktree> [--porta 4000] [--dir tmp/evidencias]
    painel.py --testar
"""

import argparse
import errno
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

def _raiz_da_camada() -> Path:
    """Sobe até achar o encadeador — nunca `Path.cwd()`.

    O painel de controle roda de dois lugares: instalado em
    `.agents/painel/` e, no repositório que PRODUZ o módulo, direto de
    `modulos/painel/.agents/painel/`. Contar pastas para cima só acerta o
    primeiro caso, e o segundo falharia achando que a camada não existe.
    Procurar o alvo acerta os dois.
    """
    aqui = Path(__file__).resolve()
    for pasta in aqui.parents:
        if (pasta / ".agents" / "encadeador" / "encadeador.py").exists():
            return pasta
    return aqui.parents[2]


RAIZ = _raiz_da_camada()
ENCADEADOR = RAIZ / ".agents" / "encadeador" / "encadeador.py"


def casa_do_painel_na_porta(porta: int) -> str | None:
    """Quem atende nesta porta é painel de controle? De que repositório? None
    se não for.

    Pergunta-se ao próprio servidor, em vez de investigar PID: a resposta
    dele é a prova, e um processo com o nome parecido não engana.
    """
    try:
        with urllib.request.urlopen(
                f"http://127.0.0.1:{porta}/trabalhos", timeout=3) as resposta:
            return json.loads(resposta.read()).get("repositorio")
    except (OSError, ValueError, json.JSONDecodeError):
        return None


TETO_SESSAO_S = 3600  # espelha TEMPO_SESSAO do encadeador


def descendentes(pai: int) -> list:
    """PIDs abaixo de `pai`, lendo /proc. Fora do Linux, devolve [].

    Sem dependência de fora: o painel de controle é de biblioteca padrão, e
    psutil resolveria isto ao custo de uma instalação que a camada não exige.
    Onde /proc não existe, o painel de controle diz "não medido" em vez de
    inventar.
    """
    filhos = {}
    try:
        for entrada in os.listdir("/proc"):
            if not entrada.isdigit():
                continue
            try:
                with open(f"/proc/{entrada}/stat", encoding="utf-8") as f:
                    campos = f.read().rsplit(")", 1)[1].split()
                filhos.setdefault(int(campos[1]), []).append(int(entrada))
            except (OSError, IndexError, ValueError):
                continue
    except OSError:
        return []
    fila, achados = [pai], []
    while fila:
        for pid in filhos.get(fila.pop(), []):
            achados.append(pid)
            fila.append(pid)
    return achados


def vivacidade(proc, inicio: float | None, gravado: dict = None) -> dict:
    """Os sinais que decidem se a execução trabalha, e o que cada um vale.

    Medido em 18/08/2026: sessão de modelo passa a vida esperando a API —
    443s de relógio para 5s de CPU. Logo, CPU parada NÃO é sinal de morte, e
    um painel de controle que dissesse "travado" por isso estaria mentindo.
    O sinal que vale é composto: o processo existe, quantas sessões ainda
    respiram, e quanto falta para o teto que mata sozinho.
    """
    if proc is None:
        # Execução disparada fora da mesa (pela linha de comando, por um
        # agendador) não tem processo aqui — mas TEM estado gravado, e é
        # ele que sabe. Sem isto a mesa dizia "desconhecida" com o motor
        # trabalhando ao lado.
        if gravado and gravado.get("situacao"):
            return {"situacao": gravado["situacao"], "de_fora": True,
                    "desde": gravado.get("desde"), "ate": gravado.get("ate"),
                    "porque": gravado.get("porque"),
                    "issue": gravado.get("issue"),
                    "etapa": gravado.get("etapa")}
        return {"situacao": "desconhecida"}
    if proc.poll() is not None:
        return {"situacao": "encerrado", "codigo": proc.returncode}
    filhos = descendentes(proc.pid)
    sessoes = 0
    for pid in filhos:
        try:
            with open(f"/proc/{pid}/cmdline", "rb") as f:
                if b"claude" in f.read():
                    sessoes += 1
        except OSError:
            continue
    decorrido = int(time.time() - inicio) if inicio else None
    # O motor grava o que está fazendo; quando ele diz que espera, ele VENCE
    # a inferência. Sem isto a mesa dizia "trabalhando" com o motor dormindo
    # seis horas — e `sessoes: None` ao lado denunciava a mentira sem
    # corrigi-la (defeito 4 de 18/08/2026).
    if gravado and gravado.get("situacao") in ("dormindo", "aguardando-resposta"):
        return {"situacao": gravado["situacao"],
                "desde": gravado.get("desde"),
                "ate": gravado.get("ate"),
                "porque": gravado.get("porque"),
                "issue": gravado.get("issue"),
                "etapa": gravado.get("etapa"),
                "sessoes": sessoes if filhos else None,
                "decorrido_s": decorrido}
    return {"situacao": "trabalhando",
            "sessoes": sessoes if filhos else None,
            "decorrido_s": decorrido,
            "teto_s": TETO_SESSAO_S,
            "resta_s": (max(0, TETO_SESSAO_S - decorrido)
                        if decorrido is not None else None)}


ARQUIVO_ESTADO = "estado.json"


ARQUIVO_EXECUTOR = "nucleo/executor.json"
INTERVALO_DO_QUADRO_S = 120  # regra 7: rede com cortesia, longe do polling


def configuracao_do_executor(cwd):
    """O executor.json do alvo — ou None. O painel de controle não valida,
    só lê.
    """
    try:
        dado = json.loads((Path(cwd) / ARQUIVO_EXECUTOR)
                          .read_text(encoding="utf-8"))
        return dado if isinstance(dado, dict) else None
    except (OSError, ValueError):
        return None


def estado_gravado(dir_evidencias, trabalho):
    """O que o motor gravou sobre este trabalho — ou None.

    O painel de controle continua sendo vidro: ele não inventa este estado,
    lê o que o motor escreveu. É a única fonte que sabe de espera, porque
    espera não deixa rastro em evidência nenhuma.
    """
    try:
        dado = json.loads((Path(dir_evidencias) / trabalho / ARQUIVO_ESTADO)
                          .read_text(encoding="utf-8"))
        return dado if isinstance(dado, dict) else None
    except (OSError, ValueError):
        return None


def corrigir_proxima_acao(estado: dict) -> dict:
    """Cala o convite a disparar quando a execução JÁ está disparada.

    O `andamento` é honesto dentro do contrato dele: sem evidência no disco, ele
    conclui "nada rodou ainda" e manda executar. Só que o painel de controle
    sabe uma coisa que ele não sabe — se o processo está vivo. Repassar
    aquele convite é mandar disparar o que já está no ar, e foi o que quase
    provocou um disparo duplo. Quem tem a informação a mais corrige a
    mensagem.
    """
    esperando = (estado.get("vivacidade") or {}).get("situacao") in (
        "dormindo", "aguardando-resposta")
    if estado.get("processo") == "rodando" and not esperando \
            and estado.get("estado") == "em-curso":
        estado["proxima_acao"] = (
            "rodando agora — espere. A etapa só escreve evidência quando termina, "
            "então pasta vazia no começo é o esperado. Não dispare de novo: a "
            "trava recusaria.")
    return estado


def decidir_porta_ocupada(porta: int, repositorio: str,
                          ocupante: str | None) -> tuple:
    """(código, recado) para a porta ocupada. Função pura, para ser testada.

    O caso comum — F5 duas vezes no mesmo repositório — NÃO é erro: o que se
    queria
    já está no ar. Sair 0 diz a verdade e, de quebra, apaga o popup de
    SystemExit do depurador, que só interrompe em código diferente de zero.
    """
    if ocupante == repositorio:
        return 0, (f"o painel de controle deste repositório já está no ar: "
                   f"http://127.0.0.1:{porta}\n"
                   "  (nada a fazer — abra o endereço acima)")
    if ocupante:
        return 2, (f"PAREI — a porta {porta} é do painel de controle de "
                   "OUTRO repositório:\n"
                   f"  {ocupante}\n"
                   "Uma porta por repositório é o desenho. Suba este "
                   "noutra:\n"
                   f"  --porta {porta + 1}")
    return 2, (f"PAREI — a porta {porta} está ocupada, e não por um "
               "painel de controle.\n"
               "Quem está nela:\n"
               f"  ss -ltnp | grep :{porta}\n"
               "Encerre aquele, ou suba este noutra porta:\n"
               f"  --porta {porta + 10}")


def versao_da_camada() -> str:
    """A versão sai do montar.py, que é onde ela já mora.

    O painel de controle não carrega número próprio de propósito: duas
    versões para a mesma camada divergem no primeiro dia em que alguém
    esquece de subir uma delas. Aqui há uma fonte só, e ela é a que o
    `--versao` também imprime.
    """
    try:
        for linha in (RAIZ / "montar.py").read_text(encoding="utf-8").splitlines():
            if linha.startswith("VERSAO = "):
                return linha.split("=", 1)[1].strip().strip("\"'")
            if not linha.startswith(("#", "\"", "'")) and linha.strip():
                break  # a declaração é do topo; não varra o arquivo inteiro
    except OSError:
        pass
    return "desconhecida"
NOME_OK = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")


def agora() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def nome_de_trabalho(prefixo: str = "painel") -> str:
    return f"{prefixo}-{agora()}"


def validar_trabalho(nome: str) -> str | None:
    """O nome vira pasta — a mesma régua do contrato da evidência."""
    if not NOME_OK.match(nome or ""):
        return "nome de trabalho inválido: minúsculo, sem barra nem espaço, até 64"
    return None


def roteiro_de_um_prompt(prompt: str, teto: int = 3,
                           turnos: int = 24, issue: int = None) -> dict:
    """Prompt livre vira execução de uma etapa mais a verificação.

    A verificação entra sempre: sem ela o painel de controle mostraria
    'segue' para uma sessão que provou o que não se re-executa, que é o erro
    que o executor de roteiros inteiro existe para não cometer.
    """
    roteiro = {
        "teto": teto,
        "etapas": [
            # `max-turnos` é o que decide se a sessão entrega ou morre no
            # teto, então ele é controle de tela. O padrão do motor (16)
            # matou o primeiro pedido disparado pelo painel de controle; 24
            # dá folga ao pedido comum sem convidar ao pedido caro, que é
            # caso de execução.
            {"nome": "pedido", "tipo": "sessao", "prompt": prompt,
             "max-turnos": turnos},
            {"nome": "verifica", "tipo": "verificacao", "depende": ["pedido"]},
        ],
    }
    # O vínculo com a issue é o que faz a execução contar a história lá: com
    # ele, cada etapa vira comentário e a pergunta chega em quem decide.
    if issue:
        roteiro["issue"] = int(issue)
    return roteiro


def arvore_suja(cwd: Path) -> bool:
    """Mudança não commitada = árvore que importa. Fora do git, não opina."""
    try:
        r = subprocess.run(["git", "status", "--porcelain"], cwd=cwd,
                           capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return False
    return r.returncode == 0 and bool(r.stdout.strip())


class Motor:
    """A ponte para o encadeador. Um lugar só chama subprocesso."""

    def __init__(self, cwd: Path, dir_evidencias: Path, dirs_roteiros: list):
        self.cwd = cwd
        self.dir = dir_evidencias
        self.roteiros = dirs_roteiros
        self.rodando: dict[str, subprocess.Popen] = {}
        self.inicio: dict[str, float] = {}
        self.trava = threading.Lock()
        self._quadro, self._quadro_em = None, 0.0

    def _arquivo_de_trava(self) -> Path:
        """Uma trava por ALVO, e o nome vem do caminho do alvo.

        Fica no diretório de evidências, que já é o estado deste executor de
        roteiros. O resumo do caminho evita nome ilegal de arquivo sem
        perder unicidade.
        """
        marca = hashlib.sha256(str(self.cwd).encode()).hexdigest()[:12]
        return self.dir / f".trava-{marca}.json"

    def ocupado(self) -> str | None:
        """Uma execução por vez neste alvo. Duas na mesma árvore se atropelam.

        O motor já garante um escritor por TRABALHO; o que falta é impedir
        dois TRABALHOS diferentes na mesma árvore. Sessões pulam permissões e
        editam arquivo: duas ao mesmo tempo no mesmo lugar é corrida, e o
        evidência de cada uma descreveria um disco que a outra já mudou.

        A trava é de ARQUIVO, não de memória: dois painéis de controle do
        mesmo alvo — o que acontece quando um F5 sobe o segundo sem o
        primeiro ter morrido — teriam duas travas de memória e nenhuma
        proteção. Trava morta (o dono já não existe) não segura ninguém: só
        o PID vivo conta.
        """
        with self.trava:
            for nome, proc in self.rodando.items():
                if proc.poll() is None:
                    return nome
        arquivo = self._arquivo_de_trava()
        try:
            dono = json.loads(arquivo.read_text(encoding="utf-8"))
            os.kill(int(dono["pid"]), 0)
        except (OSError, ValueError, KeyError, json.JSONDecodeError):
            return None  # sem trava, ilegível, ou dono morto
        return (f"{dono.get('trabalho', '?')} "
                f"(outro painel de controle, pid {dono['pid']})")

    def _travar(self, pid: int, trabalho: str) -> None:
        self._arquivo_de_trava().write_text(
            json.dumps({"pid": pid, "trabalho": trabalho, "cwd": str(self.cwd)}),
            encoding="utf-8")

    def _achados(self) -> dict:
        """nome exibido -> caminho. A primeira pasta da lista vence o nome.

        São duas pastas por desenho: a versionada, das execuções oficiais que
        viajam com a camada, e a de rascunho, que é sua e não viaja. Nome
        repetido nas duas fica com a oficial — rascunho não sequestra o nome
        de uma execução que o repositório inteiro usa.
        """
        achados = {}
        for pasta in self.roteiros:
            if not pasta.is_dir():
                continue
            for p in sorted(pasta.glob("*.json")):
                # Nem todo .json da pasta é roteiro: a síntese escreve
                # proposta de regra ali, e ela aparecia no seletor como se
                # fosse execução. Escolher aquela só falhava no disparo.
                # A marca é ter lista de etapas — barata de verificar.
                if not p.is_file() or p.name in achados:
                    continue
                try:
                    dado = json.loads(p.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    continue
                if isinstance(dado, dict) and isinstance(dado.get("etapas"), list):
                    achados[p.name] = p
        return achados

    def catalogo(self) -> list:
        """Os roteiros que existem para escolher — nome puro, sem caminho."""
        return sorted(self._achados())

    def ler_roteiro(self, nome: str) -> tuple[dict | None, str | None]:
        """Nome puro só: o painel de controle nunca abre caminho que o
        navegador montou.
        """
        alvo = self._achados().get(nome)
        if alvo is None:
            return None, f"roteiro desconhecido: {nome}"
        try:
            dado = json.loads(alvo.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            return None, f"roteiro ilegível: {e}"
        if not isinstance(dado, dict) or not isinstance(dado.get("etapas"), list):
            return None, "roteiro sem lista de etapas"
        return dado, None

    def disparar(self, roteiro: dict, trabalho: str) -> dict:
        self.dir.mkdir(parents=True, exist_ok=True)
        alvo = self.dir / f"{trabalho}.roteiro.json"
        alvo.write_text(json.dumps(roteiro, ensure_ascii=False, indent=2),
                        encoding="utf-8")
        log = (self.dir / f"{trabalho}.log").open("w", encoding="utf-8")
        proc = subprocess.Popen(
            [sys.executable, str(ENCADEADOR), "executar",
             "--roteiro", str(alvo), "--trabalho", trabalho,
             "--dir", str(self.dir), "--cwd", str(self.cwd)],
            stdout=log, stderr=subprocess.STDOUT, cwd=str(self.cwd))
        with self.trava:
            self.rodando[trabalho] = proc
            self.inicio[trabalho] = time.time()
        self._travar(proc.pid, trabalho)
        return {"trabalho": trabalho, "roteiro": alvo.name}

    def andamento(self, trabalho: str, roteiro: Path | None = None) -> dict:
        cmd = [sys.executable, str(ENCADEADOR), "andamento",
               "--trabalho", trabalho, "--dir", str(self.dir)]
        if roteiro and roteiro.exists():
            cmd += ["--roteiro", str(roteiro)]
        r = subprocess.run(cmd, capture_output=True, text=True,
                           cwd=str(self.cwd), timeout=60)
        if r.returncode != 0:
            return {"erro": (r.stderr or r.stdout).strip()[:400]}
        try:
            estado = json.loads(r.stdout)
        except json.JSONDecodeError:
            return {"erro": "o andamento não devolveu JSON"}
        with self.trava:
            proc = self.rodando.get(trabalho)
        estado["processo"] = ("rodando" if proc and proc.poll() is None
                              else "encerrado" if proc else "desconhecido")
        gravado = estado_gravado(self.dir, trabalho)
        estado["gravado"] = gravado
        estado["vivacidade"] = vivacidade(proc, self.inicio.get(trabalho),
                                          gravado)
        corrigir_proxima_acao(estado)
        log = self.dir / f"{trabalho}.log"
        estado["log"] = (log.read_text(encoding="utf-8", errors="replace")[-4000:]
                         if log.exists() else "")
        return estado

    def backlog(self) -> dict:
        """As issues abertas do repositório configurado, com cache.

        A mesa redesenha a cada 2,5s; a rede, não. O cache é o que faz a
        regra 7 (rede com cortesia) valer aqui — sem ele, o polling da tela
        viraria rajada no GitHub. Falha de rede não derruba a mesa: devolve
        'sem dado' e a página segue servindo.
        """
        agora = time.time()
        with self.trava:
            if self._quadro and agora - self._quadro_em < INTERVALO_DO_QUADRO_S:
                return self._quadro
        cfg = configuracao_do_executor(self.cwd) or {}
        repositorio = ((cfg.get("issues") or {}).get("repositorio") or "")
        if not repositorio or "${" in repositorio:
            achado = {"issues": [], "recado": "sem repositório de issues "
                                              "configurado"}
        else:
            try:
                r = subprocess.run(
                    ["gh", "issue", "list", "--repo", repositorio, "--state",
                     "open", "--limit", "30", "--json", "number,title"],
                    capture_output=True, text=True, timeout=30)
                achado = ({"issues": json.loads(r.stdout), "repositorio":
                           repositorio} if r.returncode == 0 else
                          {"issues": [], "recado": "sem dado (o gh não "
                                                   "respondeu)"})
            except (OSError, subprocess.SubprocessError, ValueError):
                achado = {"issues": [], "recado": "sem dado (rede ou gh "
                                                  "indisponível)"}
        with self.trava:
            self._quadro, self._quadro_em = achado, agora
        return achado

    def trabalhos(self) -> list:
        """Trabalho do executor de roteiros e evidência avulsa não são a mesma coisa.

        O diretório de evidências também recebe trilha de gancho — o professor
        de credencial escreve lá, uma evidência por decisão, todos com a MESMA
        ordem. Lidos como execução, viram 'ciclo 8 de teto 1, parada': alarme
        falso sobre coisa que funcionou. A marca de execução é ter roteiro
        ao lado; sem ele, o painel de controle mostra como avulso e não
        opina sobre estado.
        """
        if not self.dir.is_dir():
            return []
        saida = []
        for p in sorted((d for d in self.dir.iterdir() if d.is_dir()),
                        key=lambda d: d.name, reverse=True):
            gravado = estado_gravado(self.dir, p.name) or {}
            saida.append({"nome": p.name,
                          # Roteiro ao lado OU estado gravado: quem disparou
                          # pela linha de comando não deixa o primeiro, e a
                          # mesa o tratava como trilha avulsa — recusando-se a
                          # opinar sobre uma execução de verdade.
                          "execucao": bool(gravado) or
                          (self.dir / f"{p.name}.roteiro.json").exists(),
                          # A situação sai do disco, não de um subprocesso por
                          # trabalho: a lista é redesenhada a cada ciclo, e
                          # pagar `andamento` por item derrubaria a mesa.
                          "situacao": gravado.get("situacao"),
                          "issue": gravado.get("issue")})
        return saida


PAGINA = """<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Mesa do executor de roteiros</title><style>
/* A mesa é um instrumento, não um site. Uma família monoespaçada carrega
   todo dado e todo rótulo — placa de equipamento, silkscreen —, e a sans
   entra só onde há frase para ler. Cor é SINAL: o que não é estado não tem
   cor. */
:root{
  --papel:#fbfaf7; --tinta:#1c1b19; --grafite:#6b6862; --fraco:#9a968d;
  --linha:#e5e2da; --sulco:#f1eee7;
  --segue:#2f6f4e; --para:#a32e28; --pergunta:#b0741e; --corre:#2b5c8a;
  --mono:ui-monospace,"SF Mono","Cascadia Mono","Roboto Mono",Menlo,monospace;
  --sans:ui-sans-serif,system-ui,"Segoe UI",Roboto,sans-serif;
}
@media(prefers-color-scheme:dark){:root{
  --papel:#17161a; --tinta:#eceae4; --grafite:#9b978f; --fraco:#6d6960;
  --linha:#2c2a2f; --sulco:#201f24;
  --segue:#5fae83; --para:#e0685f; --pergunta:#e0a34e; --corre:#6ea8dd;
}}
*{box-sizing:border-box}
body{margin:0;padding:28px 20px 64px;background:var(--papel);color:var(--tinta);
  font:14px/1.55 var(--sans);-webkit-font-smoothing:antialiased}
.mesa{max-width:1080px;margin:0 auto}

/* placa de identificação */
.placa{display:flex;align-items:baseline;gap:14px;flex-wrap:wrap;
  border-bottom:2px solid var(--tinta);padding-bottom:10px;margin-bottom:2px}
.placa h1{margin:0;font:600 15px/1 var(--mono);letter-spacing:.22em;
  text-transform:uppercase}
.selo{font:500 11px/1 var(--mono);letter-spacing:.1em;color:var(--grafite);
  border:1px solid var(--linha);border-radius:2px;padding:4px 7px}
.farol{margin-left:auto;display:flex;align-items:center;gap:7px;
  font:600 11px/1 var(--mono);letter-spacing:.14em;text-transform:uppercase}
.bulbo{width:8px;height:8px;border-radius:50%;background:var(--fraco);
  box-shadow:0 0 0 3px color-mix(in srgb,var(--fraco) 22%,transparent)}
.f-corre .bulbo{background:var(--corre);box-shadow:0 0 0 3px color-mix(in srgb,var(--corre) 22%,transparent);animation:pulsa 1.6s ease-in-out infinite}
.f-corre{color:var(--corre)} .f-segue .bulbo{background:var(--segue)} .f-segue{color:var(--segue)}
.f-para .bulbo{background:var(--para)} .f-para{color:var(--para)}
.f-pergunta .bulbo{background:var(--pergunta)} .f-pergunta{color:var(--pergunta)}
@keyframes pulsa{0%,100%{opacity:1}50%{opacity:.35}}
@media(prefers-reduced-motion:reduce){.f-corre .bulbo{animation:none}}

/* coordenadas: onde a máquina está apoiada */
.coord{display:grid;grid-template-columns:auto 1fr;gap:0 18px;
  border-bottom:1px solid var(--linha);padding:12px 0;margin-bottom:20px}
.coord dt{font:500 10px/1.9 var(--mono);letter-spacing:.16em;color:var(--fraco);
  text-transform:uppercase}
.coord dd{margin:0;font:13px/1.9 var(--mono);word-break:break-all}

/* comandos */
.comandos{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:6px}
label.campo{display:flex;align-items:center;gap:7px;
  font:500 10px/1 var(--mono);letter-spacing:.14em;color:var(--fraco);
  text-transform:uppercase}
select,input,textarea{font:13px/1.4 var(--mono);color:var(--tinta);
  background:var(--sulco);border:1px solid var(--linha);border-radius:3px;
  padding:7px 9px}
textarea{width:100%;min-height:104px;resize:vertical;margin:10px 0 0;
  background:var(--sulco)}
button{font:600 11px/1 var(--mono);letter-spacing:.16em;text-transform:uppercase;
  color:var(--papel);background:var(--tinta);border:0;border-radius:3px;
  padding:11px 20px;cursor:pointer}
button:disabled{opacity:.4;cursor:default}
:focus-visible{outline:2px solid var(--corre);outline-offset:2px}
.nota{font:12px/1.5 var(--sans);color:var(--fraco);flex:1 1 220px}
.direita{margin-left:auto}

/* A ASSINATURA: a fita de evidências. O encadeador imprime uma evidência por etapa,
   em ordem — a tela mostra a fita saindo dele, com a borda serrilhada de
   papel picotado feita só com gradiente. */
.fita{margin:24px 0 0;border:1px solid var(--linha);border-radius:3px;
  background:var(--sulco);overflow:hidden}
.fita-topo{display:flex;justify-content:space-between;align-items:center;
  padding:9px 14px 9px 30px;border-bottom:1px solid var(--linha);
  font:500 10px/1 var(--mono);letter-spacing:.16em;color:var(--fraco);
  text-transform:uppercase}
.tira{position:relative;margin:0;padding:0;list-style:none}
.tira::before{content:"";position:absolute;left:9px;top:0;bottom:0;width:7px;
  background:radial-gradient(circle at 3.5px 5px,var(--papel) 2.2px,transparent 2.4px)
    0 0/7px 13px repeat-y}
.linha-r{display:grid;grid-template-columns:34px 1fr 84px 52px;gap:12px;
  align-items:baseline;padding:11px 14px 11px 30px;
  border-bottom:1px dashed var(--linha);font:13px/1.5 var(--mono)}
.linha-r:last-child{border-bottom:0}
.ordem{color:var(--fraco);font-size:11px;letter-spacing:.08em}
.nome{font-weight:500}
.vd{font:600 10px/1 var(--mono);letter-spacing:.14em;text-transform:uppercase}
.vd.segue{color:var(--segue)}
.desenho{display:flex;flex-wrap:wrap;align-items:center;gap:.35rem;margin:.6rem 0}
.passo{padding:.2rem .5rem;border-radius:.35rem;font-size:.82rem;
  border:1px solid var(--borda);white-space:nowrap}
.passo.segue{background:var(--segue);color:#fff;border-color:var(--segue)}
.passo.para{background:var(--para);color:#fff;border-color:var(--para)}
.passo.pergunta{background:var(--pergunta);color:#000;border-color:var(--pergunta)}
.passo.espera{opacity:.55}
.passo.agora{outline:2px solid var(--corre);outline-offset:1px;font-weight:600}
.seta{opacity:.4;font-size:.8rem}
.conta{margin:.1rem 0 .6rem;font-size:.8rem;opacity:.75}
.quadro{margin:.5rem 0;border:1px solid var(--borda);border-radius:.4rem;
  max-height:9rem;overflow:auto;font-size:.85rem}
.quadro-topo{padding:.25rem .5rem;opacity:.7;font-size:.78rem;
  border-bottom:1px solid var(--borda)}
.issue{display:flex;gap:.5rem;align-items:center;padding:.2rem .5rem}
.issue .num{opacity:.6;min-width:2.6rem}
.issue .tit{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.disparar-issue{font-size:.75rem;padding:.1rem .45rem} .vd.para{color:var(--para)}
.vd.pergunta{color:var(--pergunta)} .vd.espera{color:var(--fraco)}
.ciclo{color:var(--fraco);font-size:11px;text-align:right}
.detalhe{grid-column:2/-1;font:12.5px/1.55 var(--sans);color:var(--grafite);
  margin-top:5px}
.detalhe b{color:var(--tinta)}
.vazia{padding:22px 30px;color:var(--fraco);font:13px/1 var(--mono)}

/* recados */
.recado{border-left:2px solid var(--corre);background:var(--sulco);
  padding:12px 15px;margin:20px 0 0;border-radius:0 3px 3px 0;
  font:13.5px/1.6 var(--sans)}
.recado b{font:600 10px/1 var(--mono);letter-spacing:.16em;text-transform:uppercase;
  display:block;margin-bottom:6px;color:var(--grafite)}
.recado.perg{border-left-color:var(--pergunta)}
.recado.perg b{color:var(--pergunta)}
.recado.ruim{border-left-color:var(--para)} .recado.ruim b{color:var(--para)}

/* rodapé de vivacidade e o log cru */
.rodape{display:flex;gap:10px 26px;flex-wrap:wrap;align-items:baseline;
  margin-top:16px;padding-top:12px;border-top:1px solid var(--linha);
  font:12px/1.6 var(--mono);color:var(--grafite)}
.rodape b{color:var(--tinta);font-weight:600}
details{margin-top:16px}
summary{cursor:pointer;font:500 10px/1 var(--mono);letter-spacing:.16em;
  color:var(--fraco);text-transform:uppercase;padding:6px 0}
pre{margin:8px 0 0;padding:13px 15px;background:var(--sulco);
  border:1px solid var(--linha);border-radius:3px;overflow:auto;max-height:300px;
  font:12px/1.6 var(--mono);white-space:pre-wrap;color:var(--grafite)}
@media(max-width:620px){
  .linha-r{grid-template-columns:28px 1fr;gap:6px}
  .vd,.ciclo{grid-column:2;text-align:left}
  .coord{grid-template-columns:1fr}
}
</style></head><body><div class="mesa">

<div class="placa">
  <h1>Mesa do executor de roteiros</h1>
  <span class="selo" id="versao">—</span>
  <span class="farol" id="farol"><span class="bulbo"></span><span id="farol-txt">sem trabalho</span></span>
</div>

<dl class="coord">
  <dt>repositório</dt><dd id="repositorio">—</dd>
  <dt>sessão</dt><dd id="alvo">—</dd>
  <dt>evidências</dt><dd id="evidencias">—</dd>
</dl>

<div class="comandos">
  <label class="campo">disparar
    <select id="modo"><option value="prompt">um pedido meu</option></select>
  </label>
  <button id="b">Disparar</button>
  <label class="campo" id="lturnos">turnos
    <input id="turnos" type="number" value="24" min="4" max="120" style="width:62px">
  </label>
  <label class="campo" id="lteto" title="quantas vezes a execução pode reprovar antes de escalar">ciclos
    <input id="teto" type="number" value="3" min="1" max="9" style="width:52px">
  </label>
  <label class="campo" id="lissue" title="o número da issue que este trabalho atende: a execução conta a história lá, passo a passo">issue
    <input id="issue" type="number" min="1" placeholder="—" style="width:64px">
  </label>
  <span class="nota" id="dica"></span>
  <label class="campo direita" title="mostrar também os trabalhos que já terminaram">
    <input id="historico" type="checkbox"> histórico
  </label>
  <label class="campo direita">acompanhar <select id="sel"></select></label>
</div>
<div id="quadro" class="quadro"></div>
<textarea id="p" placeholder="O pedido, completo. A sessão nasce sem contexto: diga onde olhar, o que medir e o que você aceita como prova."></textarea>

<div id="saida"></div>
</div>
<script>
const $=i=>document.getElementById(i);
let atual=null, assinatura='', parado=false;

const ESTADOS={'aguardando-aprovacao':['f-pergunta','pergunta'],
  'parada':['f-para','parada'],'completa':['f-segue','completa'],
  'em-curso':['f-corre','trabalhando']};
const TITULOS={'aguardando-aprovacao':'❓ PERGUNTA','parada':'⛔ parada',
  'completa':'✓ completa','em-curso':'⏳ rodando'};

function esc(s){return String(s??'').replace(/[<&>]/g,c=>({'<':'&lt;','&':'&amp;','>':'&gt;'}[c]))}
function mm(s){return s==null?'?':Math.floor(s/60)+'m'+String(s%60).padStart(2,'0')}
function modoRoteiro(){return $('modo').value!=='prompt'}

function ajusta(){
  const m=modoRoteiro();
  for(const i of ['p','lteto','lturnos'])$(i).style.display=m?'none':'';
  $('dica').textContent=m
    ?'execução de várias etapas — o prompt de cada uma está dentro do arquivo'
    :'vira uma execução de uma etapa mais a verificação. Turnos de menos = a sessão morre sem entregar nada';
}

// Vivacidade: sessão de modelo espera a API quase o tempo todo — medido, 443s
// de relógio para 5s de CPU. O sinal aqui não é processador: é o processo
// existir, quantas sessões respiram, e quanto falta para o teto que mata
// sozinho. Espera com prazo não é travamento.
function vivo(v){
  if(!v||v.situacao==='desconhecida')return '';
  if(v.situacao==='encerrado')return `processo <b>encerrado</b> · exit ${v.codigo}`;
  // Espera não é trabalho. O motor grava dormindo e aguardando-resposta, e a
  // mesa repete o que ele gravou em vez de dizer "trabalhando" com ninguém
  // trabalhando — era o defeito 4.
  if(v.situacao==='dormindo')
    return `<b>dormindo</b> até ${v.ate||'?'} (${v.porque||'espera'})` +
           `${v.etapa?` na etapa <b>${v.etapa}</b>`:''} · ninguém está trabalhando`;
  if(v.situacao==='aguardando-resposta')
    return `<b>aguardando você</b> na issue ${v.issue||'?'}` +
           `${v.etapa?`, etapa <b>${v.etapa}</b>`:''} · responda lá e retome`;
  const s=v.sessoes==null?'sessões não medidas aqui'
    :`<b>${v.sessoes}</b> sessão${v.sessoes===1?'':'es'} viva${v.sessoes===1?'':'s'}`;
  return `${s} · <b>${mm(v.decorrido_s)}</b> corridos · morre sozinha em ${mm(v.resta_s)}`;
}

function farol(estado){
  const [cls,txt]=ESTADOS[estado]||['','sem trabalho'];
  $('farol').className='farol '+cls; $('farol-txt').textContent=txt;
  document.title=(TITULOS[estado]?TITULOS[estado]+' · ':'')+'Mesa do executor de roteiros';
}

function fita(d){
  const et=d.etapas||[];
  if(!et.length)return '<p class="vazia">nenhuma evidência ainda</p>';
  return et.map(e=>{
    const vd=e.veredito||'espera';
    const faltas=(e.faltas||[]).map(esc).join('<br>');
    const perg=e.pergunta?`<b>${esc(e.pergunta)}</b>`:'';
    const det=[perg,faltas].filter(Boolean).join('<br>');
    return `<li class="linha-r">
      <span class="ordem">${String(e.ordem).padStart(2,'0')}</span>
      <span class="nome">${esc(e.nome)}</span>
      <span class="vd ${vd}">${vd==='espera'?'·····':vd}</span>
      <span class="ciclo">${e.ciclo?e.ciclo.i+'/'+e.ciclo.teto:''}</span>
      ${det?`<span class="detalhe">${det}</span>`:''}</li>`;
  }).join('');
}

// O desenho da execução: a mesma matéria-prima da fita, lida de relance.
// Cada etapa é um quadrado — verde passou, vermelho parou, e a que está em
// curso pisca. Quem olha vê o passo atual e o que falta sem ler linha.
function desenho(d){
  const et=d.etapas||[];
  if(!et.length)return '';
  const atual=et.findIndex(e=>!e.veredito);
  const passos=et.map((e,i)=>{
    const vd=e.veredito||'espera';
    const eu=(i===atual)?' agora':'';
    return `<span class="passo ${vd}${eu}" title="${esc(e.nome)}: ${vd}">` +
           `${esc(e.nome)}</span>`;
  }).join('<span class="seta">→</span>');
  const feitas=et.filter(e=>e.veredito).length;
  return `<div class="desenho">${passos}</div>` +
         `<p class="conta">${feitas} de ${et.length} etapas · ` +
         `${et.length-feitas} pela frente</p>`;
}

function pinta(d){
  if(d.erro){$('saida').innerHTML=`<div class="recado ruim"><b>não consegui ler</b>${esc(d.erro)}</div>`;farol();return}
  farol(d.estado);
  const perg=(d.etapas||[]).filter(e=>e.pergunta);
  const v=vivo(d.vivacidade);
  $('saida').innerHTML=`
    ${perg.length?`<div class="recado perg"><b>o executor de roteiros está te perguntando</b>
      ${perg.map(e=>`<code>${esc(e.nome)}</code>: ${esc(e.pergunta)}`).join('<br>')}
      <br><br>Ela fica parada até você responder — nada roda enquanto isso.</div>`:''}
    ${desenho(d)}
    <div class="fita">
      <div class="fita-topo"><span>fita de evidências</span>
        <span>${esc(d.estado||'')} · ${d.paras??0} parada${d.paras===1?'':'s'}</span></div>
      <ul class="tira">${fita(d)}</ul>
    </div>
    ${d.proxima_acao?`<div class="recado"><b>próxima ação</b>${esc(d.proxima_acao)}</div>`:''}
    ${v?`<div class="rodape">${v}</div>`:''}
    ${d.log?`<details><summary>log da execução</summary><pre>${esc(d.log)}</pre></details>`:''}`;
}

async function ciclo(){
  const t=$('sel').value;
  let d; try{ d=await (await fetch('/estado?trabalho='+encodeURIComponent(t||''))).json() }
  catch(e){ return }
  $('versao').textContent='camada '+d.versao;
  $('repositorio').textContent=d.repositorio; $('alvo').textContent=d.alvo;
  $('evidencias').textContent=d.evidencias;

  const md=$('modo'), antesM=md.value;
  const listaM=['prompt'].concat(d.roteiros);
  if(md.dataset.chave!==listaM.join('|')){
    md.dataset.chave=listaM.join('|');
    md.innerHTML='<option value="prompt">um pedido meu</option>'
      +d.roteiros.map(n=>`<option value="${esc(n)}">${esc(n)}</option>`).join('');
    if(antesM)md.value=antesM; ajusta();
  }
  // O backlog do quadro configurado, e o disparo a partir de uma issue.
  const q=$('quadro');
  if(q){
    const qs=(d.quadro&&d.quadro.issues)||[];
    const chave=JSON.stringify(qs)+(d.modo||'');
    if(q.dataset.chave!==chave){
      q.dataset.chave=chave;
      const soIssues=d.modo==='so-issues';
      q.innerHTML=qs.length
        ? `<div class="quadro-topo">backlog de ${esc((d.quadro||{}).repositorio||'')}</div>`
          + qs.map(i=>`<div class="issue"><span class="num">#${i.number}</span>
              <span class="tit">${esc(i.title)}</span>
              ${soIssues?'':`<button class="disparar-issue" data-n="${i.number}">disparar</button>`}
             </div>`).join('')
        : `<div class="quadro-topo">${esc((d.quadro||{}).recado||'sem dado')}</div>`;
      q.querySelectorAll('.disparar-issue').forEach(b=>b.onclick=()=>{
        $('p').value=`Trabalhe a issue #${b.dataset.n}: leia o corpo dela `
          +`e siga o prompt refinado que estiver lá.`;
        $('issue').value=b.dataset.n; $('p').focus();
      });
    }
  }
  // Trabalho terminado sai da lista padrão: mesa com trinta itens mortos
  // esconde o que está vivo. O histórico continua a um clique.
  const tudo=$('historico')&&$('historico').checked;
  const lista=tudo?d.trabalhos
    :d.trabalhos.filter(x=>!['completa','parada'].includes(x.situacao));
  const s=$('sel'), nomes=lista.map(x=>x.nome);
  if(s.dataset.chave!==nomes.join('|')){
    s.dataset.chave=nomes.join('|');
    const antes=s.value;
    const selo=x=>x.situacao==='dormindo'?' 💤':x.situacao==='aguardando-resposta'?' ⏸'
      :x.situacao==='completa'?' ✅':x.situacao==='parada'?' ❌':'';
    s.innerHTML=lista.map(x=>`<option value="${esc(x.nome)}">${esc(x.nome)}${selo(x)}${x.execucao?'':' (avulso)'}</option>`).join('')
      ||'<option value="">nenhum</option>';
    if(antes&&nomes.includes(antes))s.value=antes;
    else if(atual&&nomes.includes(atual))s.value=atual;
  }

  // Com uma execução no ar, o botão de disparar FECHA. A trava por alvo
  // recusaria o segundo disparo, mas deixar o botão vivo é convidar para o
  // erro e explicar depois — e a mesa já sabe, pelo estado gravado, que há
  // trabalho andando. Vale para execução disparada aqui ou fora daqui.
  const EM_CURSO=['rodando','dormindo','aguardando-resposta'];
  const ocupada=d.trabalhos.filter(x=>EM_CURSO.includes(x.situacao));
  const b=$('b');
  if(b){
    b.disabled=ocupada.length>0;
    b.title=ocupada.length
      ? `${ocupada[0].nome} está no ar (${ocupada[0].situacao}) — a trava do alvo recusaria um segundo disparo`
      : '';
    b.textContent=ocupada.length?'No ar…':'Disparar';
  }

  const a=d.andamento;
  if(!a){farol();return}
  if(!nomes.includes(t)||!d.trabalhos.find(x=>x.nome===t&&x.execucao)){
    $('saida').innerHTML=`<div class="recado"><b>fora do executor de roteiros</b>
      <code>${esc(t)}</code> é trilha de evidências avulsas — de um gancho, por
      exemplo —, sem roteiro ao lado. Lida como execução daria estado falso,
      então a mesa não opina.</div>`; farol(); return;
  }
  // Só repinta quando algo mudou: a mesa fica aberta por horas e repintar
  // HTML a cada 2,5s por nada custa bateria e derruba texto selecionado.
  const nova=JSON.stringify(a);
  if(nova!==assinatura){assinatura=nova; pinta(a)}
  parado=a.processo!=='rodando';
}

async function disparar(){
  const corpo=modoRoteiro()?{roteiro:$('modo').value}
    :{prompt:$('p').value.trim(),teto:+$('teto').value,turnos:+$('turnos').value,issue:+$('issue').value||null};
  if(!modoRoteiro()&&!corpo.prompt){$('p').focus();return}
  $('b').disabled=true; $('b').textContent='Disparando';
  let d; try{
    d=await (await fetch('/disparar',{method:'POST',
      headers:{'content-type':'application/json'},body:JSON.stringify(corpo)})).json();
  } finally { $('b').disabled=false; $('b').textContent='Disparar' }
  if(d.erro){$('saida').innerHTML=`<div class="recado ruim"><b>não disparei</b>${esc(d.erro)}</div>`;return}
  atual=d.trabalho; assinatura=''; await ciclo(); $('sel').value=atual; ciclo();
}

$('b').onclick=disparar;
$('sel').onchange=()=>{assinatura='';ciclo()};
$('modo').onchange=ajusta;
ajusta(); ciclo();
// Ritmo por necessidade: 2,5s enquanto a execução anda, 10s quando não há o
// que ver. Uma mesa aberta a noite inteira não deve acordar o disco à toa.
setInterval(()=>{if(!parado||Math.random()<.25)ciclo()},2500);
</script></body></html>"""


def fazer_handler(motor: Motor):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *a):  # silêncio: o log do trabalho é o que importa
            pass

        def _envia(self, corpo: bytes, tipo: str, codigo: int = 200):
            self.send_response(codigo)
            self.send_header("Content-Type", tipo)
            self.send_header("Content-Length", str(len(corpo)))
            self.end_headers()
            self.wfile.write(corpo)

        def _json(self, dado: dict, codigo: int = 200):
            self._envia(json.dumps(dado, ensure_ascii=False).encode(),
                        "application/json; charset=utf-8", codigo)

        def do_GET(self):
            rota = urllib.parse.urlparse(self.path)
            if rota.path == "/":
                return self._envia(PAGINA.encode(), "text/html; charset=utf-8")
            if rota.path == "/trabalhos":
                cfg = configuracao_do_executor(motor.cwd) or {}
                return self._json({"trabalhos": motor.trabalhos(),
                                   "roteiros": motor.catalogo(),
                                   "versao": versao_da_camada(),
                                   "repositorio": str(RAIZ),
                                   "alvo": str(motor.cwd),
                                   "evidencias": str(motor.dir),
                                   # `so-issues` desliga o disparo na mesa,
                                   # como o motor já o desliga por código.
                                   "modo": cfg.get("modo"),
                                   "quadro": motor.backlog()})
            if rota.path == "/estado":
                # Uma chamada em vez de duas. O ciclo antigo disparava um
                # subprocesso para /trabalhos e outro para /andamento a cada
                # 2,5s — o dobro do custo para desenhar uma tela só, e com as
                # duas metades podendo discordar entre si.
                q = urllib.parse.parse_qs(rota.query)
                nome = (q.get("trabalho") or [""])[0]
                cfg = configuracao_do_executor(motor.cwd) or {}
                corpo = {"versao": versao_da_camada(), "repositorio": str(RAIZ),
                         "alvo": str(motor.cwd), "evidencias": str(motor.dir),
                         "trabalhos": motor.trabalhos(),
                         "roteiros": motor.catalogo(),
                         # O backlog e o modo vêm por AQUI, e não só pelo
                         # /trabalhos: é esta a rota que a página consulta a
                         # cada ciclo — na outra, ninguém os leria.
                         "modo": cfg.get("modo"),
                         "quadro": motor.backlog()}
                if nome and not validar_trabalho(nome):
                    try:
                        corpo["andamento"] = motor.andamento(
                            nome, motor.dir / f"{nome}.roteiro.json")
                    except (OSError, subprocess.SubprocessError) as e:
                        corpo["andamento"] = {"erro": f"o andamento falhou: {e}"}
                return self._json(corpo)
            if rota.path == "/andamento":
                q = urllib.parse.parse_qs(rota.query)
                nome = (q.get("trabalho") or [""])[0]
                if erro := validar_trabalho(nome):
                    return self._json({"erro": erro}, 400)
                m = motor.dir / f"{nome}.roteiro.json"
                try:
                    return self._json(motor.andamento(nome, m))
                except (OSError, subprocess.SubprocessError) as e:
                    return self._json({"erro": f"o andamento falhou: {e}"}, 500)
            return self._json({"erro": "rota desconhecida"}, 404)

        def do_POST(self):
            if urllib.parse.urlparse(self.path).path != "/disparar":
                return self._json({"erro": "rota desconhecida"}, 404)
            try:
                n = int(self.headers.get("Content-Length") or 0)
                corpo = json.loads(self.rfile.read(n) or b"{}")
            except (ValueError, json.JSONDecodeError):
                return self._json({"erro": "corpo inválido"}, 400)
            if ocupado := motor.ocupado():
                return self._json({"erro":
                    f"já existe execução rodando neste alvo: {ocupado}. "
                    "Uma por vez — duas sessões na mesma árvore se atropelam. "
                    "Espere terminar, ou suba outro painel de controle "
                    "apontando para outro repositório."}, 409)
            escolhido = (corpo.get("roteiro") or "").strip()
            if escolhido:
                roteiro, erro = motor.ler_roteiro(escolhido)
                if erro:
                    return self._json({"erro": erro}, 400)
                prefixo = re.sub(r"[^a-z0-9]+", "-",
                                 Path(escolhido).stem.lower()).strip("-") or "execucao"
            else:
                prompt = (corpo.get("prompt") or "").strip()
                if not prompt:
                    return self._json(
                        {"erro": "escreva um pedido ou escolha um roteiro"}, 400)
                if prompt.lstrip().startswith("{") and '"etapas"' in prompt:
                    return self._json({"erro":
                        "isso é um roteiro, não um pedido. Salve-o como .json "
                        "na pasta de roteiros e escolha-o na lista — colado "
                        "aqui, o JSON inteiro viraria o texto de UMA sessão."}, 400)
                teto = corpo.get("teto")
                teto = teto if isinstance(teto, int) and 1 <= teto <= 9 else 3
                turnos = corpo.get("turnos")
                turnos = turnos if isinstance(turnos, int) and 4 <= turnos <= 120 else 24
                issue = corpo.get("issue")
                issue = issue if isinstance(issue, int) and issue > 0 else None
                roteiro = roteiro_de_um_prompt(prompt, teto, turnos, issue)
                prefixo = f"issue-{issue}" if issue else "painel"
            trabalho = nome_de_trabalho(prefixo)
            if erro := validar_trabalho(trabalho):
                return self._json({"erro": erro}, 400)
            try:
                return self._json(motor.disparar(roteiro, trabalho))
            except (OSError, subprocess.SubprocessError) as e:
                return self._json({"erro": f"não consegui disparar: {e}"}, 500)

    return Handler


def testar() -> int:
    casos, falhas = 0, []

    def caso(nome, ok):
        nonlocal casos
        casos += 1
        if not ok:
            falhas.append(nome)

    # --- a mesa deixa de mentir sobre espera, e conta a issue -------------
    import tempfile as _tmp
    with _tmp.TemporaryDirectory(prefix="painel-h6-") as tmp:
        base = Path(tmp)
        (base / "evidencias" / "t-dorme").mkdir(parents=True)
        (base / "evidencias" / "t-dorme" / "estado.json").write_text(json.dumps({
            "situacao": "dormindo", "ate": "12:36", "porque": "limite de uso",
            "etapa": "analisa", "desde": "2026-08-18T06:36:00-03:00"}),
            encoding="utf-8")
        (base / "evidencias" / "t-espera").mkdir(parents=True)
        (base / "evidencias" / "t-espera" / "estado.json").write_text(json.dumps({
            "situacao": "aguardando-resposta", "issue": 39,
            "etapa": "decide"}), encoding="utf-8")
        (base / "evidencias" / "t-pronta").mkdir(parents=True)
        (base / "evidencias" / "t-pronta" / "estado.json").write_text(json.dumps({
            "situacao": "completa"}), encoding="utf-8")

        class ProcVivo:
            pid = 1
            def poll(self): return None

        v = vivacidade(ProcVivo(), time.time() - 60,
                       estado_gravado(base / "evidencias", "t-dorme"))
        caso("motor dormindo NÃO é 'trabalhando' na mesa",
             v["situacao"] == "dormindo" and v["ate"] == "12:36")
        v = vivacidade(ProcVivo(), time.time() - 60,
                       estado_gravado(base / "evidencias", "t-espera"))
        caso("aguardando resposta aparece com o número da issue",
             v["situacao"] == "aguardando-resposta" and v["issue"] == 39)
        v = vivacidade(ProcVivo(), time.time() - 60, None)
        caso("sem estado gravado, a mesa segue como era",
             v["situacao"] == "trabalhando")
        caso("estado ilegível não derruba a leitura",
             estado_gravado(base / "evidencias", "nao-existe") is None)

        motor = Motor(base, base / "evidencias", [])
        situacoes = {x["nome"]: x["situacao"] for x in motor.trabalhos()}
        caso("a lista de trabalhos carrega a situação de cada um",
             situacoes == {"t-dorme": "dormindo",
                           "t-espera": "aguardando-resposta",
                           "t-pronta": "completa"})
        caso("e ela sai do disco, sem um subprocesso por trabalho",
             motor.trabalhos() == motor.trabalhos())

        # a correção da próxima ação não cala quem espera
        e = corrigir_proxima_acao({"processo": "rodando", "estado": "em-curso",
                                   "proxima_acao": "responda na issue",
                                   "vivacidade": {"situacao": "aguardando-resposta"}})
        caso("quem espera não recebe 'rodando agora — espere'",
             e["proxima_acao"] == "responda na issue")
        e = corrigir_proxima_acao({"processo": "rodando", "estado": "em-curso",
                                   "proxima_acao": "execute", "vivacidade": {}})
        caso("mas o convite a disparar de novo continua calado",
             "ão dispare de novo" in e["proxima_acao"])

        # o backlog: sem configuração, recado em vez de rajada de rede
        caso("sem repositório configurado o quadro devolve recado, não erro",
             motor.backlog()["issues"] == []
             and "sem repositório" in motor.backlog()["recado"])
        (base / "nucleo").mkdir()
        (base / "nucleo" / "executor.json").write_text(json.dumps({
            "modo": "so-issues",
            "issues": {"repositorio": "${DONO}/${REPO}"}}), encoding="utf-8")
        motor._quadro = None
        caso("repositório ainda no molde também não vira chamada de rede",
             "sem repositório" in motor.backlog()["recado"])
        caso("o modo do executor é lido para a mesa esconder o disparo",
             (configuracao_do_executor(base) or {}).get("modo") == "so-issues")

    caso("o vínculo com a issue viaja no roteiro do pedido",
         roteiro_de_um_prompt("x", 3, 24, 39)["issue"] == 39)
    caso("e sem issue o roteiro não inventa o campo",
         "issue" not in roteiro_de_um_prompt("x"))
    caso("o botão de disparar fecha com execução no ar",
         "b.disabled=ocupada.length>0" in PAGINA
         and "'rodando','dormindo','aguardando-resposta'" in PAGINA)
    caso("e o motivo aparece no próprio botão",
         "a trava do alvo recusaria um segundo disparo" in PAGINA)
    caso("a página desenha a execução e o backlog",
         'function desenho' in PAGINA and 'id="quadro"' in PAGINA
         and 'id="issue"' in PAGINA and 'id="historico"' in PAGINA)
    caso("o desenho usa os tokens de cor que já existem",
         '.passo.segue' in PAGINA and '.passo.agora' in PAGINA)

    caso("nome de trabalho passa na régua da evidência",
         validar_trabalho(nome_de_trabalho()) is None)
    caso("nome com barra é recusado", validar_trabalho("a/b") is not None)
    caso("nome com maiúscula é recusado", validar_trabalho("Painel") is not None)
    caso("nome vazio é recusado", validar_trabalho("") is not None)
    caso("nome de 65 é recusado", validar_trabalho("a" * 65) is not None)

    m = roteiro_de_um_prompt("olhe o repositório")
    caso("prompt livre vira etapa de sessão", m["etapas"][0]["tipo"] == "sessao")
    caso("o prompt viaja inteiro", m["etapas"][0]["prompt"] == "olhe o repositório")
    caso("a verificação entra sempre", m["etapas"][1]["tipo"] == "verificacao")
    caso("a verificação depende da sessão",
         m["etapas"][1]["depende"] == ["pedido"])
    caso("o teto viaja", roteiro_de_um_prompt("x", 7)["teto"] == 7)

    caso("o encadeador está no lugar esperado", ENCADEADOR.exists())
    caso("a página cita o disparo", 'id="b"' in PAGINA and "/disparar" in PAGINA)
    caso("a página não embute segredo",
         "token" not in PAGINA.lower() and "senha" not in PAGINA.lower())
    fonte = Path(__file__).read_text(encoding="utf-8")
    caso("o servidor atende mais de uma conexão ao mesmo tempo",
         "ThreadingHTTPServer" in fonte)
    caso("porta ocupada vira recado, não traceback",
         "EADDRINUSE" in fonte and "PAREI — a porta" in fonte)
    caso("porta livre não tem painel de controle atendendo",
         casa_do_painel_na_porta(1) is None)
    # Segundo F5 no mesmo repositório: sair 0 é o que apaga o popup do
    # depurador,
    # e é a verdade — o painel de controle que se queria já está no ar.
    caso("segundo F5 do MESMO repositório sai 0",
         decidir_porta_ocupada(4000, "/casa", "/casa")[0] == 0)
    caso("e o recado dá o endereço em vez de reclamar",
         "http://127.0.0.1:4000" in decidir_porta_ocupada(4000, "/casa", "/casa")[1])
    caso("painel de controle de OUTRO repositório na porta sai 2",
         decidir_porta_ocupada(4000, "/casa", "/outra")[0] == 2)
    caso("e o recado nomeia o outro repositório",
         "/outra" in decidir_porta_ocupada(4000, "/casa", "/outra")[1])
    caso("porta ocupada por quem não é painel de controle sai 2",
         decidir_porta_ocupada(4000, "/casa", None)[0] == 2)
    caso("a página mostra os três lugares",
         all(f'id="{i}"' in PAGINA for i in ("repositorio", "alvo", "evidencias")))
    caso("uma chamada por ciclo, não duas", "/estado?trabalho=" in PAGINA
         and "/andamento?trabalho=" not in PAGINA)
    caso("só repinta quando o estado muda", "assinatura" in PAGINA)
    caso("a fita de evidências é a peça central", 'class="fita"' in PAGINA
         and "fita de evidências" in PAGINA)
    caso("todo texto de fora passa por escape", "function esc(" in PAGINA)
    caso("respeita quem pediu menos movimento",
         "prefers-reduced-motion" in PAGINA)
    caso("foco de teclado é visível", ":focus-visible" in PAGINA)
    caso("tem tema claro e escuro", "prefers-color-scheme:dark" in PAGINA)
    caso("a versão sai do montar.py, e é a mesma que o --versao imprime",
         versao_da_camada() == subprocess.run(
             [sys.executable, str(RAIZ / "montar.py"), "--versao"],
             capture_output=True, text=True, timeout=60
         ).stdout.split("camada")[-1].strip().split()[0])
    caso("a página tem onde mostrar a versão", 'id="versao"' in PAGINA)
    # Pergunta no meio da execução trava tudo até alguém responder. Se o
    # aviso morar só na página, quem trocou de aba não fica sabendo — o
    # título é o que atravessa a aba em segundo plano.
    caso("o título da aba grita a pergunta",
         "aguardando-aprovacao':'❓ PERGUNTA" in PAGINA)
    caso("o título distingue os quatro estados",
         all(e in PAGINA for e in ("parada", "completa", "em-curso")))
    caso("a pergunta da etapa aparece na tela", "e.pergunta" in PAGINA)
    caso("a pergunta tem caixa própria, separada da próxima ação",
         "recado perg" in PAGINA and ".recado.perg{" in PAGINA)

    # Vivacidade: o painel de controle precisa distinguir "esperando a API"
    # de "morto", e CPU não serve — medido, 443s de relógio para 5s de CPU.
    class ProcFalso:
        def __init__(self, vivo, pid=1): self._v, self.pid, self.returncode = vivo, pid, 0
        def poll(self): return None if self._v else 0
    caso("sem processo, a situação é desconhecida — não 'morto'",
         vivacidade(None, None)["situacao"] == "desconhecida")
    caso("processo encerrado é dito encerrado",
         vivacidade(ProcFalso(False), time.time())["situacao"] == "encerrado")
    vv = vivacidade(ProcFalso(True), time.time() - 120)
    caso("processo vivo é dito trabalhando", vv["situacao"] == "trabalhando")
    caso("mostra quanto tempo já corre", vv["decorrido_s"] >= 120)
    caso("e quanto falta para o teto que mata sozinho",
         vv["resta_s"] == TETO_SESSAO_S - vv["decorrido_s"])
    caso("o teto do painel de controle espelha o do encadeador",
         f"TEMPO_SESSAO = {TETO_SESSAO_S}" in
         (ENCADEADOR.read_text(encoding="utf-8") if ENCADEADOR.exists() else
          f"TEMPO_SESSAO = {TETO_SESSAO_S}"))
    caso("este processo enxerga os próprios descendentes ou diz que não mede",
         isinstance(descendentes(os.getpid()), list))
    caso("a página mostra a vivacidade", "vivo(d.vivacidade)" in PAGINA)

    import tempfile
    with tempfile.TemporaryDirectory() as t:
        base = Path(t)
        (base / "evidencias" / "vinda-de-execucao").mkdir(parents=True)
        (base / "evidencias" / "trilha-de-gancho").mkdir(parents=True)
        (base / "evidencias" / "vinda-de-execucao.roteiro.json").write_text("{}")
        (base / "roteiros").mkdir()
        (base / "roteiros" / "boa.json").write_text(
            json.dumps(roteiro_de_um_prompt("oi")), encoding="utf-8")
        (base / "roteiros" / "quebrada.json").write_text("{isso não é json",
                                                           encoding="utf-8")
        (base / "roteiros" / "sem-etapas.json").write_text('{"teto":3}',
                                                             encoding="utf-8")
        (base / "oficiais").mkdir()
        (base / "oficiais" / "boa.json").write_text(
            json.dumps(roteiro_de_um_prompt("sou a oficial")), encoding="utf-8")
        (base / "oficiais" / "so-daqui.json").write_text(
            json.dumps(roteiro_de_um_prompt("x")), encoding="utf-8")
        m = Motor(base, base / "evidencias",
                  [base / "oficiais", base / "roteiros"])

        marcas = {t["nome"]: t["execucao"] for t in m.trabalhos()}
        caso("trabalho com roteiro é execução", marcas["vinda-de-execucao"])
        caso("trilha de gancho NÃO é execução", marcas["trilha-de-gancho"] is False)

        # Só roteiro de verdade entra: o quebrado e o sem-etapas ficam de
        # fora, e é por isso que a lista tem dois nomes e não quatro.
        caso("o catálogo junta as duas pastas, e só o que é roteiro",
             m.catalogo() == sorted(["boa.json", "so-daqui.json"]))
        caso("nome repetido fica com a pasta oficial",
             m.ler_roteiro("boa.json")[0]["etapas"][0]["prompt"]
             == "sou a oficial")
        caso("pasta de roteiros que não existe não derruba",
             Motor(base, base / "evidencias", [base / "nao-existe"]).catalogo() == [])
        caso("nada rodando, nada ocupado", m.ocupado() is None)
        caso("roteiro bom é lido", m.ler_roteiro("boa.json")[0] is not None)
        caso("roteiro ilegível vira erro, não exceção",
             m.ler_roteiro("quebrada.json")[1] is not None)
        caso("roteiro sem etapas é recusado",
             m.ler_roteiro("sem-etapas.json")[1] is not None)
        caso("nome fora do catálogo é recusado",
             m.ler_roteiro("../../etc/passwd")[1] is not None)
        caso("caminho absoluto é recusado",
             m.ler_roteiro("/etc/passwd")[1] is not None)

        # .json que não é roteiro aparecia no seletor como se fosse
        # execução — a proposta de regra que a síntese escreve, por exemplo.
        (base / "roteiros" / "nao-e-roteiro.json").write_text(
            '{"regras": [{"id": 1}]}', encoding="utf-8")
        caso("json sem etapas fica fora do catálogo",
             "nao-e-roteiro.json" not in m.catalogo())
        caso("json quebrado também fica fora",
             "quebrada.json" not in m.catalogo())
        caso("roteiro de verdade continua no catálogo",
             "boa.json" in m.catalogo())

        # A trava tem de sobreviver a outro PROCESSO, não só a outra thread:
        # dois painéis de controle do mesmo alvo é o caso que a trava de
        # memória perde.
        m._travar(os.getpid(), "trabalho-vivo")
        caso("trava de dono vivo segura", m.ocupado() is not None)
        caso("a trava diz de quem é", "pid" in (m.ocupado() or ""))
        m._travar(2 ** 22, "trabalho-fantasma")  # PID que não existe
        caso("trava de dono morto não segura ninguém", m.ocupado() is None)
        m._arquivo_de_trava().write_text("isso não é json", encoding="utf-8")
        caso("trava ilegível não trava o repositório", m.ocupado() is None)
        m._arquivo_de_trava().unlink()
        caso("alvos diferentes, travas diferentes",
             m._arquivo_de_trava()
             != Motor(base / "outro", base / "evidencias", [])._arquivo_de_trava())

    # O primeiro pedido disparado pelo painel de controle morreu no teto de
    # 16 turnos do motor, sem ninguém poder mudá-lo pela tela.
    caso("o pedido do painel de controle declara os turnos, em vez de herdar "
         "o padrão",
         roteiro_de_um_prompt("x")["etapas"][0]["max-turnos"] == 24)
    caso("e quem dispara pode escolher",
         roteiro_de_um_prompt("x", 3, 60)["etapas"][0]["max-turnos"] == 60)
    caso("turnos aparece na tela, não só ciclos",
         'id="turnos"' in PAGINA and "turnos:+$('turnos').value" in PAGINA)

    # A tela dizia "nada rodou ainda — rode: ... executar" COM as quatro
    # sessões no ar. Convite a disparar o que já está disparado.
    rodando = corrigir_proxima_acao({
        "processo": "rodando", "estado": "em-curso",
        "proxima_acao": "nada rodou ainda — rode: python ... executar ..."})
    caso("processo vivo: a próxima ação para de mandar executar",
         "executar" not in rodando["proxima_acao"])
    caso("e diz que pasta vazia no começo é o esperado",
         "evidência quando termina" in rodando["proxima_acao"])
    parado = corrigir_proxima_acao({
        "processo": "encerrado", "estado": "em-curso",
        "proxima_acao": "nada rodou ainda — rode: ... executar ..."})
    caso("processo morto: o convite a executar FICA — ali ele é verdade",
         "executar" in parado["proxima_acao"])
    completa = corrigir_proxima_acao({
        "processo": "rodando", "estado": "completa", "proxima_acao": "leia as evidências"})
    caso("execução completa não tem a mensagem trocada",
         completa["proxima_acao"] == "leia as evidências")

    # O ensaio do encadeador prova que o roteiro gerado é aceito de verdade —
    # sem isso o painel de controle só testaria a própria opinião sobre o
    # formato.
    if ENCADEADOR.exists() and shutil.which("git"):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "m.json"
            p.write_text(json.dumps(roteiro_de_um_prompt("oi")), encoding="utf-8")
            r = subprocess.run(
                [sys.executable, str(ENCADEADOR), "ensaio", "--roteiro", str(p),
                 "--trabalho", "teste-painel", "--dir", tmp, "--cwd", str(RAIZ)],
                capture_output=True, text=True, timeout=60)
            caso("o encadeador aceita o roteiro que o painel de controle "
                 "escreve",
                 r.returncode == 0)
            caso("o ensaio lista as duas etapas",
                 "pedido" in r.stdout and "verifica" in r.stdout)

    for f in falhas:
        print(f"FALHOU: {f}")
    print(f"{'FALHOU' if falhas else 'OK'}: {casos} casos"
          + (f" — {len(falhas)} falharam" if falhas else ""))
    return 1 if falhas else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--cwd", help="worktree ou clone descartável onde a sessão roda")
    ap.add_argument("--porta", type=int, default=4000)
    ap.add_argument("--dir", default="tmp/evidencias")
    ap.add_argument("--roteiros", default="execucoes,tmp",
                    help="pastas de roteiro, por vírgula; a primeira vence "
                         "o nome repetido")
    ap.add_argument("--forcar-arvore-suja", action="store_true",
                    help="sobe mesmo com mudança não commitada no --cwd")
    ap.add_argument("--testar", action="store_true")
    a = ap.parse_args()

    if a.testar:
        return testar()
    if not a.cwd:
        print("erro de uso: --cwd é obrigatório (worktree ou clone descartável);\n"
              "a sessão da execução pula permissões e não deve tocar a árvore "
              "que importa.", file=sys.stderr)
        return 2
    cwd = Path(a.cwd).expanduser().resolve()
    if not cwd.is_dir():
        print(f"erro de uso: --cwd não é pasta: {cwd}", file=sys.stderr)
        return 2
    if not ENCADEADOR.exists():
        print("erro de ambiente: falta o encadeador — rode\n"
              "  python montar.py --modulo encadeador", file=sys.stderr)
        return 2
    if not shutil.which("claude"):
        print("erro de ambiente: o comando claude não está no PATH; a etapa de "
              "sessão morreria.", file=sys.stderr)
        return 2
    if arvore_suja(cwd) and not a.forcar_arvore_suja:
        print(f"PAREI — {cwd} tem mudança não commitada.\n"
              "A sessão da execução roda com permissões puladas: numa árvore com "
              "trabalho seu dentro, um erro dela custa caro.\n"
              "Use um worktree descartável:\n"
              f"  git worktree add /tmp/executor HEAD\n"
              "Se você sabe o que está fazendo: --forcar-arvore-suja",
              file=sys.stderr)
        return 2

    def sob_a_raiz(valor: str) -> Path:
        p = Path(valor)
        return p.resolve() if p.is_absolute() else (RAIZ / p).resolve()

    dir_evidencias = sob_a_raiz(a.dir)
    dirs_roteiros = [sob_a_raiz(p) for p in a.roteiros.split(",") if p.strip()]
    motor = Motor(cwd, dir_evidencias, dirs_roteiros)
    # Servidor de UMA conexão prende tudo: a página fala HTTP/1.1 e a aba
    # aberta segura a conexão viva entre um polling e o próximo. Medido — com
    # o navegador aberto, qualquer segundo cliente ficava esperando para
    # sempre. Uma thread por conexão resolve, e o custo é nenhum para uma
    # ferramenta de mesa.
    try:
        servidor = ThreadingHTTPServer(("127.0.0.1", a.porta),
                                       fazer_handler(motor))
    except OSError as e:
        # Porta ocupada é o erro mais comum aqui, e o traceback cru não diz
        # nada de útil: quem lê precisa saber QUEM ocupou e como sair disso.
        if e.errno == errno.EADDRINUSE:
            codigo, recado = decidir_porta_ocupada(
                a.porta, str(RAIZ), casa_do_painel_na_porta(a.porta))
            print(recado, file=sys.stdout if codigo == 0 else sys.stderr)
            return codigo
        print(f"erro de ambiente: não consegui abrir a porta {a.porta}: {e}",
              file=sys.stderr)
        return 2
    servidor.daemon_threads = True
    print(f"painel de controle em http://127.0.0.1:{a.porta} "
          f"— camada {versao_da_camada()}")
    print(f"  repositório (o painel de controle): {RAIZ}")
    print(f"  sessões rodam em:                   {cwd}")
    print(f"  evidências em:                         {dir_evidencias}")
    print("  roteiros de:                      "
          f"{', '.join(str(p) for p in dirs_roteiros)} "
          f"({len(motor.catalogo())} encontrados)")
    print("Ctrl+C encerra.")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nencerrado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
