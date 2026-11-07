"""
potter_arduino.py  --  BACK-END da PotterLang: gera o sketch .ino do Arduino.

Pipeline completo:
    Código PotterLang -> LexerPotter -> ParserPotterArduino -> SemanticAnalyzerArduino
                      -> TranspilerArduino -> arquivo .ino

Este módulo NÃO altera o potter_lang.py: ele estende as classes existentes.

Extensões de linguagem introduzidas (mínimas e retrocompatíveis):
  1. CAST pode ser usado também como EXPRESSÃO, para aproveitar o retorno:
         SORTILEGIO (CAST digitalRead(5) == BAIXO) { ... }
     (como statement, continua igual:  CAST delay(100); )
  2. Constantes nativas do Arduino, já declaradas como VOTO GALLEON:
         ALTO, BAIXO, ENTRADA, SAIDA, ENTRADA_PULLUP, LED_EMBUTIDO
     (viram HIGH, LOW, INPUT, OUTPUT, INPUT_PULLUP, LED_BUILTIN no .ino)

Convenções do transpilador:
  * VOTO/VARINHA no topo do HOGWARTS  -> variáveis globais C++ (VOTO = const)
  * INCANTATIO                        -> função C++ (tipos inferidos pelos CAST/EXPELLIARMUS)
  * comandos soltos no topo           -> setup()
  * o PRIMEIRO  VIRATEMPO (ALWAYS) {} -> corpo vira loop()
  * LUMOS(x)                          -> Serial.println(x)  (Serial.begin(9600) automático)
"""
import argparse
import os
import sys
from typing import Dict, List, Optional

from potter_lang import (
    ARDUINO_BUILTINS,
    AssignNode,
    BinaryOpNode,
    CallNode,
    ExpelliarmusNode,
    FuncDeclNode,
    IdentifierNode,
    LexerPotter,
    LiteralNode,
    LumosNode,
    ParserPotter,
    ProgramNode,
    SemanticAnalyzerPotter,
    SemanticError,
    SortilegioNode,
    Symbol,
    TokenType,
    UnaryOpNode,
    VarDeclNode,
    ViraTempoNode,
    descrever_posicao,
)

# =====================================================================
# EXTENSÕES DA LINGUAGEM
# =====================================================================

ARDUINO_CONSTANTS = {
    "ALTO": "HIGH",
    "BAIXO": "LOW",
    "ENTRADA": "INPUT",
    "SAIDA": "OUTPUT",
    "ENTRADA_PULLUP": "INPUT_PULLUP",
    "LED_EMBUTIDO": "LED_BUILTIN",
}

BUILTIN_RETURNS = {"digitalRead": "GALLEON", "analogRead": "GALLEON"}

GALLEON_MIN, GALLEON_MAX = -32768, 32767  # 'int' de 16 bits do ATmega328P


def retorna_valor(func: FuncDeclNode) -> bool:
    return any(isinstance(n, ExpelliarmusNode) for n in walk(func.body))


def sempre_retorna(stmts) -> bool:
    """True se toda execução da lista de comandos termina em EXPELLIARMUS (ou nunca termina)."""
    for s in stmts:
        if isinstance(s, ExpelliarmusNode) or is_infinite_loop(s):
            return True
        if (isinstance(s, SortilegioNode) and s.else_branch is not None
                and sempre_retorna(s.then_branch) and sempre_retorna(s.else_branch)):
            return True
    return False


class ParserPotterArduino(ParserPotter):
    """Permite `CAST feitiço(args)` dentro de expressões (sem ';')."""

    def primary(self):
        if self.match(TokenType.CAST):
            return self._call_expression(self.previous())
        return super().primary()

    def _call_expression(self, cast_tok) -> CallNode:
        name_tok = self.consume(TokenType.IDENTIFIER, "CAST precisa do nome do feitiço a lançar.")
        self.consume(TokenType.LPAREN, "Esperado '(' após nome do feitiço.")
        args = []
        if not self.check(TokenType.RPAREN):
            args.append(self.expression())
            while self.match(TokenType.COMMA):
                args.append(self.expression())
        self.consume(TokenType.RPAREN, "Esperado ')' após argumentos.")
        return self._pos(CallNode(name_tok.value, args), cast_tok)


class SemanticAnalyzerArduino(SemanticAnalyzerPotter):
    """Regras semânticas extras do back-end Arduino.

    * pré-declara as constantes do Arduino (ALTO, BAIXO, ...) e proíbe redeclará-las;
    * tipa CAST usado como expressão e rejeita feitiços/comandos sem valor de retorno;
    * exige que um INCANTATIO com EXPELLIARMUS retorne em todos os caminhos;
    * avisa sobre parâmetros nunca usados;
    * anota cada IdentifierNode/AssignNode/VarDeclNode com o Symbol resolvido
      (atributo `simbolo`), para o transpilador saber o tipo respeitando escopos.
    """

    def __init__(self):
        super().__init__()
        self.avisos: List[str] = []
        self.funcoes: Dict[str, FuncDeclNode] = {}
        for nome in ARDUINO_CONSTANTS:
            self.global_scope.declare(Symbol(nome, "GALLEON", "VOTO", 0))

    def _checar_nome(self, nome: str, onde):
        if nome in ARDUINO_CONSTANTS:
            self.error(onde, f"'{nome}' é uma constante nativa do Arduino "
                             f"({ARDUINO_CONSTANTS[nome]}) e não pode ser redeclarada.")

    def visit_VarDeclNode(self, node: VarDeclNode):
        self._checar_nome(node.name, node)
        super().visit_VarDeclNode(node)
        node.simbolo = self.current_scope.symbols[node.name]

    def visit_AssignNode(self, node: AssignNode):
        super().visit_AssignNode(node)
        node.simbolo = self.current_scope.resolve(node.name)

    def visit_FuncDeclNode(self, node: FuncDeclNode):
        self._checar_nome(node.name, node)
        for p in node.params:
            self._checar_nome(p, node)
        self.funcoes[node.name] = node
        inicio = len(self.tabela_completa)
        super().visit_FuncDeclNode(node)

        # o núcleo registra o feitiço e, logo em seguida, seus parâmetros
        params = self.tabela_completa[inicio + 1: inicio + 1 + len(node.params)]
        for s in params:
            s.param_de = node.name

        if retorna_valor(node) and not sempre_retorna(node.body):
            self.error(node,
                       f"INCANTATIO '{node.name}' conjura EXPELLIARMUS, mas nem todo caminho "
                       f"termina em EXPELLIARMUS (adicione um EXPELLIARMUS no fim ou um SENAO).")

        lidos = {id(n.simbolo) for n in walk(node.body)
                 if isinstance(n, IdentifierNode) and getattr(n, "simbolo", None) is not None}
        for s in params:
            if id(s) not in lidos:
                self.avisos.append(f"{descrever_posicao(node)}: parâmetro '{s.name}' do INCANTATIO "
                                   f"'{node.name}' nunca é usado.")

    def infer_type(self, expr):
        if isinstance(expr, CallNode):
            self.visit_CallNode(expr)
            simbolo = self.current_scope.resolve(expr.name)
            if simbolo is None:  # builtin Arduino
                if expr.name not in BUILTIN_RETURNS:
                    self.error(expr, f"Comando Arduino '{expr.name}' não devolve valor "
                                          f"e não pode ser usado em uma expressão.")
                return BUILTIN_RETURNS[expr.name]
            func = self.funcoes.get(expr.name)
            if func is not None and not retorna_valor(func):
                self.error(expr, f"INCANTATIO '{expr.name}' não conjura EXPELLIARMUS "
                                      f"(não devolve valor) e não pode ser usado em uma expressão.")
            return None  # tipo de retorno definido pelo transpilador (inferência)
        tipo = super().infer_type(expr)
        if isinstance(expr, IdentifierNode):
            expr.simbolo = self.current_scope.resolve(expr.name)
        return tipo


# =====================================================================
# TRANSPILADOR
# =====================================================================

class TranspileError(Exception):
    pass


def erro_transpilacao(onde, msg: str) -> TranspileError:
    """`onde` é o nó da AST com o problema (ou None)."""
    pos = f" {descrever_posicao(onde)}:" if onde is not None else ""
    return TranspileError(f"💥 [Erro de Transpilação]{pos} {msg}")


CPP_TYPES = {"GALLEON": "int", "SICKLE": "float", "PARCHMENT": "String", "VERITAS": "bool"}

# Nomes que não podem ser usados "crus" em C++/Arduino -> recebem sufixo _pl
RESERVED = {
    "int", "float", "double", "bool", "char", "long", "short", "unsigned", "signed", "void",
    "if", "else", "while", "for", "do", "return", "switch", "case", "break", "continue",
    "class", "struct", "new", "delete", "this", "true", "false", "const", "static",
    "namespace", "template", "typename", "auto", "register", "volatile", "default", "goto",
    "enum", "union", "typedef", "sizeof", "using", "public", "private", "protected",
    "virtual", "operator", "friend", "inline", "extern", "explicit", "mutable", "try",
    "catch", "throw", "main", "setup", "loop", "Serial", "String", "HIGH", "LOW", "INPUT",
    "OUTPUT", "INPUT_PULLUP", "LED_BUILTIN", "PI", "min", "max", "abs", "round", "sq", "pow",
    "sqrt", "map", "constrain", "byte", "word", "boolean", "random", "millis", "micros",
    "delay", "delayMicroseconds", "pinMode", "digitalWrite", "digitalRead", "analogRead",
    "analogWrite", "tone", "noTone", "F", "fmod", "NULL",
    # funções do core que um INCANTATIO homônimo redefiniria
    "init", "initVariant", "yield", "pulseIn", "pulseInLong", "shiftIn", "shiftOut",
    "attachInterrupt", "detachInterrupt", "randomSeed", "makeWord", "analogReference",
    "serialEvent", "isAlpha", "isDigit", "isSpace", "isUpperCase", "isLowerCase",
} | {f"A{i}" for i in range(8)} | set(ARDUINO_BUILTINS)


def _carregar_macros_arduino() -> frozenset:
    """Macros do pré-processador do UNO (B1, DEC, PORTB, ...): ver dados/macros_arduino_uno.txt."""
    caminho = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dados", "macros_arduino_uno.txt")
    with open(caminho, encoding="utf-8") as f:
        return frozenset(l.strip() for l in f if l.strip() and not l.startswith("#"))


RESERVED |= _carregar_macros_arduino()


def walk(node):
    """Percorre statements/expressões (sem entrar em INCANTATIO aninhado, que é proibido)."""
    if isinstance(node, list):
        for n in node:
            yield from walk(n)
        return
    if node is None:
        return
    yield node
    if isinstance(node, VarDeclNode):
        yield from walk(node.value_expr)
    elif isinstance(node, (AssignNode, LumosNode, ExpelliarmusNode)):
        yield from walk(node.expr)
    elif isinstance(node, SortilegioNode):
        yield from walk(node.condition)
        yield from walk(node.then_branch)
        yield from walk(node.else_branch)
    elif isinstance(node, ViraTempoNode):
        yield from walk(node.condition)
        yield from walk(node.body)
    elif isinstance(node, FuncDeclNode):
        yield from walk(node.body)
    elif isinstance(node, BinaryOpNode):
        yield from walk(node.left)
        yield from walk(node.right)
    elif isinstance(node, UnaryOpNode):
        yield from walk(node.operand)
    elif isinstance(node, CallNode):
        yield from walk(node.args)


def collect_locals(stmts) -> Dict[str, str]:
    """Tipos de todas as variáveis declaradas (qualquer bloco), ignorando funções."""
    env = {}
    for n in walk(stmts):
        if isinstance(n, VarDeclNode):
            env[n.name] = n.data_type
    return env


def is_infinite_loop(node) -> bool:
    return (
        isinstance(node, ViraTempoNode)
        and isinstance(node.condition, LiteralNode)
        and node.condition.type_name == "VERITAS"
        and node.condition.value is True
    )


class _FuncInfo:
    def __init__(self, node: FuncDeclNode):
        self.node = node
        self.ptypes: Dict[str, Optional[str]] = {p: None for p in node.params}
        self.ret: Optional[str] = None
        self.has_return = any(isinstance(n, ExpelliarmusNode) for n in walk(node.body))


class TranspilerArduino:
    def __init__(self, program: ProgramNode):
        self.program = program
        self.warnings: List[str] = []
        self.funcs: Dict[str, _FuncInfo] = {}
        self.global_env: Dict[str, str] = {}
        self.main_stmts: list = []
        self.cur_env: Dict[str, str] = {}

    # ------------------------------------------------------------------
    # Nomes, literais e expressões
    # ------------------------------------------------------------------
    def ident(self, name: str) -> str:
        if name in ARDUINO_CONSTANTS:
            return ARDUINO_CONSTANTS[name]
        if not name.isascii():
            # o avr-gcc 7.3 do core Arduino não aceita identificadores UTF-8: ç -> _u00e7
            return "".join(ch if ch.isascii() else f"_u{ord(ch):04x}" for ch in name)
        if name in RESERVED:
            return name + "_pl"
        return name

    @staticmethod
    def c_string(texto: str) -> str:
        escapado = (
            texto.replace("\\", "\\\\").replace('"', '\\"')
            .replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")
        )
        return f'"{escapado}"'

    def infer(self, e, env) -> Optional[str]:
        if isinstance(e, LiteralNode):
            return e.type_name
        if isinstance(e, IdentifierNode):
            if e.name in ARDUINO_CONSTANTS:
                return "GALLEON"
            simbolo = getattr(e, "simbolo", None)  # anotado pelo SemanticAnalyzerArduino
            if simbolo is not None:
                return self.tipo_do_simbolo(simbolo)
            return env.get(e.name)
        if isinstance(e, BinaryOpNode):
            if e.op in ("==", "!=", "<", ">", "<=", ">=", "&&", "||"):
                return "VERITAS"
            lt, rt = self.infer(e.left, env), self.infer(e.right, env)
            if "SICKLE" in (lt, rt):
                return "SICKLE"
            if lt is None or rt is None:
                return None
            return "GALLEON"
        if isinstance(e, UnaryOpNode):
            return "VERITAS" if e.op == "!" else self.infer(e.operand, env)
        if isinstance(e, CallNode):
            if e.name in self.funcs:
                return self.funcs[e.name].ret
            return BUILTIN_RETURNS.get(e.name)
        return None

    def tipo_do_simbolo(self, simbolo: Symbol) -> Optional[str]:
        if simbolo.tipo:
            return simbolo.tipo
        func = getattr(simbolo, "param_de", None)  # parâmetro: tipo vem da inferência
        if func in self.funcs:
            return self.funcs[func].ptypes.get(simbolo.name)
        return None

    def expr(self, e) -> str:
        if isinstance(e, LiteralNode):
            if e.type_name == "VERITAS":
                return "true" if e.value else "false"
            if e.type_name == "PARCHMENT":
                return self.c_string(e.value)
            if e.type_name == "SICKLE":
                return f"{e.value!r}f"
            if e.value > GALLEON_MAX:
                raise erro_transpilacao(
                    e, f"literal GALLEON {e.value} não cabe no 'int' de 16 bits do Arduino UNO "
                            f"({GALLEON_MIN} a {GALLEON_MAX}). Use SICKLE para valores maiores.")
            return str(e.value)
        if isinstance(e, IdentifierNode):
            return self.ident(e.name)
        if isinstance(e, BinaryOpNode):
            l, r = self.expr(e.left), self.expr(e.right)
            if e.op == "%" and "SICKLE" in (self.infer(e.left, self.cur_env), self.infer(e.right, self.cur_env)):
                return f"fmod({l}, {r})"
            return f"({l} {e.op} {r})"
        if isinstance(e, UnaryOpNode):
            op = e.operand
            if (e.op == "-" and isinstance(op, LiteralNode) and op.type_name == "GALLEON"
                    and op.value == -GALLEON_MIN):
                return f"(-{op.value})"  # -32768 é o menor int válido
            return f"({e.op}{self.expr(op)})"
        if isinstance(e, CallNode):
            return self.call(e)
        raise erro_transpilacao(e, f"Expressão não suportada: {type(e).__name__}")

    @staticmethod
    def strip_outer(texto: str) -> str:
        """Remove um par de parênteses externos redundante: ((a)) -> (a) no if/while."""
        if texto.startswith("(") and texto.endswith(")"):
            nivel = 0
            for i, ch in enumerate(texto):
                nivel += ch == "("
                nivel -= ch == ")"
                if nivel == 0 and i < len(texto) - 1:
                    return texto
            return texto[1:-1]
        return texto

    def call(self, c: CallNode) -> str:
        nome = self.ident(c.name) if c.name in self.funcs else c.name
        return f"{nome}({', '.join(self.expr(a) for a in c.args)})"

    # ------------------------------------------------------------------
    # Inferência de assinaturas (tipos de parâmetros e retorno)
    # ------------------------------------------------------------------
    def _func_env(self, info: _FuncInfo) -> Dict[str, str]:
        env = dict(self.global_env)
        env.update({p: t for p, t in info.ptypes.items() if t})
        env.update(collect_locals(info.node.body))
        return env

    def _bind_calls(self, stmts, env) -> bool:
        changed = False
        for n in walk(stmts):
            if isinstance(n, CallNode) and n.name in self.funcs:
                info = self.funcs[n.name]
                for param, arg in zip(info.node.params, n.args):
                    if info.ptypes[param] is None:
                        t = self.infer(arg, env)
                        if t:
                            info.ptypes[param] = t
                            changed = True
        return changed

    def _infer_signatures(self):
        main_env = dict(self.global_env)
        main_env.update(collect_locals(self.main_stmts))
        for _ in range(len(self.funcs) + 5):
            changed = self._bind_calls(self.main_stmts, main_env)
            for info in self.funcs.values():
                env = self._func_env(info)
                changed |= self._bind_calls(info.node.body, env)
                if info.has_return and info.ret is None:
                    for n in walk(info.node.body):
                        if isinstance(n, ExpelliarmusNode):
                            t = self.infer(n.expr, env)
                            if t:
                                info.ret = t
                                changed = True
                                break
            if not changed:
                break

    def _verificar_tipos(self, main_env: Dict[str, str]):
        """Checagem de tipos que só é possível depois de inferir parâmetros e retornos."""
        for info in self.funcs.values():
            env = self._func_env(info)
            retornos = [(self.infer(n.expr, env), n) for n in walk(info.node.body)
                        if isinstance(n, ExpelliarmusNode)]
            retornos = [(t, l) for t, l in retornos if t]
            for t, no in retornos[1:]:
                if t != retornos[0][0]:
                    raise erro_transpilacao(
                        no, f"INCANTATIO '{info.node.name}' devolve tipos diferentes: "
                               f"{retornos[0][0]} (linha {retornos[0][1].line}) e {t}.")

        blocos = [(self.main_stmts, main_env)]
        blocos += [(info.node.body, self._func_env(info)) for info in self.funcs.values()]
        for stmts, env in blocos:
            for n in walk(stmts):
                if isinstance(n, CallNode) and n.name in self.funcs:
                    info = self.funcs[n.name]
                    for param, arg in zip(info.node.params, n.args):
                        esperado, t = info.ptypes[param], self.infer(arg, env)
                        if t and esperado and t != esperado:
                            raise erro_transpilacao(
                                n, f"parâmetro '{param}' do INCANTATIO '{n.name}' é {esperado} "
                                        f"(inferido da primeira chamada), mas recebeu {t}.")
                elif isinstance(n, (VarDeclNode, AssignNode)):
                    valor = n.value_expr if isinstance(n, VarDeclNode) else n.expr
                    simbolo = getattr(n, "simbolo", None)
                    esperado = self.tipo_do_simbolo(simbolo) if simbolo else getattr(n, "data_type", None)
                    t = self.infer(valor, env)
                    if t and esperado and t != esperado:
                        raise erro_transpilacao(n, f"'{n.name}' é {esperado} mas recebeu {t}.")
                elif isinstance(n, (SortilegioNode, ViraTempoNode)):
                    t = self.infer(n.condition, env)
                    if t and t != "VERITAS":
                        nome = "SORTILEGIO" if isinstance(n, SortilegioNode) else "VIRATEMPO"
                        raise erro_transpilacao(n, f"condição do {nome} exige VERITAS, encontrado {t}.")

    # ------------------------------------------------------------------
    # Statements
    # ------------------------------------------------------------------
    def stmt(self, n, ind: int) -> List[str]:
        p = "    " * ind
        if isinstance(n, VarDeclNode):
            const = "const " if n.is_const else ""
            return [f"{p}{const}{CPP_TYPES[n.data_type]} {self.ident(n.name)} = {self.expr(n.value_expr)};"]
        if isinstance(n, AssignNode):
            return [f"{p}{self.ident(n.name)} = {self.expr(n.expr)};"]
        if isinstance(n, LumosNode):
            e = n.expr
            if isinstance(e, LiteralNode) and e.type_name == "PARCHMENT":
                return [f'{p}Serial.println(F({self.c_string(e.value)}));']
            return [f"{p}Serial.println({self.expr(e)});"]
        if isinstance(n, CallNode):
            return [f"{p}{self.call(n)};"]
        if isinstance(n, ExpelliarmusNode):
            return [f"{p}return {self.expr(n.expr)};"]
        if isinstance(n, SortilegioNode):
            out = [f"{p}if ({self.strip_outer(self.expr(n.condition))}) {{"]
            out += self.block(n.then_branch, ind + 1)
            if n.else_branch is not None:
                out.append(f"{p}}} else {{")
                out += self.block(n.else_branch, ind + 1)
            out.append(f"{p}}}")
            return out
        if isinstance(n, ViraTempoNode):
            out = [f"{p}while ({self.strip_outer(self.expr(n.condition))}) {{"]
            out += self.block(n.body, ind + 1)
            out.append(f"{p}}}")
            return out
        if isinstance(n, FuncDeclNode):
            raise erro_transpilacao(n, f"INCANTATIO '{n.name}' só pode ser declarado no nível do HOGWARTS.")
        raise erro_transpilacao(n, f"Comando não suportado: {type(n).__name__}")

    def block(self, stmts, ind: int) -> List[str]:
        out = []
        for s in stmts:
            out += self.stmt(s, ind)
        return out

    # ------------------------------------------------------------------
    # Geração final
    # ------------------------------------------------------------------
    def generate(self) -> str:
        prog = self.program

        # 1) classificar o topo do programa
        globals_decl: List[VarDeclNode] = []
        funcs: List[FuncDeclNode] = []
        pre_loop: list = []
        loop_body: Optional[list] = None
        for s in prog.body:
            if loop_body is not None:
                raise erro_transpilacao(s, "código inalcançável após o VIRATEMPO (ALWAYS) principal.")
            if isinstance(s, FuncDeclNode):
                funcs.append(s)
            elif is_infinite_loop(s):
                loop_body = s.body
            else:
                pre_loop.append(s)
                if isinstance(s, VarDeclNode):
                    globals_decl.append(s)

        for s in globals_decl:
            self.global_env[s.name] = s.data_type
        for f in funcs:
            if f.name in self.funcs:
                raise erro_transpilacao(f, f"INCANTATIO '{f.name}' declarado duas vezes.")
            self.funcs[f.name] = _FuncInfo(f)
        self.main_stmts = pre_loop + (loop_body or [])
        self._infer_signatures()
        main_env = dict(self.global_env)
        main_env.update(collect_locals(self.main_stmts))
        self._verificar_tipos(main_env)

        usa_serial = any(isinstance(n, LumosNode) for n in walk(prog.body))

        # 2) globais
        lines = [
            f"// ======================================================",
            f"// {prog.name}.ino  --  gerado pelo compilador PotterLang",
            f"// NAO EDITE: altere o .potter e compile novamente.",
            f"// ======================================================",
            "",
        ]
        deferred = {}  # VarDecl com CAST no inicializador -> atribuído em setup()
        self.cur_env = self.global_env
        for s in globals_decl:
            tem_call = any(isinstance(n, CallNode) for n in walk(s.value_expr))
            tipo = CPP_TYPES[s.data_type]
            if tem_call:
                lines.append(f"{tipo} {self.ident(s.name)};")
                deferred[id(s)] = s
            else:
                const = "const " if s.is_const else ""
                lines.append(f"{const}{tipo} {self.ident(s.name)} = {self.expr(s.value_expr)};")
        if globals_decl:
            lines.append("")

        # 3) funções
        for f in funcs:
            info = self.funcs[f.name]
            params = []
            for pn in f.params:
                t = info.ptypes[pn]
                if t is None:
                    self.warnings.append(
                        f"INCANTATIO '{f.name}': tipo do parametro '{pn}' nao inferido (nunca lancado); usando int."
                    )
                    t = "GALLEON"
                params.append(f"{CPP_TYPES[t]} {self.ident(pn)}")
            if info.has_return:
                if info.ret is None:
                    self.warnings.append(f"INCANTATIO '{f.name}': tipo de retorno nao inferido; usando int.")
                ret = CPP_TYPES[info.ret or "GALLEON"]
            else:
                ret = "void"
            self.cur_env = self._func_env(info)
            lines.append(f"// INCANTATIO {f.name}")
            lines.append(f"{ret} {self.ident(f.name)}({', '.join(params)}) {{")
            lines += self.block(f.body, 1)
            lines.append("}")
            lines.append("")

        # 4) setup()
        self.cur_env = main_env
        lines.append("void setup() {")
        if usa_serial:
            lines.append("    Serial.begin(9600);")
        for s in pre_loop:
            if isinstance(s, VarDeclNode):
                if id(s) in deferred:
                    lines.append(f"    {self.ident(s.name)} = {self.expr(s.value_expr)};")
                continue  # global já declarado e inicializado no topo
            lines += self.stmt(s, 1)
        lines.append("}")
        lines.append("")

        # 5) loop()
        lines.append("void loop() {")
        if loop_body is not None:
            lines += self.block(loop_body, 1)
        lines.append("}")
        lines.append("")
        return "\n".join(lines)


# =====================================================================
# API / CLI
# =====================================================================

def compilar(source: str):
    """Código PotterLang -> (texto do .ino, lista de avisos)."""
    tokens = LexerPotter(source).tokenize()
    ast = ParserPotterArduino(tokens).parse()
    semantico = SemanticAnalyzerArduino()
    semantico.analyze(ast)
    t = TranspilerArduino(ast)
    ino = t.generate()
    return ast.name, ino, semantico.avisos + t.warnings


def caminho_sketch(arquivo_potter: str, nome: str) -> str:
    """<pasta do fonte>/<Nome>/<Nome>.ino  (a IDE do Arduino exige a pasta com o nome do sketch)."""
    pasta = os.path.dirname(os.path.abspath(arquivo_potter))
    return os.path.join(pasta, nome, f"{nome}.ino")


def salvar_ino(destino: str, ino: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(destino)), exist_ok=True)
    with open(destino, "w", encoding="utf-8") as f:
        f.write(ino)


def configurar_saida_utf8() -> None:
    """No Windows, saída redirecionada (pipe/arquivo) usa cp1252 e quebra nos emojis das mensagens."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure") and not stream.isatty():
            stream.reconfigure(encoding="utf-8", errors="replace")


def main(argv=None) -> int:
    configurar_saida_utf8()
    ap = argparse.ArgumentParser(
        prog="potterc",
        description="Compilador PotterLang -> sketch Arduino (.ino)",
    )
    ap.add_argument("arquivo", help="arquivo .potter de entrada")
    ap.add_argument(
        "-o", "--saida",
        help="caminho do .ino. Padrao: <pasta do fonte>/<NomeDoPrograma>/<NomeDoPrograma>.ino "
             "(a IDE do Arduino exige pasta com o mesmo nome do sketch)",
    )
    ap.add_argument("--stdout", action="store_true", help="imprime o .ino em vez de gravar")
    args = ap.parse_args(argv)

    with open(args.arquivo, encoding="utf-8") as f:
        fonte = f.read()
    try:
        nome, ino, avisos = compilar(fonte)
    except (SyntaxError, SemanticError, TranspileError) as e:
        print(e, file=sys.stderr)
        return 1

    for a in avisos:
        print(f"[aviso] {a}", file=sys.stderr)
    if args.stdout:
        print(ino)
        return 0

    destino = args.saida or caminho_sketch(args.arquivo, nome)
    salvar_ino(destino, ino)
    print(f"Feitico compilado com sucesso: {destino}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
