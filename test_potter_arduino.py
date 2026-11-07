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
