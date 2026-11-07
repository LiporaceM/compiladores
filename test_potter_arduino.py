import os
import unittest

from potter_arduino import (
    ParserPotterArduino,
    SemanticAnalyzerArduino,
    TranspileError,
    compilar,
)
from potter_lang import CallNode, LexerPotter, SemanticError


def ino(corpo, nome="T"):
    return compilar(f"HOGWARTS {nome} {{ {corpo} }}")[1]


class ExtensaoCastExpressaoTests(unittest.TestCase):
    def test_cast_como_expressao_gera_callnode(self):
        src = "HOGWARTS A { VARINHA GALLEON x ~> CAST digitalRead(5); }"
        ast = ParserPotterArduino(LexerPotter(src).tokenize()).parse()
        self.assertIsInstance(ast.body[0].value_expr, CallNode)

    def test_digitalread_tem_tipo_galleon(self):
        SemanticAnalyzerArduino().analyze(ParserPotterArduino(LexerPotter(
            "HOGWARTS A { SORTILEGIO (CAST digitalRead(5) == BAIXO) { LUMOS(1); } }"
        ).tokenize()).parse())

    def test_digitalread_em_variavel_de_tipo_errado_e_rejeitado(self):
        with self.assertRaises(SemanticError):
            compilar('HOGWARTS A { VARINHA PARCHMENT s ~> CAST digitalRead(5); }')

    def test_aridade_de_cast_em_expressao_e_validada(self):
        with self.assertRaises(SemanticError):
            compilar("HOGWARTS A { VARINHA GALLEON x ~> CAST digitalRead(); }")

    def test_constantes_arduino_sao_votos(self):
        with self.assertRaises(SemanticError):
            compilar("HOGWARTS A { ALTO ~> 3; }")


class TranspilacaoTests(unittest.TestCase):
    def test_constantes_e_setup_loop(self):
        c = ino("""
            VOTO GALLEON LED ~> 13;
            CAST pinMode(LED, SAIDA);
            VIRATEMPO (ALWAYS) {
                CAST digitalWrite(LED, ALTO);
                CAST delay(500);
                CAST digitalWrite(LED, BAIXO);
                CAST delay(500);
            }
        """)
        self.assertIn("const int LED = 13;", c)
        self.assertIn("void setup() {\n    pinMode(LED, OUTPUT);", c)
        self.assertIn("void loop() {\n    digitalWrite(LED, HIGH);", c)
        self.assertNotIn("while (true)", c)

    def test_sem_loop_infinito_loop_fica_vazio(self):
        c = ino("VARINHA GALLEON x ~> 1;")
        self.assertIn("void loop() {\n}", c)

    def test_lumos_ativa_serial_e_usa_f_macro(self):
        c = ino('LUMOS("oi"); LUMOS(1 + 2);')
        self.assertIn("Serial.begin(9600);", c)
        self.assertIn('Serial.println(F("oi"));', c)
        self.assertIn("Serial.println((1 + 2));", c)

    def test_sem_lumos_nao_inicia_serial(self):
        self.assertNotIn("Serial.begin", ino("VARINHA GALLEON x ~> 1;"))

    def test_tipos_c(self):
        c = ino('VARINHA GALLEON a ~> 1; VARINHA SICKLE b ~> 2.5; '
                'VARINHA PARCHMENT c ~> "x"; VARINHA VERITAS d ~> NEVER;')
        for trecho in ("int a = 1;", "float b = 2.5f;", 'String c = "x";', "bool d = false;"):
            self.assertIn(trecho, c)

    def test_precedencia_preservada_com_parenteses(self):
        c = ino("VARINHA GALLEON x ~> (1 + 2) * 3;")
        self.assertIn("int x = ((1 + 2) * 3);", c)

    def test_resto_de_sickle_usa_fmod(self):
        c = ino("VARINHA SICKLE x ~> 5.5 % 2.0;")
        self.assertIn("fmod(5.5f, 2.0f)", c)

    def test_nomes_reservados_do_cpp_sao_renomeados(self):
        c = ino("VARINHA GALLEON loop ~> 1; VARINHA GALLEON int ~> 2;")
        self.assertIn("int loop_pl = 1;", c)
        self.assertIn("int int_pl = 2;", c)

    def test_tipos_de_parametros_e_retorno_sao_inferidos(self):
        c = ino("""
            INCANTATIO dobro(n) { EXPELLIARMUS n * 2; }
            INCANTATIO maior(a, b) { EXPELLIARMUS a > b; }
            VARINHA GALLEON r ~> CAST dobro(4);
            VARINHA VERITAS m ~> CAST maior(1, 2);
        """)
        self.assertIn("int dobro(int n)", c)
        self.assertIn("bool maior(int a, int b)", c)

    def test_parametro_sickle_inferido_do_callsite(self):
        c = ino("INCANTATIO f(x) { LUMOS(x); } CAST f(1.5);")
        self.assertIn("void f(float x)", c)

    def test_global_com_cast_e_inicializado_no_setup(self):
        c = ino("VARINHA GALLEON leitura ~> CAST digitalRead(2);")
        self.assertIn("int leitura;", c)
        self.assertIn("    leitura = digitalRead(2);", c)

    def test_if_else_while(self):
        c = ino("""
            VARINHA GALLEON i ~> 0;
            VIRATEMPO (i < 3) { i ~> i + 1; }
            SORTILEGIO (i == 3) { LUMOS("ok"); } SENAO { LUMOS("ruim"); }
        """)
        self.assertIn("while (i < 3) {", c)
        self.assertIn("if (i == 3) {", c)
        self.assertIn("} else {", c)

    def test_string_com_aspas_e_barra_e_escapada(self):
        c = ino(r'LUMOS("a\b");')
        self.assertIn(r'F("a\\b")', c)


class ErrosDeTranspilacaoTests(unittest.TestCase):
    def test_codigo_apos_loop_principal_e_rejeitado(self):
        with self.assertRaises(TranspileError):
            ino("VIRATEMPO (ALWAYS) { LUMOS(1); } LUMOS(2);")

    def test_incantatio_aninhado_e_rejeitado(self):
        with self.assertRaises(TranspileError):
            ino("SORTILEGIO (ALWAYS) { INCANTATIO f() { LUMOS(1); } }")

    def test_erros_semanticos_continuam_barrando_antes_de_gerar(self):
        with self.assertRaises(SemanticError):
            ino("VOTO GALLEON x ~> 1; x ~> 2;")


class EndurecimentoTests(unittest.TestCase):
    """Casos que antes geravam C++ inválido ou com comportamento silenciosamente errado."""

    def assert_erro(self, corpo, trecho, linha=None):
        with self.assertRaises((SemanticError, TranspileError)) as ctx:
            ino(corpo)
        msg = str(ctx.exception)
        self.assertIn(trecho, msg)
        if linha is not None:
            self.assertIn(f"Linha {linha}", msg)

    # --- EXPELLIARMUS ---
    def test_retorno_em_apenas_um_ramo_e_rejeitado(self):
        self.assert_erro("INCANTATIO f(x) {\n SORTILEGIO (x > 0) { EXPELLIARMUS 1; }\n }\n CAST f(2);",
                         "nem todo caminho", linha=1)

    def test_retorno_nos_dois_ramos_e_aceito(self):
        c = ino("INCANTATIO f(x) { SORTILEGIO (x > 0) { EXPELLIARMUS 1; } SENAO { EXPELLIARMUS 2; } }"
                " VARINHA GALLEON r ~> CAST f(2);")
        self.assertIn("int f(int x)", c)

    def test_retorno_dentro_de_laco_infinito_e_aceito(self):
        ino("INCANTATIO f() { VIRATEMPO (ALWAYS) { EXPELLIARMUS 1; } } VARINHA GALLEON r ~> CAST f();")

    def test_recursao_e_aceita(self):
        c = ino("INCANTATIO fat(n) { SORTILEGIO (n <= 1) { EXPELLIARMUS 1; } EXPELLIARMUS n * CAST fat(n - 1); }"
                " VARINHA GALLEON r ~> CAST fat(5);")
        self.assertIn("int fat(int n)", c)

    def test_retornos_de_tipos_diferentes_sao_rejeitados(self):
        self.assert_erro("INCANTATIO f(x) {\n SORTILEGIO (x > 0) { EXPELLIARMUS 1; }\n EXPELLIARMUS ALWAYS; }"
                         " VARINHA GALLEON r ~> CAST f(2);", "tipos diferentes", linha=3)

    # --- função sem retorno em expressão ---
    def test_funcao_sem_retorno_em_expressao_e_erro_semantico_com_linha(self):
        with self.assertRaises(SemanticError) as ctx:
            ino("INCANTATIO f() { LUMOS(1); }\n\n VARINHA GALLEON x ~> CAST f();")
        self.assertIn("Linha 3", str(ctx.exception))
        self.assertIn("não conjura EXPELLIARMUS", str(ctx.exception))

    def test_funcao_sem_retorno_como_comando_continua_valida(self):
        self.assertIn("void f()", ino("INCANTATIO f() { LUMOS(1); } CAST f();"))

    # --- tipos após a inferência ---
    def test_parametro_com_tipos_conflitantes_e_rejeitado(self):
        self.assert_erro('INCANTATIO f(a) { LUMOS(a); }\n CAST f(1);\n CAST f("x");',
                         "parâmetro 'a'", linha=3)

    def test_retorno_usado_com_tipo_errado_e_rejeitado(self):
        self.assert_erro("INCANTATIO f(a) { EXPELLIARMUS a + 1; }\n VARINHA VERITAS b ~> CAST f(1);",
                         "VERITAS", linha=2)

    def test_condicao_com_retorno_nao_veritas_e_rejeitada(self):
        self.assert_erro("INCANTATIO f() { EXPELLIARMUS 1; }\n SORTILEGIO (CAST f()) { LUMOS(1); }",
                         "VERITAS", linha=2)

    # --- escopos ---
    def test_mesmo_nome_em_blocos_diferentes_tem_tipos_independentes(self):
        c = ino('INCANTATIO g(v) { LUMOS(v); }'
                ' SORTILEGIO (ALWAYS) { VARINHA SICKLE x ~> 1.5; CAST g(x); }'
                ' SENAO { VARINHA PARCHMENT x ~> "a"; LUMOS(x); }')
        self.assertIn("void g(float v)", c)

    def test_local_que_sombreia_global_nao_afeta_o_tipo_do_global(self):
        c = ino("VARINHA GALLEON x ~> 7;"
                " INCANTATIO h() { LUMOS(x % 2); SORTILEGIO (ALWAYS) { VARINHA SICKLE x ~> 2.5; LUMOS(x % 2.0); } }"
                " CAST h();")
        self.assertIn("Serial.println((x % 2));", c)
        self.assertIn("fmod(x, 2.0f)", c)

    def test_constante_arduino_nao_pode_ser_redeclarada(self):
        self.assert_erro("INCANTATIO f() { VARINHA GALLEON ALTO ~> 5; }", "constante nativa")

    # --- GALLEON no UNO ---
    def test_galleon_acima_de_32767_e_rejeitado(self):
        self.assert_erro("VARINHA GALLEON x ~> 40000;", "16 bits", linha=1)

    def test_galleon_nos_limites_e_aceito(self):
        c = ino("VARINHA GALLEON a ~> 32767; VARINHA GALLEON b ~> -32768;")
        self.assertIn("int a = 32767;", c)
        self.assertIn("int b = (-32768);", c)

    # --- nomes ---
    def test_nomes_de_macros_do_arduino_sao_renomeados(self):
        c = ino("VOTO GALLEON B1 ~> 2; VOTO GALLEON DEC ~> 3; VARINHA GALLEON PORTB ~> B1 + DEC;")
        self.assertIn("const int B1_pl = 2;", c)
        self.assertIn("int PORTB_pl = (B1_pl + DEC_pl);", c)

    def test_funcao_com_nome_do_core_arduino_e_renomeada(self):
        self.assertIn("void init_pl()", ino("INCANTATIO init() { LUMOS(1); } CAST init();"))

    # --- strings ---
    def test_caracteres_especiais_em_strings_sao_escapados(self):
        c = ino('LUMOS("tab\taspas\\\\fim");')
        self.assertIn(r'F("tab\taspas\\\\fim")', c)

    # --- parâmetros ---
    def test_parametro_nunca_usado_gera_aviso(self):
        _, _, avisos = compilar("HOGWARTS T { INCANTATIO f(a, b) { LUMOS(a); } CAST f(1, 2); }")
        self.assertTrue(any("'b'" in a and "nunca é usado" in a for a in avisos), avisos)


class DueloArcanoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        caminho = os.path.join(os.path.dirname(__file__), "duelo_arcano.potter")
        with open(caminho, encoding="utf-8") as f:
            cls.nome, cls.ino, cls.avisos = compilar(f.read())

    def test_compila_sem_avisos(self):
        self.assertEqual(self.nome, "DueloArcano")
        self.assertEqual(self.avisos, [])

    def test_pinagem_da_protoboard(self):
        for linha in (
            "const int LED_DANO_J1 = 2;", "const int LED_EMPATE = 3;", "const int LED_DANO_J2 = 4;",
            "const int BTN_J1_EXPELLIARMUS = 5;", "const int BTN_J1_PROTEGO = 6;", "const int BTN_J1_BOMBARDA = 7;",
            "const int BTN_J2_EXPELLIARMUS = 8;", "const int BTN_J2_PROTEGO = 9;", "const int BTN_J2_BOMBARDA = 10;",
            "const int BTN_INICIAR = 11;",
        ):
            self.assertIn(linha, self.ino)

    def test_botoes_usam_pullup_e_leds_saida(self):
        self.assertEqual(self.ino.count("INPUT_PULLUP);"), 7)
        self.assertEqual(self.ino.count("OUTPUT);"), 3)

    def test_regra_pedra_papel_tesoura_magica(self):
        self.assertIn("bool venceMagia(int a, int b)", self.ino)
        self.assertIn("(a == F_EXPELLIARMUS) && (b == F_BOMBARDA)", self.ino)
        self.assertIn("(a == F_BOMBARDA) && (b == F_PROTEGO)", self.ino)
        self.assertIn("(a == F_PROTEGO) && (b == F_EXPELLIARMUS)", self.ino)

    def test_tem_setup_e_loop(self):
        self.assertIn("void setup() {", self.ino)
        self.assertIn("void loop() {", self.ino)


if __name__ == "__main__":
    unittest.main()
