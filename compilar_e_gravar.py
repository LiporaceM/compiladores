"""
compilar_e_gravar.py  --  pipeline completo até a placa:

    arquivo .potter -> PotterLang (front-end + back-end) -> .ino
                    -> arduino-cli compile -> arduino-cli upload (porta COM)

Uso (Windows):
    python compilar_e_gravar.py duelo_arcano.potter --porta COM3
    python compilar_e_gravar.py duelo_arcano.potter --so-compilar
    python compilar_e_gravar.py --listar-portas

Requer o arduino-cli com o core AVR instalado:
    winget install ArduinoSA.CLI
    arduino-cli core update-index
    arduino-cli core install arduino:avr
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
from typing import Callable, List, Optional, Tuple

from potter_arduino import TranspileError, caminho_sketch, compilar, configurar_saida_utf8, salvar_ino
from potter_lang import SemanticError

FQBN_PADRAO = "arduino:avr:uno"
LOCAIS_CONHECIDOS = (
    r"C:\Program Files\Arduino CLI\arduino-cli.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Programs\Arduino CLI\arduino-cli.exe"),
)

Log = Callable[[str], None]

# Evita que cada chamada ao arduino-cli abra uma janela de console (IDE no Windows).
_SEM_JANELA = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def encontrar_arduino_cli() -> Optional[str]:
    caminho = shutil.which("arduino-cli")
    if caminho:
        return caminho
    for c in LOCAIS_CONHECIDOS:
        if os.path.isfile(c):
            return c
    return None


def executar(cmd: List[str], log: Log) -> int:
    """Roda um comando repassando a saída linha a linha para `log`."""
    log("> " + " ".join(cmd))
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, encoding="utf-8", errors="replace",
                                creationflags=_SEM_JANELA)
    except OSError as e:
        log(f"[erro] não foi possível executar {cmd[0]}: {e}")
        return 1
    for linha in proc.stdout:
        log(linha.rstrip())
    return proc.wait()


def gerar_sketch(arquivo: str, log: Log) -> Optional[str]:
    """Compila o .potter e grava o .ino. Devolve a pasta do sketch ou None em caso de erro."""
    with open(arquivo, encoding="utf-8") as f:
        fonte = f.read()
    try:
        nome, ino, avisos = compilar(fonte)
    except (SyntaxError, SemanticError, TranspileError) as e:
        log(str(e))
        return None
    for a in avisos:
        log(f"[aviso] {a}")
    destino = caminho_sketch(arquivo, nome)
    salvar_ino(destino, ino)
    log(f"[1/3] PotterLang -> {destino}")
    return os.path.dirname(destino)


def compilar_e_gravar(arquivo: str, porta: Optional[str] = None, fqbn: str = FQBN_PADRAO,
                      so_compilar: bool = False, log: Log = print) -> int:
    pasta = gerar_sketch(arquivo, log)
    if pasta is None:
        return 1

    cli = encontrar_arduino_cli()
    if cli is None:
        log("[erro] arduino-cli não encontrado. Instale com: winget install ArduinoSA.CLI")
        return 1

    log(f"[2/3] arduino-cli compile ({fqbn})")
    if executar([cli, "compile", "--fqbn", fqbn, pasta], log) != 0:
        log("[erro] falha na compilação do sketch.")
        return 1

    if so_compilar:
        log("[3/3] gravação pulada (--so-compilar).")
        return 0
    if not porta:
        log("[erro] informe a porta da placa (ex.: --porta COM3). Use --listar-portas para descobrir.")
        return 1

    log(f"[3/3] arduino-cli upload -> {porta}")
    if executar([cli, "upload", "-p", porta, "--fqbn", fqbn, pasta], log) != 0:
        log("[erro] falha ao gravar na placa. Confira a porta e o cabo USB.")
        return 1
    log("Feitiço gravado na placa com sucesso!")
    return 0


def interpretar_portas(json_texto: str) -> List[Tuple[str, str]]:
    """Saída de `arduino-cli board list --format json` -> [(porta, descrição)], placas reconhecidas primeiro."""
    try:
        dados = json.loads(json_texto)
    except ValueError:
        return []
    portas = []
    for item in dados.get("detected_ports", []) if isinstance(dados, dict) else []:
        porta = item.get("port", {})
        if porta.get("protocol") != "serial" or not porta.get("address"):
            continue
        placas = [b.get("name", "") for b in item.get("matching_boards", []) if b.get("name")]
        descricao = ", ".join(placas) or porta.get("protocol_label", "Porta serial")
        portas.append((porta["address"], descricao, bool(placas)))
    portas.sort(key=lambda p: (not p[2], p[0]))
    return [(endereco, descricao) for endereco, descricao, _ in portas]


def portas_detectadas() -> List[Tuple[str, str]]:
    cli = encontrar_arduino_cli()
    if cli is None:
        return []
    try:
        r = subprocess.run([cli, "board", "list", "--format", "json"],
                           capture_output=True, text=True, timeout=30, creationflags=_SEM_JANELA)
    except (OSError, subprocess.TimeoutExpired):
        return []
    return interpretar_portas(r.stdout)


def listar_portas(log: Log = print) -> int:
    cli = encontrar_arduino_cli()
    if cli is None:
        log("[erro] arduino-cli não encontrado.")
        return 1
    return executar([cli, "board", "list"], log)


def main(argv=None) -> int:
    configurar_saida_utf8()
    ap = argparse.ArgumentParser(description="PotterLang -> .ino -> arduino-cli compile -> upload")
    ap.add_argument("arquivo", nargs="?", help="arquivo .potter")
    ap.add_argument("-p", "--porta", help="porta serial da placa, ex.: COM3")
    ap.add_argument("--fqbn", default=FQBN_PADRAO, help=f"placa alvo (padrão: {FQBN_PADRAO})")
    ap.add_argument("--so-compilar", action="store_true", help="não grava na placa")
    ap.add_argument("--listar-portas", action="store_true", help="lista placas conectadas")
    args = ap.parse_args(argv)

    if args.listar_portas:
        return listar_portas()
    if not args.arquivo:
        ap.error("informe o arquivo .potter")
    return compilar_e_gravar(args.arquivo, args.porta, args.fqbn, args.so_compilar)


if __name__ == "__main__":
    sys.exit(main())
