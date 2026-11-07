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

    def test_unicode_digits_are_not_numbers(self):
        with self.assertRaises(SyntaxError) as ctx:
            LexerPotter('x ~> 2²;').tokenize()
        self.assertIn('Coluna 7', str(ctx.exception))

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

    def test_unary_on_untyped_parameter_is_deferred(self):
        # parâmetros não têm tipo declarado: como no binário, a checagem é adiada
        analyze('HOGWARTS A { INCANTATIO f(p) { SORTILEGIO (!p) { LUMOS(1); } } CAST f(ALWAYS); }')
        analyze('HOGWARTS A { INCANTATIO g(n) { LUMOS(-n); LUMOS(+n); } CAST g(3); }')
        analyze('HOGWARTS A { INCANTATIO h(p) { VARINHA VERITAS q ~> !p; } CAST h(NEVER); }')

    def test_unary_on_known_wrong_type_is_still_rejected(self):
        for source in ('HOGWARTS A { LUMOS(!3); }', 'HOGWARTS A { LUMOS(-ALWAYS); }'):
            with self.subTest(source=source):
                with self.assertRaises(SemanticError):
                    analyze(source)


class PositionInMessagesTests(unittest.TestCase):
    """Toda mensagem de erro deve apontar linha e coluna quando possível."""

    def assert_position(self, source, line, col, error=SemanticError):
        with self.assertRaises(error) as ctx:
            analyze(source)
        self.assertIn(f'Linha {line}, Coluna {col}', str(ctx.exception))

    def test_semantic_unknown_identifier_has_column(self):
        self.assert_position('HOGWARTS A {\n    LUMOS(ghost);\n}', 2, 11)

    def test_semantic_constant_assignment_has_column(self):
        self.assert_position('HOGWARTS A {\n VOTO GALLEON x ~> 1;\n   x ~> 2;\n}', 3, 4)

    def test_semantic_type_error_points_to_operator(self):
        self.assert_position('HOGWARTS A { VARINHA VERITAS x ~> ALWAYS && 1; }', 1, 42)

    def test_semantic_redeclaration_has_column(self):
        self.assert_position('HOGWARTS A {\n VARINHA GALLEON x ~> 1;\n  VARINHA GALLEON x ~> 2;\n}', 3, 3)

    def test_ast_nodes_carry_column(self):
        program = ParserPotter(LexerPotter('HOGWARTS A {\n  VARINHA GALLEON x ~> 1 + 2;\n}').tokenize()).parse()
        decl = program.body[0]
        self.assertEqual((decl.line, decl.col), (2, 3))
        self.assertEqual((decl.value_expr.line, decl.value_expr.col), (2, 26))

    def test_multiline_string_token_starts_at_opening_quote(self):
        tokens = LexerPotter('HOGWARTS A {\n LUMOS("a\nb"); }').tokenize()
        string = next(t for t in tokens if t.type == TokenType.STRING_LITERAL)
        self.assertEqual((string.line, string.column), (2, 8))
        self.assertEqual(string.value, 'a\nb')
        semicolon = tokens[-3]  # 'b");' -> ';' na linha 3, coluna 4
        self.assertEqual((semicolon.line, semicolon.column), (3, 4))

    def test_unterminated_string_points_to_opening_quote(self):
        with self.assertRaises(SyntaxError) as ctx:
            LexerPotter('LUMOS("abc\n def').tokenize()
        self.assertIn('Linha 1, Coluna 7', str(ctx.exception))


if __name__ == '__main__':
    unittest.main()
