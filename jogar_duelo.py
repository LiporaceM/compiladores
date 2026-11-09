"""Joga o Duelo Arcano no terminal, sem Arduino.

Compila duelo_arcano.potter para TAC (potter_tac.py) e executa o programa de
verdade: o teclado faz o papel dos botoes (digitalRead) e o terminal faz o papel
dos LEDs (digitalWrite) e do Serial (LUMOS).

    python jogar_duelo.py            # joga (so Windows: usa msvcrt)
    python jogar_duelo.py --demo     # partida roteirizada, em tempo virtual

Teclas:   J1: A = Expelliarmus  S = Protego  D = Bombarda
          J2: J = Expelliarmus  K = Protego  L = Bombarda
          ESPACO = iniciar rodada        Q ou Ctrl+C = sair
"""
import sys
import time

import potter_tac
from potter_tac import Const, VALORES_ARDUINO, _binaria, gerar_tac, LimiteDePassos

# pino do botao -> tecla
TECLAS = {"a": 5, "s": 6, "d": 7, "j": 8, "k": 9, "l": 10, " ": 11}
LEDS = {2: ("\033[91m", "LED VERMELHO (dano no J1)"),
        3: ("\033[90m", "LED CINZA (empate)"),
        4: ("\033[92m", "LED VERDE (dano no J2)")}
RESET = "\033[0m"
SEGURA_S = 0.12  # quanto tempo um toque de tecla "segura" o botao apertado
FIM_DEMO_S = 16.0


class Relogio:
    """Tempo real (jogo) ou virtual (demo)."""

    def __init__(self, virtual=False):
        self.virtual, self.t = virtual, 0.0

    def agora(self):
        return self.t if self.virtual else time.monotonic()

    def esperar(self, ms):
        if self.virtual:
            self.t += ms / 1000
        else:
            time.sleep(ms / 1000)


def executar_interativo(codigo, prims, ao_imprimir):
    """Mesma maquina de potter_tac.executar, mas imprime o LUMOS na hora e roda sem limite."""
    rotulos = {i.a: k for k, i in enumerate(codigo) if i.op == "label"}
    funcoes = {i.a: (k, i.b) for k, i in enumerate(codigo) if i.op == "func"}
    globais = dict(VALORES_ARDUINO)
    pilha, quadro, params, pc = [], None, [], 0

    def ler(end):
        if isinstance(end, Const):
            return end.valor
        if quadro is not None and end in quadro:
            return quadro[end]
        return globais[end]

    def escrever(nome, valor):
        if quadro is not None and nome not in globais:
            quadro[nome] = valor
        else:
            globais[nome] = valor

    while True:
        i = codigo[pc]
        pc += 1
        op = i.op
        if op in ("label", "func", "program"):
            continue
        if op == "halt":
            return
        if op == "copy":
            escrever(i.a, ler(i.b))
        elif op == "bin":
            escrever(i.a, _binaria(i.c, ler(i.b), ler(i.d)))
        elif op == "un":
            v = ler(i.c)
            escrever(i.a, (not v) if i.b == "!" else (-v if i.b == "-" else v))
        elif op == "goto":
            pc = rotulos[i.a]
        elif op == "if":
            if ler(i.a):
                pc = rotulos[i.b]
        elif op == "iffalse":
            if not ler(i.a):
                pc = rotulos[i.b]
        elif op == "param":
            params.append(ler(i.a))
        elif op == "print":
            ao_imprimir(ler(i.a))
        elif op == "call":
            n = i.c
            args, params = params[len(params) - n:], params[:len(params) - n]
            if i.b in funcoes:
                inicio, nomes = funcoes[i.b]
                pilha.append((pc, quadro, i.a))
                quadro = dict(zip(nomes, args))
                pc = inicio + 1
            else:
                r = prims.get(i.b, lambda *a: None)(*args)
                if i.a:
                    escrever(i.a, r)
        elif op in ("return", "endfunc"):
            valor = ler(i.a) if (op == "return" and i.a is not None) else None
            pc, quadro, destino = pilha.pop()
            if destino:
                escrever(destino, valor)
        else:
            raise ValueError(f"instrucao desconhecida: {op}")


def main(argv):
    demo = "--demo" in argv
    relogio = Relogio(virtual=demo)
    soltar_em = {}          # pino -> instante em que o botao solta
    roteiro = []            # demo: (instante_s, tecla)
    leds = {}

    if demo:
        # J1 Expelliarmus x J2 Bombarda quase juntos (J1 vence); depois J1 Protego, J2 nunca aperta.
        roteiro = [(0.5, " "), (2.0, "a"), (2.1, "l"), (9.0, " "), (10.5, "s")]
    else:
        import msvcrt

    def ler_teclas():
        agora = relogio.agora()
        if demo:
            while roteiro and roteiro[0][0] <= agora:
                _, tecla = roteiro.pop(0)
                soltar_em[TECLAS[tecla]] = agora + SEGURA_S
            return
        while msvcrt.kbhit():
            c = msvcrt.getwch().lower()
            if c in ("q", "\x03"):
                raise KeyboardInterrupt
            if c in TECLAS:
                soltar_em[TECLAS[c]] = agora + SEGURA_S

    def digital_read(pino):
        if demo:
            relogio.esperar(1)   # loop ocioso sem delay: o tempo virtual precisa andar
            if relogio.agora() > FIM_DEMO_S:
                raise KeyboardInterrupt
        ler_teclas()
        return 0 if relogio.agora() < soltar_em.get(pino, 0) else 1   # pull-up: LOW = apertado

    def digital_write(pino, valor):
        if pino in LEDS and leds.get(pino) != valor:
            leds[pino] = valor
            cor, nome = LEDS[pino]
            if valor:
                print(f"{cor}   ●  {nome} aceso{RESET}", flush=True)

    def delay(ms):
        # espera em fatias para nao perder toques de tecla durante os delays do jogo
        fim = relogio.agora() + ms / 1000
        while relogio.agora() < fim:
            ler_teclas()
            relogio.esperar(min(10, (fim - relogio.agora()) * 1000))

    def imprimir(v):
        print(f"   {v}", flush=True)

    with open("duelo_arcano.potter", encoding="utf-8") as f:
        codigo = gerar_tac(f.read())

    print("Teclas  J1: A=Expelliarmus S=Protego D=Bombarda | J2: J=Expelliarmus K=Protego L=Bombarda"
          " | ESPACO=iniciar | Q=sair\n", flush=True)
    prims = {"digitalRead": digital_read, "digitalWrite": digital_write, "delay": delay}
    try:
        executar_interativo(codigo, prims, imprimir)
    except KeyboardInterrupt:
        print("\nAte a proxima, duelistas!")
    except LimiteDePassos as e:
        print(e)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main(sys.argv[1:])
