"""
potter_tac.py  --  Código intermediário de Três Endereços (TAC) da PotterLang.

Pipeline (não substitui o caminho AST -> C++ do potter_arduino.py):

    .potter -> LexerPotter -> ParserPotterArduino -> SemanticAnalyzerArduino
            -> GeradorTAC -> lista de Instr  (impressa como texto)

Instruções (no máximo três endereços cada):

    x = y                     cópia
    x = y op z                binária (+ - * / % == != < > <= >=)
    x = op y                  unária (- + !)
    L1:                       rótulo
    goto L1                   desvio incondicional
    if x goto L1              desvio se verdadeiro
    ifFalse x goto L1         desvio se falso
    param x                   empilha argumento
    call f, n / x = call f, n chamada com n argumentos
    return / return x         retorno de função
    print x                   LUMOS
    function f(a, b): ... end f
    halt                      fim do programa principal

Decisões:
  * && e || usam curto-circuito com desvios (um CAST no lado direito só roda se preciso),
    como no C++ gerado pelo back-end.
  * Os argumentos são todos avaliados antes dos `param`, então chamadas aninhadas não se misturam.
  * Variáveis com o mesmo nome em escopos diferentes recebem nomes únicos (x, x_1, ...)
    a partir dos símbolos resolvidos pelo semântico.

Uso:  python potter_tac.py duelo_arcano.potter
"""
import argparse
import math
import sys
from dataclasses import dataclass
from typing import Dict, List, Optional, Union

from potter_arduino import (
    ARDUINO_CONSTANTS,
    ParserPotterArduino,
    SemanticAnalyzerArduino,
    TranspileError,
    configurar_saida_utf8,
)
from potter_lang import (
    AssignNode,
    BinaryOpNode,
    CallNode,
    ExpelliarmusNode,
    FuncDeclNode,
    IdentifierNode,
    LexerPotter,
    LiteralNode,
    LumosNode,
    SemanticError,
    SortilegioNode,
    UnaryOpNode,
    VarDeclNode,
    ViraTempoNode,
)


# =====================================================================
# Representação
# =====================================================================

@dataclass(frozen=True)
class Const:
    """Endereço constante (literal)."""
    valor: object

    def __str__(self):
        if isinstance(self.valor, bool):
            return "true" if self.valor else "false"
        if isinstance(self.valor, str):
            return '"' + self.valor.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'
        return repr(self.valor)


Endereco = Union[str, Const]  # nome de variável/temporário ou constante


@dataclass
class Instr:
    op: str          # copy, bin, un, label, goto, if, iffalse, param, call, return, print, func, endfunc, halt
    a: object = None
    b: object = None
    c: object = None
    d: object = None
    linha: Optional[int] = None  # linha do fonte que originou a instrução

    def __str__(self):
        op, a, b, c, d = self.op, self.a, self.b, self.c, self.d
        if op == "label":
            return f"{a}:"
        if op == "program":
            return f"program {a}:"
        if op == "func":
            return f"function {a}({', '.join(b)}):"
        if op == "endfunc":
            return f"end {a}"
        texto = {
            "copy": lambda: f"{a} = {b}",
            "bin": lambda: f"{a} = {b} {c} {d}",
            "un": lambda: f"{a} = {b}{c}",
            "goto": lambda: f"goto {a}",
            "if": lambda: f"if {a} goto {b}",
            "iffalse": lambda: f"ifFalse {a} goto {b}",
            "param": lambda: f"param {a}",
            "call": lambda: (f"{a} = " if a else "") + f"call {b}, {c}",
            "return": lambda: "return" if a is None else f"return {a}",
            "print": lambda: f"print {a}",
            "halt": lambda: "halt",
        }[op]()
        return "    " + texto


# =====================================================================
# Gerador
# =====================================================================

class GeradorTAC:
    def __init__(self, analisador: SemanticAnalyzerArduino):
        self.codigo: List[Instr] = []
        self.n_temp = 0
        self.n_rotulo = 0
        self.nomes: Dict[int, str] = {}
        self.params_de: Dict[str, list] = {}
        usados = set(ARDUINO_CONSTANTS)
        for s in analisador.tabela_completa:
            if s.categoria == "INCANTATIO":
                usados.add(s.name)
        for s in analisador.tabela_completa:
            if s.categoria == "INCANTATIO":
                continue
            nome, i = s.name, 0
            while nome in usados:
                i += 1
                nome = f"{s.name}_{i}"
            usados.add(nome)
            self.nomes[id(s)] = nome
            func = getattr(s, "param_de", None)
            if func is not None:
                self.params_de.setdefault(func, []).append(nome)
        self.funcoes = analisador.funcoes

    # ---------------- auxiliares ----------------
    def temp(self) -> str:
        self.n_temp += 1
        return f"t{self.n_temp}"

    def rotulo(self) -> str:
        self.n_rotulo += 1
        return f"L{self.n_rotulo}"

    def emit(self, op, a=None, b=None, c=None, d=None, no=None):
        self.codigo.append(Instr(op, a, b, c, d, getattr(no, "line", None)))

    def nome(self, no, nome_fonte: str) -> str:
        simbolo = getattr(no, "simbolo", None)
        if simbolo is not None and id(simbolo) in self.nomes:
            return self.nomes[id(simbolo)]
        return nome_fonte

    # ---------------- programa ----------------
    def gerar(self, programa) -> List[Instr]:
        funcoes = [s for s in programa.body if isinstance(s, FuncDeclNode)]
        self.emit("program", programa.name)
        for s in programa.body:
            if not isinstance(s, FuncDeclNode):
                self.comando(s)
        self.emit("halt")
        for f in funcoes:
            self.funcao(f)
        return self.codigo

    def funcao(self, f: FuncDeclNode):
        self.emit("func", f.name, self.params_de.get(f.name, []), no=f)
        for s in f.body:
            self.comando(s)
        if not self.codigo or self.codigo[-1].op != "return":
            self.emit("return", no=f)
        self.emit("endfunc", f.name, no=f)

    # ---------------- comandos ----------------
    def comando(self, n):
        if isinstance(n, VarDeclNode):
            self.emit("copy", self.nome(n, n.name), self.expr(n.value_expr), no=n)
        elif isinstance(n, AssignNode):
            self.emit("copy", self.nome(n, n.name), self.expr(n.expr), no=n)
        elif isinstance(n, LumosNode):
            self.emit("print", self.expr(n.expr), no=n)
        elif isinstance(n, CallNode):
            self.chamada(n, com_retorno=False)
        elif isinstance(n, ExpelliarmusNode):
            self.emit("return", self.expr(n.expr), no=n)
        elif isinstance(n, SortilegioNode):
            cond = self.expr(n.condition)
            senao = self.rotulo() if n.else_branch is not None else None
            fim = self.rotulo()
            self.emit("iffalse", cond, senao or fim, no=n)
            for s in n.then_branch:
                self.comando(s)
            if n.else_branch is not None:
                self.emit("goto", fim)
                self.emit("label", senao)
                for s in n.else_branch:
                    self.comando(s)
            self.emit("label", fim)
        elif isinstance(n, ViraTempoNode):
            inicio, fim = self.rotulo(), self.rotulo()
            self.emit("label", inicio)
            self.emit("iffalse", self.expr(n.condition), fim, no=n)
            for s in n.body:
                self.comando(s)
            self.emit("goto", inicio)
            self.emit("label", fim)
        elif isinstance(n, FuncDeclNode):
            raise TranspileError(f"💥 [Erro TAC] Linha {n.line}: INCANTATIO '{n.name}' "
                                 f"só pode ser declarado no nível do HOGWARTS.")
        else:
            raise TranspileError(f"💥 [Erro TAC] comando não suportado: {type(n).__name__}")

    # ---------------- expressões ----------------
    def expr(self, e) -> Endereco:
        if isinstance(e, LiteralNode):
            return Const(e.value)
        if isinstance(e, IdentifierNode):
            return self.nome(e, e.name)
        if isinstance(e, UnaryOpNode):
            v = self.expr(e.operand)
            t = self.temp()
            self.emit("un", t, e.op, v, no=e)
            return t
        if isinstance(e, BinaryOpNode):
            if e.op in ("&&", "||"):
                return self.curto_circuito(e)
            l, r = self.expr(e.left), self.expr(e.right)
            t = self.temp()
            self.emit("bin", t, l, e.op, r, no=e)
            return t
        if isinstance(e, CallNode):
            return self.chamada(e, com_retorno=True)
        raise TranspileError(f"💥 [Erro TAC] expressão não suportada: {type(e).__name__}")

    def curto_circuito(self, e: BinaryOpNode) -> str:
        t = self.temp()
        fim = self.rotulo()
        self.emit("copy", t, self.expr(e.left), no=e)
        self.emit("iffalse" if e.op == "&&" else "if", t, fim, no=e)
        self.emit("copy", t, self.expr(e.right), no=e)
        self.emit("label", fim)
        return t

    def chamada(self, c: CallNode, com_retorno: bool) -> Optional[str]:
        args = [self.expr(a) for a in c.args]
        for a in args:
            self.emit("param", a, no=c)
        t = self.temp() if com_retorno else None
        self.emit("call", t, c.name, len(args), no=c)
        return t


def gerar_tac(fonte: str) -> List[Instr]:
    """Código PotterLang -> lista de instruções TAC. Erros léxicos/sintáticos/semânticos sobem."""
    tokens = LexerPotter(fonte).tokenize()
    ast = ParserPotterArduino(tokens).parse()
    analisador = SemanticAnalyzerArduino()
    analisador.analyze(ast)
    return GeradorTAC(analisador).gerar(ast)


def formatar(codigo: List[Instr]) -> str:
    return "\n".join(str(i) for i in codigo)


# =====================================================================
# Interpretador (valida a semântica do TAC nos testes)
# =====================================================================

class LimiteDePassos(Exception):
    pass


VALORES_ARDUINO = {"ALTO": 1, "BAIXO": 0, "ENTRADA": 0, "SAIDA": 1,
                   "ENTRADA_PULLUP": 2, "LED_EMBUTIDO": 13}


def _aritmetica(op, x, y):
    if op == "+":
        return x + y
    if op == "-":
        return x - y
    if op == "*":
        return x * y
    if isinstance(x, int) and isinstance(y, int):
        q = abs(x) // abs(y)
        q = q if (x >= 0) == (y >= 0) else -q   # como no C: a divisão trunca em direção a zero
        return q if op == "/" else x - y * q
    return x / y if op == "/" else math.fmod(x, y)


def _binaria(op, x, y):
    if op in ("+", "-", "*", "/", "%"):
        return _aritmetica(op, x, y)
    return {"==": x == y, "!=": x != y, "<": x < y, ">": x > y, "<=": x <= y, ">=": x >= y}[op]


def executar(codigo: List[Instr], primitivas=None, max_passos: int = 100_000) -> List[object]:
    """Executa o TAC e devolve os valores impressos por `print` (LUMOS).

    `primitivas` mapeia nome -> função Python para as primitivas Arduino; por padrão,
    digitalRead/analogRead devolvem ALTO (1) e as demais não fazem nada.
    """
    prims = {"digitalRead": lambda p: 1, "analogRead": lambda p: 0}
    if primitivas:
        prims.update(primitivas)
    rotulos = {i.a: k for k, i in enumerate(codigo) if i.op == "label"}
    funcoes = {i.a: (k, i.b) for k, i in enumerate(codigo) if i.op == "func"}
    globais: Dict[str, object] = dict(VALORES_ARDUINO)
    saida: List[object] = []
    pilha = []                    # (pc de retorno, quadro, destino do retorno)
    quadro: Optional[dict] = None  # None = programa principal (usa os globais)
    params: List[object] = []

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

    pc, passos = 0, 0
    while True:
        passos += 1
        if passos > max_passos:
            raise LimiteDePassos(f"mais de {max_passos} instruções (laço infinito?)")
        i = codigo[pc]
        pc += 1
        op = i.op
        if op in ("label", "func", "program"):
            continue
        if op == "halt":
            return saida
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
            saida.append(ler(i.a))
        elif op == "call":
            n = i.c
            args, params = params[len(params) - n:], params[:len(params) - n]
            if i.b in funcoes:
                inicio, nomes_params = funcoes[i.b]
                pilha.append((pc, quadro, i.a))
                quadro = dict(zip(nomes_params, args))
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
            raise ValueError(f"instrução desconhecida: {op}")


# =====================================================================
# CLI
# =====================================================================

def main(argv=None) -> int:
    configurar_saida_utf8()
    ap = argparse.ArgumentParser(prog="potter_tac",
                                 description="Imprime o código de três endereços (TAC) de um .potter")
    ap.add_argument("arquivo", help="arquivo .potter de entrada")
    ap.add_argument("--linhas", action="store_true", help="anota a linha do fonte de cada instrução")
    args = ap.parse_args(argv)
    with open(args.arquivo, encoding="utf-8") as f:
        fonte = f.read()
    try:
        codigo = gerar_tac(fonte)
    except (SyntaxError, SemanticError, TranspileError) as e:
        print(e, file=sys.stderr)
        return 1
    for instr in codigo:
        texto = str(instr)
        if args.linhas and instr.linha is not None:
            texto = f"{texto:<44}# linha {instr.linha}"
        print(texto)
    return 0


if __name__ == "__main__":
    sys.exit(main())
