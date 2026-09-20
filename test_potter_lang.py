import unittest

from potter_lang import (
    BinaryOpNode,
    LexerPotter,
    ParserPotter,
    SemanticAnalyzerPotter,
    SemanticError,
    TokenType,
    UnaryOpNode,
)


def analyze(source):
    tokens = LexerPotter(source).tokenize()
    return SemanticAnalyzerPotter().analyze(ParserPotter(tokens).parse())


class LexerTests(unittest.TestCase):
    def test_all_literals_keywords_delimiters_and_operators(self):
        source = (
            'HOGWARTS A { VARINHA GALLEON x ~> 1; '
            'LUMOS("ok"); ALWAYS NEVER == != < > <= >= + - * / % && || ! '
            '( ) { } , ; }'
        )
        tokens = LexerPotter(source).tokenize()
        types = [token.type for token in tokens]
        expected = [
            TokenType.HOGWARTS, TokenType.IDENTIFIER, TokenType.LBRACE,
            TokenType.VARINHA, TokenType.TYPE_GALLEON, TokenType.IDENTIFIER,
            TokenType.WAND_ASSIGN, TokenType.INT_LITERAL, TokenType.SEMICOLON,
            TokenType.LUMOS, TokenType.LPAREN, TokenType.STRING_LITERAL,
            TokenType.RPAREN, TokenType.SEMICOLON, TokenType.ALWAYS,
            TokenType.NEVER, TokenType.EQ, TokenType.NEQ, TokenType.LT,
            TokenType.GT, TokenType.LTE, TokenType.GTE, TokenType.PLUS,
            TokenType.MINUS, TokenType.STAR_MULT, TokenType.SLASH,
            TokenType.MOD, TokenType.AND, TokenType.OR, TokenType.NOT,
            TokenType.LPAREN, TokenType.RPAREN, TokenType.LBRACE,
            TokenType.RBRACE, TokenType.COMMA, TokenType.SEMICOLON,
            TokenType.RBRACE, TokenType.EOF,
        ]
        self.assertEqual(types, expected)

    def test_comments_are_ignored_and_columns_continue(self):
        tokens = LexerPotter("HOGWARTS A { -- comentário\n LUMOS(1); }").tokenize()
        self.assertEqual([token.type for token in tokens[3:]], [
            TokenType.LUMOS, TokenType.LPAREN, TokenType.INT_LITERAL,
            TokenType.RPAREN, TokenType.SEMICOLON, TokenType.RBRACE,
            TokenType.EOF,
        ])
        self.assertEqual(tokens[3].column, 2)

    def test_numbers_and_identifiers(self):
        tokens = LexerPotter("_x 10 2.5").tokenize()
        self.assertEqual([token.type for token in tokens], [
            TokenType.IDENTIFIER, TokenType.INT_LITERAL,
            TokenType.FLOAT_LITERAL, TokenType.EOF,
        ])
        self.assertEqual(tokens[2].value, 2.5)

    def test_lexical_errors(self):
        for source in ('@', '1.2.3', '"unterminated', '=', '&'):
            with self.subTest(source=source):
                with self.assertRaises(SyntaxError):
                    LexerPotter(source).tokenize()


class ParserTests(unittest.TestCase):
    def test_expression_precedence_and_unary_nodes(self):
        program = ParserPotter(LexerPotter(
            'HOGWARTS A { VARINHA VERITAS ok ~> !(1 < 2) || ALWAYS; }'
        ).tokenize()).parse()
        expression = program.body[0].value_expr
        self.assertIsInstance(expression, BinaryOpNode)
        self.assertEqual(expression.op, '||')
        self.assertIsInstance(expression.left, UnaryOpNode)

    def test_parser_rejects_trailing_tokens(self):
        with self.assertRaises(SyntaxError):
            ParserPotter(LexerPotter('HOGWARTS A { } lixo').tokenize()).parse()

    def test_parser_rejects_missing_statement_terminator(self):
        with self.assertRaises(SyntaxError):
            ParserPotter(LexerPotter('HOGWARTS A { LUMOS(1) }').tokenize()).parse()


class SemanticTests(unittest.TestCase):
    def test_core_language_constructs(self):
        analyze('''
            HOGWARTS ViaLactea {
                VOTO SICKLE velocidadeLuz ~> 299792.458;
                VARINHA GALLEON temperatura ~> 273;
                VARINHA PARCHMENT mensagem ~> "Explorando a galáxia...";
                LUMOS(mensagem);
                SORTILEGIO (temperatura > 0) {
                    LUMOS("Sistema térmico estável!");
                } SENAO {
                    LUMOS("Congelamento absoluto detectado!");
                }
                VARINHA GALLEON orbitas ~> 0;
                VIRATEMPO (orbitas < 3) {
                    orbitas ~> orbitas + 1;
                    LUMOS(orbitas);
                }
            }
        ''')

    def test_valid_types_scopes_and_arduino_commands(self):
        analyze('''
            HOGWARTS A {
                VARINHA GALLEON pin ~> 13;
                VARINHA VERITAS ligado ~> ALWAYS;
                VARINHA GALLEON leitura ~> 1 + 2 % 2;
                SORTILEGIO (ligado && !(leitura >= 3)) { LUMOS(pin); }
                CAST pinMode(pin, 1);
                CAST digitalWrite(pin, ligado);
                CAST delay(1000);
            }
        ''')

    def test_constant_assignment_is_rejected(self):
        with self.assertRaises(SemanticError):
            analyze('HOGWARTS A { VOTO GALLEON x ~> 1; x ~> 2; }')

    def test_unknown_identifier_and_redeclaration_are_rejected(self):
        for source in (
            'HOGWARTS A { LUMOS(ghost); }',
            'HOGWARTS A { VARINHA GALLEON x ~> 1; VARINHA GALLEON x ~> 2; }',
        ):
            with self.subTest(source=source):
                with self.assertRaises(SemanticError):
                    analyze(source)

    def test_type_and_condition_errors_are_rejected(self):
        cases = (
            'HOGWARTS A { VARINHA GALLEON x ~> ALWAYS; }',
            'HOGWARTS A { SORTILEGIO (1) { LUMOS(1); } }',
            'HOGWARTS A { VARINHA VERITAS x ~> !1; }',
            'HOGWARTS A { VARINHA GALLEON x ~> 1; SORTILEGIO ("a" < "b") { } }',
            'HOGWARTS A { VARINHA VERITAS x ~> ALWAYS && 1; }',
        )
        for source in cases:
            with self.subTest(source=source):
                with self.assertRaises(SemanticError):
                    analyze(source)

    def test_function_and_arduino_arity_errors(self):
        cases = (
            'HOGWARTS A { INCANTATIO f(x) { LUMOS(x); } CAST f(); }',
            'HOGWARTS A { CAST delay(1, 2); }',
            'HOGWARTS A { CAST unknown(1); }',
        )
        for source in cases:
            with self.subTest(source=source):
                with self.assertRaises(SemanticError):
                    analyze(source)

    def test_return_outside_function_is_rejected(self):
        with self.assertRaises(SemanticError):
            analyze('HOGWARTS A { EXPELLIARMUS ALWAYS; }')


if __name__ == '__main__':
    unittest.main()
