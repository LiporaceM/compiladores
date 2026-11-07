"""
potter_api.py  --  fachada do compilador PotterLang para ferramentas (IDE, scripts).

Funções puras: recebem o código-fonte e devolvem um `Resultado` com o texto pronto
para exibir, os dados estruturados e os diagnósticos (erros/avisos) com fase,
linha e coluna. Nenhuma função daqui levanta exceção para o chamador: até um erro
interno inesperado vira um Diagnostico da fase "Interno" (importante numa demo ao vivo).
"""
import re
import traceback
from dataclasses import dataclass, field
from typing import Any, List, Optional, Tuple

from potter_arduino import (
    ARDUINO_CONSTANTS,
    BUILTIN_RETURNS,
    CPP_TYPES,
    ParserPotterArduino,
    SemanticAnalyzerArduino,
    TranspileError,
    TranspilerArduino,
)
from potter_lang import ARDUINO_BUILTINS, LexerPotter, SemanticError, TokenType

# ---------------------------------------------------------------------
# Diagnósticos
# ---------------------------------------------------------------------

_POSICAO = re.compile(r"Linha (\d+)(?:, Coluna (\d+))?")
_FASES = (
    ("[Erro Léxico]", "Léxico"),
    ("[Erro Sintático]", "Sintático"),
    ("[Erro Semântico]", "Semântico"),
    ("[Erro de Transpilação]", "Transpilação"),
)


@dataclass
class Diagnostico:
    fase: str
    mensagem: str
    linha: Optional[int] = None
    coluna: Optional[int] = None

    @classmethod
    def de_texto(cls, texto: str, fase_padrao: str) -> "Diagnostico":
        fase = next((nome for marca, nome in _FASES if marca in texto), fase_padrao)
        m = _POSICAO.search(texto)
        linha = int(m.group(1)) if m else None
        coluna = int(m.group(2)) if m and m.group(2) else None
        return cls(fase, texto.strip(), linha, coluna)

    @classmethod
    def de_excecao(cls, exc: BaseException) -> "Diagnostico":
        if isinstance(exc, (SyntaxError, SemanticError, TranspileError)):
            return cls.de_texto(str(exc), "Sintático" if isinstance(exc, SyntaxError) else "Semântico")
        detalhe = traceback.format_exception_only(type(exc), exc)[-1].strip()
        return cls("Interno", f"Erro interno do compilador: {detalhe}")

    @property
    def descricao(self) -> str:
        """Mensagem sem o prefixo '💥 [Erro X]' e sem a posição (já exibidos à parte)."""
        texto = re.sub(r"^\W*\[[^\]]*\]\s*", "", self.mensagem)
        return re.sub(r"^Linha \d+(?:, Coluna \d+)?:?\s*", "", texto)

    def __str__(self) -> str:
        return self.mensagem


@dataclass
class Resultado:
    ok: bool
    texto: str = ""
    dados: Any = None
    erros: List[Diagnostico] = field(default_factory=list)
    avisos: List[Diagnostico] = field(default_factory=list)


def _falha(exc: BaseException) -> Resultado:
    diag = Diagnostico.de_excecao(exc)
    return Resultado(False, diag.mensagem, erros=[diag])


# ---------------------------------------------------------------------
# Fases do compilador
# ---------------------------------------------------------------------

def _tokens(codigo: str):
    return LexerPotter(codigo).tokenize()


def _ast(codigo: str):
    return ParserPotterArduino(_tokens(codigo)).parse()


def obter_tokens(codigo: str) -> Resultado:
    """Análise léxica: tabela de tokens."""
    try:
        toks = _tokens(codigo)
    except Exception as e:  # noqa: BLE001 -- a IDE nunca pode cair
        return _falha(e)
    linhas = [f"{'Lin:Col':<9}{'Tipo':<17}Valor", "-" * 48]
    for t in toks:
        linhas.append(f"{f'{t.line}:{t.column}':<9}{t.type.name:<17}{t.value!r}")
    linhas.append(f"\n{len(toks)} tokens.")
    return Resultado(True, "\n".join(linhas), toks)


def obter_ast(codigo: str) -> Resultado:
    """Análise sintática: árvore de sintaxe abstrata."""
    try:
        arvore = _ast(codigo)
    except Exception as e:  # noqa: BLE001
        return _falha(e)
    return Resultado(True, arvore.print_tree().rstrip(), arvore)


def _assinaturas(arvore) -> List[str]:
    """Assinaturas C++ inferidas pelo back-end (tipos de parâmetros e retorno)."""
    t = TranspilerArduino(arvore)
    t.generate()
    linhas = []
    for nome, info in t.funcs.items():
        params = ", ".join(f"{CPP_TYPES[info.ptypes[p] or 'GALLEON']} {p}" for p in info.node.params)
        ret = CPP_TYPES[info.ret or "GALLEON"] if info.has_return else "void"
        linhas.append(f"{ret} {nome}({params})")
    return linhas


def obter_tabela_simbolos(codigo: str) -> Resultado:
    """Análise semântica: tabela de símbolos (+ assinaturas inferidas para o Arduino)."""
    try:
        arvore = _ast(codigo)
        semantico = SemanticAnalyzerArduino()
        semantico.analyze(arvore)
    except Exception as e:  # noqa: BLE001
        return _falha(e)
    avisos = [Diagnostico.de_texto(a, "Semântico") for a in semantico.avisos]
    texto = ["✅ Nenhum erro semântico encontrado.", "", semantico.print_symbol_table()]
    try:
        assinaturas = _assinaturas(arvore)
        if assinaturas:
            texto += ["", "Assinaturas inferidas pelo back-end (C++):"]
            texto += [f"  {a}" for a in assinaturas]
    except Exception as e:  # noqa: BLE001 -- erro de back-end aparece ao compilar
        texto += ["", f"(assinaturas indisponíveis: {Diagnostico.de_excecao(e).mensagem})"]
    return Resultado(True, "\n".join(texto), semantico.tabela_completa, avisos=avisos)


def gerar_ino(codigo: str) -> Resultado:
    """Pipeline completo: dados = (nome do programa, texto do .ino)."""
    try:
        arvore = _ast(codigo)
        semantico = SemanticAnalyzerArduino()
        semantico.analyze(arvore)
        t = TranspilerArduino(arvore)
        ino = t.generate()
    except Exception as e:  # noqa: BLE001
        return _falha(e)
    avisos = [Diagnostico.de_texto(a, "Semântico") for a in semantico.avisos]
    avisos += [Diagnostico.de_texto(a, "Transpilação") for a in t.warnings]
    return Resultado(True, ino, (arvore.name, ino), avisos=avisos)


# ---------------------------------------------------------------------
# Realce de sintaxe (tolerante a código com erro)
# ---------------------------------------------------------------------

PALAVRAS_CHAVE = frozenset(
    k for k, t in LexerPotter("").keywords.items()
    if not t.name.startswith("TYPE_") and t not in (TokenType.ALWAYS, TokenType.NEVER)
)
TIPOS = frozenset(k for k, t in LexerPotter("").keywords.items() if t.name.startswith("TYPE_"))
CONSTANTES = frozenset({"ALWAYS", "NEVER"} | set(ARDUINO_CONSTANTS))
PRIMITIVAS_ARDUINO = frozenset(set(ARDUINO_BUILTINS) | set(BUILTIN_RETURNS))

_REALCE = re.compile(r'''
    (?P<comentario>--[^\n]*)
  | (?P<texto>"[^"]*"?)
  | (?P<numero>\b\d+(?:\.\d+)?\b)
  | (?P<palavra>[A-Za-z_]\w*)
  | (?P<operador>~>)
''', re.VERBOSE)


def realce(codigo: str) -> List[Tuple[str, int, int]]:
    """Lista de (categoria, início, fim) em deslocamentos de caractere.

    Categorias: comentario, texto, numero, palavra_chave, tipo, constante, primitiva, operador.
    """
    trechos = []
    for m in _REALCE.finditer(codigo):
        tipo = m.lastgroup
        if tipo == "palavra":
            p = m.group()
            if p in PALAVRAS_CHAVE:
                tipo = "palavra_chave"
            elif p in TIPOS:
                tipo = "tipo"
            elif p in CONSTANTES:
                tipo = "constante"
            elif p in PRIMITIVAS_ARDUINO:
                tipo = "primitiva"
            else:
                continue
        trechos.append((tipo, m.start(), m.end()))
    return trechos
