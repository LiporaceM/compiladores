import enum
from typing import List, Optional, Any, Dict

# =====================================================================
# 1. ANALISADOR LÉXICO (LEXER)
# =====================================================================

class TokenType(enum.Enum):
    # Palavras-chave do Mundo Bruxo
    HOGWARTS = "HOGWARTS"          # Declaração do Programa
    INCANTATIO = "INCANTATIO"      # Definição de Função
    CAST = "CAST"                  # Chamada de Função
    VARINHA = "VARINHA"            # Declaração de Variável
    VOTO = "VOTO"                  # Declaração de Constante
    SORTILEGIO = "SORTILEGIO"      # Se (If)
    SENAO = "SENAO"                # Senão (Else)
    VIRATEMPO = "VIRATEMPO"        # Enquanto (While)
    LUMOS = "LUMOS"                # Imprimir (Print)
    EXPELLIARMUS = "EXPELLIARMUS"  # Retorno (Return)

    # Tipos de Dados
    TYPE_GALLEON = "GALLEON"       # Inteiro
    TYPE_SICKLE = "SICKLE"         # Ponto Flutuante
    TYPE_PARCHMENT = "PARCHMENT"   # Texto (String)
    TYPE_VERITAS = "VERITAS"       # Booleano

    # Literais e Identificadores
    IDENTIFIER = "IDENTIFIER"
    INT_LITERAL = "INT_LITERAL"
    FLOAT_LITERAL = "FLOAT_LITERAL"
    STRING_LITERAL = "STRING_LITERAL"
    ALWAYS = "ALWAYS"              # Booleano Verdadeiro
    NEVER = "NEVER"                # Booleano Falso

    # Operadores e Delimitadores
    WAND_ASSIGN = "~>"             # Atribuição
    PLUS = "+"
    MINUS = "-"
    STAR_MULT = "*"
    SLASH = "/"
    EQ = "=="
    NEQ = "!="
    LT = "<"
    GT = ">"
    LTE = "<="
    GTE = ">="
    MOD = "%"
    AND = "&&"
    OR = "||"
    NOT = "!"

    LPAREN = "("
    RPAREN = ")"
    LBRACE = "{"
    RBRACE = "}"
    COMMA = ","
    SEMICOLON = ";"
    EOF = "EOF"


class Token:
    def __init__(self, type_: TokenType, value: Any, line: int, column: int):
        self.type = type_
        self.value = value
        self.line = line
        self.column = column

    def __repr__(self):
        return f"⚡ Token({self.type.name:<16}, Value='{self.value}', Line={self.line}:{self.column})"


class LexerPotter:
    def __init__(self, source_code: str):
        self.source = source_code
        self.pos = 0
        self.line = 1
        self.col = 1
        self.tokens: List[Token] = []

        self.keywords = {
            "HOGWARTS": TokenType.HOGWARTS,
            "INCANTATIO": TokenType.INCANTATIO,
            "CAST": TokenType.CAST,
            "VARINHA": TokenType.VARINHA,
            "VOTO": TokenType.VOTO,
            "SORTILEGIO": TokenType.SORTILEGIO,
            "SENAO": TokenType.SENAO,
            "VIRATEMPO": TokenType.VIRATEMPO,
            "LUMOS": TokenType.LUMOS,
            "EXPELLIARMUS": TokenType.EXPELLIARMUS,
            "GALLEON": TokenType.TYPE_GALLEON,
            "SICKLE": TokenType.TYPE_SICKLE,
            "PARCHMENT": TokenType.TYPE_PARCHMENT,
            "VERITAS": TokenType.TYPE_VERITAS,
            "ALWAYS": TokenType.ALWAYS,
            "NEVER": TokenType.NEVER,
        }

    def error(self, msg: str):
        raise SyntaxError(f"💥 [Erro Léxico] Linha {self.line}, Coluna {self.col}: {msg}")

    def peek(self, offset: int = 1) -> str:
        if self.pos + offset < len(self.source):
            return self.source[self.pos + offset]
        return ''

    def advance(self, step: int = 1):
        self.pos += step
        self.col += step

    def tokenize(self) -> List[Token]:
        while self.pos < len(self.source):
            char = self.source[self.pos]

            if char == '\n':
                self.line += 1
                self.col = 1
                self.pos += 1
                continue
            elif char.isspace():
                self.pos += 1
                self.col += 1
                continue

            # Comentários de linha: tudo até a quebra de linha é descartado.
            if char == '-' and self.peek() == '-':
                while self.pos < len(self.source) and self.source[self.pos] != '\n':
                    self.pos += 1
                    self.col += 1
                continue

            # Operador de Atribuição ~>
            if char == '~' and self.peek() == '>':
                self.tokens.append(Token(TokenType.WAND_ASSIGN, "~>", self.line, self.col))
                self.advance(2)
                continue

            # Operadores Relacionais, Lógicos e Aritméticos
            if char == '=' and self.peek() == '=':
                self.tokens.append(Token(TokenType.EQ, "==", self.line, self.col))
                self.advance(2)
                continue
            elif char == '=':
                self.error("Atribuição simples inválida; use '~>'.")
            elif char == '!' and self.peek() == '=':
                self.tokens.append(Token(TokenType.NEQ, "!=", self.line, self.col))
                self.advance(2)
                continue
            elif char == '!':
                self.tokens.append(Token(TokenType.NOT, "!", self.line, self.col))
                self.advance()
                continue
            elif char == '<' and self.peek() == '=':
                self.tokens.append(Token(TokenType.LTE, "<=", self.line, self.col))
                self.advance(2)
                continue
            elif char == '<':
                self.tokens.append(Token(TokenType.LT, "<", self.line, self.col))
                self.advance()
                continue
            elif char == '>' and self.peek() == '=':
                self.tokens.append(Token(TokenType.GTE, ">=", self.line, self.col))
                self.advance(2)
                continue
            elif char == '>':
                self.tokens.append(Token(TokenType.GT, ">", self.line, self.col))
                self.advance()
                continue
            elif char == '&' and self.peek() == '&':
                self.tokens.append(Token(TokenType.AND, "&&", self.line, self.col))
                self.advance(2)
                continue
            elif char == '|' and self.peek() == '|':
                self.tokens.append(Token(TokenType.OR, "||", self.line, self.col))
                self.advance(2)
                continue
            elif char in '&|':
                self.error("Operador lógico incompleto; use '&&' ou '||'.")
            elif char == '+':
                self.tokens.append(Token(TokenType.PLUS, "+", self.line, self.col))
                self.advance()
                continue
            elif char == '-':
                self.tokens.append(Token(TokenType.MINUS, "-", self.line, self.col))
                self.advance()
                continue
            elif char == '*':
                self.tokens.append(Token(TokenType.STAR_MULT, "*", self.line, self.col))
                self.advance()
                continue
            elif char == '/':
                self.tokens.append(Token(TokenType.SLASH, "/", self.line, self.col))
                self.advance()
                continue
            elif char == '%':
                self.tokens.append(Token(TokenType.MOD, "%", self.line, self.col))
                self.advance()
                continue

            # Delimitadores
            if char == '(':
                self.tokens.append(Token(TokenType.LPAREN, "(", self.line, self.col))
                self.advance()
                continue
            elif char == ')':
                self.tokens.append(Token(TokenType.RPAREN, ")", self.line, self.col))
                self.advance()
                continue
            elif char == '{':
                self.tokens.append(Token(TokenType.LBRACE, "{", self.line, self.col))
                self.advance()
                continue
            elif char == '}':
                self.tokens.append(Token(TokenType.RBRACE, "}", self.line, self.col))
                self.advance()
                continue
            elif char == ',':
                self.tokens.append(Token(TokenType.COMMA, ",", self.line, self.col))
                self.advance()
                continue
            elif char == ';':
                self.tokens.append(Token(TokenType.SEMICOLON, ";", self.line, self.col))
                self.advance()
                continue

            # Strings
            if char == '"':
                self.advance()
                start_col = self.col
                val = ""
                while self.pos < len(self.source) and self.source[self.pos] != '"':
                    if self.source[self.pos] == '\n':
                        self.line += 1
                        self.col = 1
                    val += self.source[self.pos]
                    self.pos += 1
                    self.col += 1
                if self.pos >= len(self.source):
                    self.error("Encantamento de texto incompleto (faltou fechar aspas).")
                self.advance()
                self.tokens.append(Token(TokenType.STRING_LITERAL, val, self.line, start_col))
                continue

            # Números (Galleons e Sickles)
            if char.isdigit():
                start_col = self.col
                num_str = ""
                is_float = False
                while self.pos < len(self.source) and (self.source[self.pos].isdigit() or self.source[self.pos] == '.'):
                    if self.source[self.pos] == '.':
                        if is_float:
                            self.error("Número bruxo malformado com múltiplos pontos.")
                        is_float = True
                    num_str += self.source[self.pos]
                    self.pos += 1
                    self.col += 1
                if is_float:
                    self.tokens.append(Token(TokenType.FLOAT_LITERAL, float(num_str), self.line, start_col))
                else:
                    self.tokens.append(Token(TokenType.INT_LITERAL, int(num_str), self.line, start_col))
                continue

            # Identificadores e Palavras Reservadas
            if char.isalpha() or char == '_':
                start_col = self.col
                ident = ""
                while self.pos < len(self.source) and (self.source[self.pos].isalnum() or self.source[self.pos] == '_'):
                    ident += self.source[self.pos]
                    self.pos += 1
                    self.col += 1

                tok_type = self.keywords.get(ident, TokenType.IDENTIFIER)
                self.tokens.append(Token(tok_type, ident, self.line, start_col))
                continue

            self.error(f"Símbolo das trevas não reconhecido: '{char}'")

        self.tokens.append(Token(TokenType.EOF, "EOF", self.line, self.col))
        return self.tokens


# =====================================================================
# 2. ÁRVORE DE SINTAXE ABSTRATA (AST)
# =====================================================================

class ASTNode:
    line: int = None

    def print_tree(self, indent: str = "", is_last: bool = True) -> str:
        raise NotImplementedError


class ProgramNode(ASTNode):
    def __init__(self, name: str, body: List[ASTNode], line: int = None):
        self.name = name
        self.body = body
        self.line = line

    def print_tree(self, indent: str = "", is_last: bool = True) -> str:
        marker = "└── " if is_last else "├── "
        res = f"{indent}{marker}🏰 HOGWARTS ({self.name})\n"
        new_indent = indent + ("    " if is_last else "│   ")
        for i, stmt in enumerate(self.body):
            res += stmt.print_tree(new_indent, i == len(self.body) - 1)
        return res


class VarDeclNode(ASTNode):
    def __init__(self, is_const: bool, data_type: str, name: str, value_expr: ASTNode, line: int = None):
        self.is_const = is_const
        self.data_type = data_type
        self.name = name
        self.value_expr = value_expr
        self.line = line

    def print_tree(self, indent: str = "", is_last: bool = True) -> str:
        marker = "└── " if is_last else "├── "
        kind = "📜 VOTO (Const)" if self.is_const else "🪄 VARINHA (Var)"
        res = f"{indent}{marker}{kind}: {self.name} [{self.data_type}]\n"
        new_indent = indent + ("    " if is_last else "│   ")
        res += self.value_expr.print_tree(new_indent, True)
        return res


class AssignNode(ASTNode):
    def __init__(self, name: str, expr: ASTNode, line: int = None):
        self.name = name
        self.expr = expr
        self.line = line

    def print_tree(self, indent: str = "", is_last: bool = True) -> str:
        marker = "└── " if is_last else "├── "
        res = f"{indent}{marker}⚡ WAND_ASSIGN (~>): {self.name}\n"
        new_indent = indent + ("    " if is_last else "│   ")
        res += self.expr.print_tree(new_indent, True)
        return res


class LumosNode(ASTNode):
    """LUMOS(expr); -- Impressão no console"""
    def __init__(self, expr: ASTNode, line: int = None):
        self.expr = expr
        self.line = line

    def print_tree(self, indent: str = "", is_last: bool = True) -> str:
        marker = "└── " if is_last else "├── "
        res = f"{indent}{marker}💡 LUMOS (Print)\n"
        new_indent = indent + ("    " if is_last else "│   ")
        res += self.expr.print_tree(new_indent, True)
        return res


class SortilegioNode(ASTNode):
    """SORTILEGIO (cond) { ... } SENAO { ... } -- Condicional"""
    def __init__(self, condition: ASTNode, then_branch: List[ASTNode],
                 else_branch: Optional[List[ASTNode]] = None, line: int = None):
        self.condition = condition
        self.then_branch = then_branch
        self.else_branch = else_branch
        self.line = line

    def print_tree(self, indent: str = "", is_last: bool = True) -> str:
        marker = "└── " if is_last else "├── "
        res = f"{indent}{marker}🔮 SORTILEGIO (If)\n"
        new_indent = indent + ("    " if is_last else "│   ")
        res += f"{new_indent}├── ❓ Condição:\n"
        res += self.condition.print_tree(new_indent + "│   ", True)

        res += f"{new_indent}├── ✨ Ramo Verdadeiro:\n"
        for i, stmt in enumerate(self.then_branch):
            res += stmt.print_tree(new_indent + "│   ", i == len(self.then_branch) - 1)

        if self.else_branch:
            res += f"{new_indent}└── 🐍 Ramo SENAO:\n"
            for i, stmt in enumerate(self.else_branch):
                res += stmt.print_tree(new_indent + "    ", i == len(self.else_branch) - 1)
        return res


class ViraTempoNode(ASTNode):
    """VIRATEMPO (cond) { ... } -- Laço de Repetição"""
    def __init__(self, condition: ASTNode, body: List[ASTNode], line: int = None):
        self.condition = condition
        self.body = body
        self.line = line

    def print_tree(self, indent: str = "", is_last: bool = True) -> str:
        marker = "└── " if is_last else "├── "
        res = f"{indent}{marker}⏳ VIRATEMPO (While)\n"
        new_indent = indent + ("    " if is_last else "│   ")
        res += f"{new_indent}├── ❓ Condição:\n"
        res += self.condition.print_tree(new_indent + "│   ", True)
        res += f"{new_indent}└── 🔁 Corpo do Laço:\n"
        for i, stmt in enumerate(self.body):
            res += stmt.print_tree(new_indent + "    ", i == len(self.body) - 1)
        return res


class FuncDeclNode(ASTNode):
    """INCANTATIO nome(params) { ... } -- Declaração de Feitiço"""
    def __init__(self, name: str, params: List[str], body: List[ASTNode], line: int = None):
        self.name = name
        self.params = params
        self.body = body
        self.line = line

    def print_tree(self, indent: str = "", is_last: bool = True) -> str:
        marker = "└── " if is_last else "├── "
        res = f"{indent}{marker}🧹 INCANTATIO (Feitiço): {self.name}({', '.join(self.params)})\n"
        new_indent = indent + ("    " if is_last else "│   ")
        for i, stmt in enumerate(self.body):
            res += stmt.print_tree(new_indent, i == len(self.body) - 1)
        return res


class CallNode(ASTNode):
    """CAST nome(args); -- Lançamento de Feitiço"""
    def __init__(self, name: str, args: List[ASTNode], line: int = None):
        self.name = name
        self.args = args
        self.line = line

    def print_tree(self, indent: str = "", is_last: bool = True) -> str:
        marker = "└── " if is_last else "├── "
        res = f"{indent}{marker}🪄 CAST (Lançar): {self.name}\n"
        new_indent = indent + ("    " if is_last else "│   ")
        for i, arg in enumerate(self.args):
            res += arg.print_tree(new_indent, i == len(self.args) - 1)
        return res


class ExpelliarmusNode(ASTNode):
    """EXPELLIARMUS expr; -- Retorno"""
    def __init__(self, expr: ASTNode, line: int = None):
        self.expr = expr
        self.line = line

    def print_tree(self, indent: str = "", is_last: bool = True) -> str:
        marker = "└── " if is_last else "├── "
        res = f"{indent}{marker}💥 EXPELLIARMUS (Return)\n"
        new_indent = indent + ("    " if is_last else "│   ")
        res += self.expr.print_tree(new_indent, True)
        return res


class BinaryOpNode(ASTNode):
    def __init__(self, left: ASTNode, op: str, right: ASTNode, line: int = None):
        self.left = left
        self.op = op
        self.right = right
        self.line = line

    def print_tree(self, indent: str = "", is_last: bool = True) -> str:
        marker = "└── " if is_last else "├── "
        res = f"{indent}{marker}⚔️ BINARY_OP ({self.op})\n"
        new_indent = indent + ("    " if is_last else "│   ")
        res += self.left.print_tree(new_indent, False)
        res += self.right.print_tree(new_indent, True)
        return res


class UnaryOpNode(ASTNode):
    def __init__(self, op: str, operand: ASTNode, line: int = None):
        self.op = op
        self.operand = operand
        self.line = line

    def print_tree(self, indent: str = "", is_last: bool = True) -> str:
        marker = "└── " if is_last else "├── "
        res = f"{indent}{marker}⚔️ UNARY_OP ({self.op})\n"
        new_indent = indent + ("    " if is_last else "│   ")
        res += self.operand.print_tree(new_indent, True)
        return res


class LiteralNode(ASTNode):
    def __init__(self, value: Any, type_name: str, line: int = None):
        self.value = value
        self.type_name = type_name
        self.line = line

    def print_tree(self, indent: str = "", is_last: bool = True) -> str:
        marker = "└── " if is_last else "├── "
        return f"{indent}{marker}💎 LITERAL [{self.type_name}]: {repr(self.value)}\n"


class IdentifierNode(ASTNode):
    def __init__(self, name: str, line: int = None):
        self.name = name
        self.line = line

    def print_tree(self, indent: str = "", is_last: bool = True) -> str:
        marker = "└── " if is_last else "├── "
        return f"{indent}{marker}🏷️ IDENTIFIER: {self.name}\n"


# =====================================================================
# 3. ANALISADOR SINTÁTICO (PARSER LL(1))
# =====================================================================

class ParserPotter:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.current = 0

    def error(self, message: str):
        tok = self.peek()
        raise SyntaxError(f"💥 [Erro Sintático] Linha {tok.line}, Coluna {tok.column} próximo a '{tok.value}': {message}")

    def peek(self) -> Token:
        return self.tokens[self.current]

    def previous(self) -> Token:
        return self.tokens[self.current - 1]

    def is_at_end(self) -> bool:
        return self.peek().type == TokenType.EOF

    def advance(self) -> Token:
        token = self.peek()
        if not self.is_at_end():
            self.current += 1
        return token

    def check(self, type_: TokenType) -> bool:
        return self.peek().type == type_

    def match(self, *types: TokenType) -> bool:
        for t in types:
            if self.check(t):
                self.advance()
                return True
        return False

    def consume(self, type_: TokenType, message: str) -> Token:
        if self.check(type_):
            return self.advance()
        self.error(message)

    def parse(self) -> ProgramNode:
        hogwarts_tok = self.consume(TokenType.HOGWARTS, "Programa deve ser iniciado com 'HOGWARTS'.")
        name_tok = self.consume(TokenType.IDENTIFIER, "Esperado nome para o castelo/programa HOGWARTS.")
        self.consume(TokenType.LBRACE, "Esperado '{' para iniciar os portões de Hogwarts.")

        body = []
        while not self.check(TokenType.RBRACE) and not self.is_at_end():
            body.append(self.statement())

        self.consume(TokenType.RBRACE, "Esperado '}' para fechar os portões de Hogwarts.")
        self.consume(TokenType.EOF, "Esperado fim do programa.")
        return ProgramNode(name_tok.value, body, line=hogwarts_tok.line)

    def statement(self) -> ASTNode:
        if self.match(TokenType.VARINHA, TokenType.VOTO):
            return self.var_declaration()
        elif self.match(TokenType.LUMOS):
            return self.lumos_statement()
        elif self.match(TokenType.SORTILEGIO):
            return self.sortilegio_statement()
        elif self.match(TokenType.VIRATEMPO):
            return self.viratempo_statement()
        elif self.match(TokenType.INCANTATIO):
            return self.incantatio_statement()
        elif self.match(TokenType.CAST):
            return self.cast_statement()
        elif self.match(TokenType.EXPELLIARMUS):
            return self.expelliarmus_statement()
        elif self.check(TokenType.IDENTIFIER):
            return self.assignment_statement()
        else:
            self.error("Comando bruxo desconhecido.")

    def var_declaration(self) -> VarDeclNode:
        decl_tok = self.previous()
        is_const = (decl_tok.type == TokenType.VOTO)

        if not self.match(TokenType.TYPE_GALLEON, TokenType.TYPE_SICKLE,
                          TokenType.TYPE_PARCHMENT, TokenType.TYPE_VERITAS):
            self.error("Esperado tipo bruxo (GALLEON, SICKLE, PARCHMENT, VERITAS).")
        data_type = self.previous().value

        name_tok = self.consume(TokenType.IDENTIFIER, "Variável ou Voto precisa de um nome.")
        self.consume(TokenType.WAND_ASSIGN, "Esperado atribuição com aceno de varinha '~>'.")
        expr = self.expression()
        self.consume(TokenType.SEMICOLON, "Declarações mágicas devem terminar com ';'.")

        return VarDeclNode(is_const, data_type, name_tok.value, expr, line=decl_tok.line)

    def assignment_statement(self) -> AssignNode:
        name_tok = self.consume(TokenType.IDENTIFIER, "Esperado nome do identificador.")
        self.consume(TokenType.WAND_ASSIGN, "Esperado aceno de varinha '~>'.")
        expr = self.expression()
        self.consume(TokenType.SEMICOLON, "Atribuição deve terminar com ';'.")
        return AssignNode(name_tok.value, expr, line=name_tok.line)

    def lumos_statement(self) -> LumosNode:
        lumos_tok = self.previous()
        self.consume(TokenType.LPAREN, "Esperado '(' após LUMOS.")
        expr = self.expression()
        self.consume(TokenType.RPAREN, "Esperado ')' após expressão do LUMOS.")
        self.consume(TokenType.SEMICOLON, "LUMOS precisa terminar com ';'.")
        return LumosNode(expr, line=lumos_tok.line)

    def sortilegio_statement(self) -> SortilegioNode:
        sort_tok = self.previous()
        self.consume(TokenType.LPAREN, "Esperado '(' após SORTILEGIO.")
        cond = self.expression()
        self.consume(TokenType.RPAREN, "Esperado ')' após condição.")

        self.consume(TokenType.LBRACE, "Esperado '{' para o bloco SORTILEGIO.")
        then_branch = []
        while not self.check(TokenType.RBRACE) and not self.is_at_end():
            then_branch.append(self.statement())
        self.consume(TokenType.RBRACE, "Esperado '}' para fechar SORTILEGIO.")

        else_branch = None
        if self.match(TokenType.SENAO):
            self.consume(TokenType.LBRACE, "Esperado '{' para o bloco SENAO.")
            else_branch = []
            while not self.check(TokenType.RBRACE) and not self.is_at_end():
                else_branch.append(self.statement())
            self.consume(TokenType.RBRACE, "Esperado '}' para fechar SENAO.")

        return SortilegioNode(cond, then_branch, else_branch, line=sort_tok.line)

    def viratempo_statement(self) -> ViraTempoNode:
        vira_tok = self.previous()
        self.consume(TokenType.LPAREN, "Esperado '(' após VIRATEMPO.")
        cond = self.expression()
        self.consume(TokenType.RPAREN, "Esperado ')' após condição.")

        self.consume(TokenType.LBRACE, "Esperado '{' para o bloco VIRATEMPO.")
        body = []
        while not self.check(TokenType.RBRACE) and not self.is_at_end():
            body.append(self.statement())
        self.consume(TokenType.RBRACE, "Esperado '}' para fechar VIRATEMPO.")

        return ViraTempoNode(cond, body, line=vira_tok.line)

    def incantatio_statement(self) -> FuncDeclNode:
        inc_tok = self.previous()
        name_tok = self.consume(TokenType.IDENTIFIER, "INCANTATIO precisa de um nome para o feitiço.")
        self.consume(TokenType.LPAREN, "Esperado '(' após nome do feitiço.")
        params = []
        if not self.check(TokenType.RPAREN):
            params.append(self.consume(TokenType.IDENTIFIER, "Esperado nome do parâmetro.").value)
            while self.match(TokenType.COMMA):
                params.append(self.consume(TokenType.IDENTIFIER, "Esperado nome do parâmetro.").value)
        self.consume(TokenType.RPAREN, "Esperado ')' após parâmetros.")

        self.consume(TokenType.LBRACE, "Esperado '{' para corpo do feitiço.")
        body = []
        while not self.check(TokenType.RBRACE) and not self.is_at_end():
            body.append(self.statement())
        self.consume(TokenType.RBRACE, "Esperado '}' para fechar o feitiço.")

        return FuncDeclNode(name_tok.value, params, body, line=inc_tok.line)

    def cast_statement(self) -> CallNode:
        cast_tok = self.previous()
        name_tok = self.consume(TokenType.IDENTIFIER, "CAST precisa do nome do feitiço a lançar.")
        self.consume(TokenType.LPAREN, "Esperado '(' após nome do feitiço.")
        args = []
        if not self.check(TokenType.RPAREN):
            args.append(self.expression())
            while self.match(TokenType.COMMA):
                args.append(self.expression())
        self.consume(TokenType.RPAREN, "Esperado ')' após argumentos.")
        self.consume(TokenType.SEMICOLON, "Comando CAST precisa terminar com ';'.")
        return CallNode(name_tok.value, args, line=cast_tok.line)

    def expelliarmus_statement(self) -> ExpelliarmusNode:
        exp_tok = self.previous()
        expr = self.expression()
        self.consume(TokenType.SEMICOLON, "EXPELLIARMUS precisa terminar com ';'.")
        return ExpelliarmusNode(expr, line=exp_tok.line)

    def expression(self) -> ASTNode:
        # A ordem dos métodos representa a precedência dos operadores.
        return self.logical_or()

    def logical_or(self) -> ASTNode:
        expr = self.logical_and()
        while self.match(TokenType.OR):
            op_tok = self.previous()
            expr = BinaryOpNode(expr, op_tok.value, self.logical_and(), line=op_tok.line)
        return expr

    def logical_and(self) -> ASTNode:
        expr = self.equality()
        while self.match(TokenType.AND):
            op_tok = self.previous()
            expr = BinaryOpNode(expr, op_tok.value, self.equality(), line=op_tok.line)
        return expr

    def equality(self) -> ASTNode:
        expr = self.relational()
        while self.match(TokenType.EQ, TokenType.NEQ):
            op_tok = self.previous()
            right = self.relational()
            expr = BinaryOpNode(expr, op_tok.value, right, line=op_tok.line)
        return expr

    def relational(self) -> ASTNode:
        expr = self.additive()
        while self.match(TokenType.LT, TokenType.GT, TokenType.LTE, TokenType.GTE):
            op_tok = self.previous()
            right = self.additive()
            expr = BinaryOpNode(expr, op_tok.value, right, line=op_tok.line)
        return expr

    def additive(self) -> ASTNode:
        expr = self.multiplicative()
        while self.match(TokenType.PLUS, TokenType.MINUS):
            op_tok = self.previous()
            right = self.multiplicative()
            expr = BinaryOpNode(expr, op_tok.value, right, line=op_tok.line)
        return expr

    def multiplicative(self) -> ASTNode:
        expr = self.unary()
        while self.match(TokenType.STAR_MULT, TokenType.SLASH, TokenType.MOD):
            op_tok = self.previous()
            right = self.unary()
            expr = BinaryOpNode(expr, op_tok.value, right, line=op_tok.line)
        return expr

    def unary(self) -> ASTNode:
        if self.match(TokenType.NOT, TokenType.MINUS, TokenType.PLUS):
            op_tok = self.previous()
            return UnaryOpNode(op_tok.value, self.unary(), line=op_tok.line)
        return self.primary()

    def primary(self) -> ASTNode:
        if self.match(TokenType.INT_LITERAL):
            tok = self.previous()
            return LiteralNode(tok.value, "GALLEON", line=tok.line)
        elif self.match(TokenType.FLOAT_LITERAL):
            tok = self.previous()
            return LiteralNode(tok.value, "SICKLE", line=tok.line)
        elif self.match(TokenType.STRING_LITERAL):
            tok = self.previous()
            return LiteralNode(tok.value, "PARCHMENT", line=tok.line)
        elif self.match(TokenType.ALWAYS, TokenType.NEVER):
            tok = self.previous()
            return LiteralNode(tok.type == TokenType.ALWAYS, "VERITAS", line=tok.line)
        elif self.match(TokenType.IDENTIFIER):
            tok = self.previous()
            return IdentifierNode(tok.value, line=tok.line)
        elif self.match(TokenType.LPAREN):
            expr = self.expression()
            self.consume(TokenType.RPAREN, "Esperado ')' após expressão.")
            return expr
        else:
            self.error("Expressão mágica inválida.")


# =====================================================================
# 4. ANALISADOR SEMÂNTICO E TABELA DE SÍMBOLOS
# =====================================================================

TIPOS_NUMERICOS = {"GALLEON", "SICKLE"}
OPS_COMPARACAO = {"==", "!=", "<", ">", "<=", ">="}
OPS_ARITMETICOS = {"+", "-", "*", "/", "%"}
OPS_LOGICOS = {"&&", "||"}
ARDUINO_BUILTINS = {
    "pinMode": 2,
    "digitalWrite": 2,
    "digitalRead": 1,
    "analogWrite": 2,
    "analogRead": 1,
    "delay": 1,
}


class SemanticError(Exception):
    pass


class Symbol:
    def __init__(self, name: str, tipo: Optional[str], categoria: str,
                 line: int, params: Optional[List[str]] = None):
        self.name = name
        self.tipo = tipo            # GALLEON / SICKLE / PARCHMENT / VERITAS / None
        self.categoria = categoria  # "VOTO" | "VARINHA" | "INCANTATIO"
        self.line = line
        self.params = params

    def __repr__(self):
        desc = f"feitiço({', '.join(self.params)})" if self.categoria == "INCANTATIO" else self.tipo
        return f"🏷️ Symbol({self.name:<20}, {self.categoria:<12}, {desc}, Line={self.line})"


class Scope:
    def __init__(self, nome: str, parent: Optional["Scope"] = None):
        self.nome = nome
        self.symbols: Dict[str, Symbol] = {}
        self.parent = parent

    def declare(self, symbol: Symbol):
        if symbol.name in self.symbols:
            anterior = self.symbols[symbol.name]
            raise SemanticError(
                f"💥 [Erro Semântico] Linha {symbol.line}: "
                f"'{symbol.name}' já foi declarado na linha {anterior.line} "
                f"(redeclaração proibida no mesmo escopo)."
            )
        self.symbols[symbol.name] = symbol

    def resolve(self, name: str) -> Optional[Symbol]:
        if name in self.symbols:
            return self.symbols[name]
        if self.parent is not None:
            return self.parent.resolve(name)
        return None


class SemanticAnalyzerPotter:
    def __init__(self):
        self.global_scope = Scope("HOGWARTS (Global)")
        self.current_scope = self.global_scope
        self.dentro_de_incantatio = False
        self.tabela_completa: List[Symbol] = []

    def error(self, line: int, message: str):
        raise SemanticError(f"💥 [Erro Semântico] Linha {line}: {message}")

    def analyze(self, program: ProgramNode) -> Scope:
        for stmt in program.body:
            self.visit(stmt)
        return self.global_scope

    def visit(self, node: ASTNode):
        metodo = getattr(self, f"visit_{type(node).__name__}", None)
        if metodo is None:
            raise SemanticError(f"Nenhuma regra semântica definida para {type(node).__name__}")
        return metodo(node)

    def visit_VarDeclNode(self, node: VarDeclNode):
        tipo_valor = self.infer_type(node.value_expr)

        if tipo_valor is not None and tipo_valor != node.data_type:
            self.error(
                node.line,
                f"'{node.name}' foi declarado como {node.data_type} mas recebeu tipo {tipo_valor}."
            )

        categoria = "VOTO" if node.is_const else "VARINHA"
        simbolo = Symbol(node.name, node.data_type, categoria, node.line)
        self.current_scope.declare(simbolo)
        self.tabela_completa.append(simbolo)

    def visit_AssignNode(self, node: AssignNode):
        simbolo = self.current_scope.resolve(node.name)
        if simbolo is None:
            self.error(node.line, f"Identificador '{node.name}' usado antes de ser declarado.")
        if simbolo.categoria == "VOTO":
            self.error(node.line, f"'{node.name}' é um VOTO Inquebrável (constante na linha {simbolo.line}) e não pode ser alterado.")
        if simbolo.categoria == "INCANTATIO":
            self.error(node.line, f"'{node.name}' é um feitiço e não aceita atribuição.")

        tipo_valor = self.infer_type(node.expr)
        if tipo_valor is not None and simbolo.tipo is not None and tipo_valor != simbolo.tipo:
            self.error(node.line, f"'{node.name}' é do tipo {simbolo.tipo} mas recebeu um {tipo_valor}.")

    def visit_LumosNode(self, node: LumosNode):
        self.infer_type(node.expr)

    def visit_SortilegioNode(self, node: SortilegioNode):
        tipo_cond = self.infer_type(node.condition)
        if tipo_cond is not None and tipo_cond != "VERITAS":
            self.error(node.line, f"Condição do SORTILEGIO exige tipo VERITAS (booleano), encontrado {tipo_cond}.")
        self.visit_bloco(node.then_branch, "SORTILEGIO")
        if node.else_branch is not None:
            self.visit_bloco(node.else_branch, "SENAO")

    def visit_ViraTempoNode(self, node: ViraTempoNode):
        tipo_cond = self.infer_type(node.condition)
        if tipo_cond is not None and tipo_cond != "VERITAS":
            self.error(node.line, f"Condição do VIRATEMPO exige tipo VERITAS (booleano), encontrado {tipo_cond}.")
        self.visit_bloco(node.body, "VIRATEMPO")

    def visit_FuncDeclNode(self, node: FuncDeclNode):
        simbolo = Symbol(node.name, None, "INCANTATIO", node.line, params=node.params)
        self.current_scope.declare(simbolo)
        self.tabela_completa.append(simbolo)

        escopo_anterior = self.current_scope
        dentro_anterior = self.dentro_de_incantatio
        self.current_scope = Scope(f"INCANTATIO {node.name}", parent=escopo_anterior)
        self.dentro_de_incantatio = True

        for nome_param in node.params:
            param_sym = Symbol(nome_param, None, "VARINHA", node.line)
            self.current_scope.declare(param_sym)
            self.tabela_completa.append(param_sym)

        for stmt in node.body:
            self.visit(stmt)

        self.current_scope = escopo_anterior
        self.dentro_de_incantatio = dentro_anterior

    def visit_CallNode(self, node: CallNode):
        simbolo = self.current_scope.resolve(node.name)
        if simbolo is None and node.name in ARDUINO_BUILTINS:
            # Comandos nativos ficam reservados para a futura geração Arduino.
            esperados = ARDUINO_BUILTINS[node.name]
            if len(node.args) != esperados:
                self.error(node.line, f"Comando Arduino '{node.name}' requer {esperados} parâmetro(s), recebidos {len(node.args)}.")
            for arg in node.args:
                self.infer_type(arg)
            return
        if simbolo is None:
            self.error(node.line, f"Tentativo de lançar '{node.name}', mas nenhum feitiço com esse nome foi ensinado.")
        if simbolo.categoria != "INCANTATIO":
            self.error(node.line, f"'{node.name}' não é um feitiço (INCANTATIO).")
        if len(node.args) != len(simbolo.params):
            self.error(node.line, f"Feitiço '{node.name}' requer {len(simbolo.params)} parâmetro(s), recebidos {len(node.args)}.")
        for arg in node.args:
            self.infer_type(arg)

    def visit_ExpelliarmusNode(self, node: ExpelliarmusNode):
        if not self.dentro_de_incantatio:
            self.error(node.line, "EXPELLIARMUS (retorno) só pode ser conjurado dentro de um INCANTATIO.")
        self.infer_type(node.expr)

    def visit_bloco(self, comandos: List[ASTNode], nome_bloco: str):
        escopo_anterior = self.current_scope
        self.current_scope = Scope(nome_bloco, parent=escopo_anterior)
        for stmt in comandos:
            self.visit(stmt)
        self.current_scope = escopo_anterior

    def infer_type(self, expr: ASTNode) -> Optional[str]:
        if isinstance(expr, LiteralNode):
            return expr.type_name

        if isinstance(expr, IdentifierNode):
            simbolo = self.current_scope.resolve(expr.name)
            if simbolo is None:
                self.error(expr.line, f"Variável '{expr.name}' usada antes de ser declarada.")
            return simbolo.tipo

        if isinstance(expr, BinaryOpNode):
            tipo_esq = self.infer_type(expr.left)
            tipo_dir = self.infer_type(expr.right)

            if tipo_esq is None or tipo_dir is None:
                return None

            if expr.op in OPS_COMPARACAO:
                if expr.op in {"<", ">", "<=", ">="} and (
                    tipo_esq not in TIPOS_NUMERICOS or tipo_dir not in TIPOS_NUMERICOS
                ):
                    self.error(expr.line, f"Operador '{expr.op}' exige tipos numéricos.")
                if tipo_esq != tipo_dir:
                    self.error(expr.line, f"Comparação entre tipos incompatíveis ({tipo_esq} {expr.op} {tipo_dir}).")
                return "VERITAS"

            if expr.op in OPS_LOGICOS:
                if tipo_esq != "VERITAS" or tipo_dir != "VERITAS":
                    self.error(expr.line, f"Operador '{expr.op}' exige operandos VERITAS.")
                return "VERITAS"

            if expr.op in OPS_ARITMETICOS:
                if tipo_esq not in TIPOS_NUMERICOS or tipo_dir not in TIPOS_NUMERICOS:
                    self.error(expr.line, f"Operador '{expr.op}' exige tipos numéricos (GALLEON/SICKLE), recebidos {tipo_esq} e {tipo_dir}.")
                return "SICKLE" if "SICKLE" in (tipo_esq, tipo_dir) else "GALLEON"

        if isinstance(expr, UnaryOpNode):
            tipo = self.infer_type(expr.operand)
            if expr.op == "!":
                if tipo != "VERITAS":
                    self.error(expr.line, "Operador '!' exige operando VERITAS.")
                return "VERITAS"
            if tipo not in TIPOS_NUMERICOS:
                self.error(expr.line, f"Operador '{expr.op}' exige operando numérico.")
            return tipo

        return None

    def print_symbol_table(self) -> str:
        linhas = [f"{'Nome':<22}{'Categoria':<14}{'Tipo':<22}{'Linha'}"]
        linhas.append("-" * 66)
        for s in self.tabela_completa:
            desc = f"feitiço({', '.join(s.params)})" if s.categoria == "INCANTATIO" else (s.tipo or "(parâmetro)")
            linhas.append(f"{s.name:<22}{s.categoria:<14}{desc:<22}{s.line}")
        return "\n".join(linhas)