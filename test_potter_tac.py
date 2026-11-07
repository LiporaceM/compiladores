import contextlib
import io
import os
import unittest

from potter_lang import SemanticError
from potter_tac import executar, formatar, gerar_tac, main

RAIZ = os.path.dirname(os.path.abspath(__file__))


def tac(corpo: str) -> str:
    return formatar(gerar_tac(f"HOGWARTS T {{ {corpo} }}"))


def rodar(corpo: str, **kw):
    return executar(gerar_tac(f"HOGWARTS T {{ {corpo} }}"), **kw)


def linhas(texto: str):
    return [l.strip() for l in texto.strip().splitlines()]


class FormatoTests(unittest.TestCase):
    def test_expressao_em_tres_enderecos_respeita_precedencia(self):
        self.assertEqual(linhas(tac("VARINHA GALLEON x ~> 2 + 3 * 4;")), [
            "program T:", "t1 = 3 * 4", "t2 = 2 + t1", "x = t2", "halt"])

    def test_literais(self):
        # a PotterLang não tem escapes: a barra é literal e o TAC a escapa ao imprimir
        saida = tac('VARINHA SICKLE s ~> 2.5; VARINHA PARCHMENT p ~> "a\\b"; VARINHA VERITAS v ~> NEVER;')
        self.assertIn("s = 2.5", saida)
        self.assertIn('p = "a\\\\b"', saida)
        self.assertIn("v = false", saida)

    def test_unarios(self):
        self.assertEqual(linhas(tac("VARINHA GALLEON x ~> -5; VARINHA VERITAS v ~> !ALWAYS;"))[1:5],
                         ["t1 = -5", "x = t1", "t2 = !true", "v = t2"])

    def test_sortilegio_com_senao(self):
        self.assertEqual(linhas(tac("SORTILEGIO (1 < 2) { LUMOS(1); } SENAO { LUMOS(2); }")), [
            "program T:", "t1 = 1 < 2", "ifFalse t1 goto L1", "print 1", "goto L2",
            "L1:", "print 2", "L2:", "halt"])

    def test_sortilegio_sem_senao(self):
        self.assertEqual(linhas(tac("SORTILEGIO (1 < 2) { LUMOS(1); }"))[1:5],
                         ["t1 = 1 < 2", "ifFalse t1 goto L1", "print 1", "L1:"])

    def test_viratempo(self):
        self.assertEqual(linhas(tac("VARINHA GALLEON i ~> 0; VIRATEMPO (i < 3) { i ~> i + 1; }")), [
            "program T:", "i = 0", "L1:", "t1 = i < 3", "ifFalse t1 goto L2",
            "t2 = i + 1", "i = t2", "goto L1", "L2:", "halt"])

    def test_funcao_parametros_chamada_e_retorno(self):
        saida = linhas(tac("INCANTATIO soma(a, b) { EXPELLIARMUS a + b; }"
                           " VARINHA GALLEON r ~> CAST soma(1, 2);"))
        self.assertEqual(saida, [
            "program T:", "param 1", "param 2", "t1 = call soma, 2", "r = t1", "halt",
            "function soma(a, b):", "t2 = a + b", "return t2", "end soma"])

    def test_funcao_sem_retorno_ganha_return_implicito(self):
        saida = linhas(tac("INCANTATIO f() { LUMOS(1); } CAST f();"))
        self.assertEqual(saida[-3:], ["print 1", "return", "end f"])
        self.assertIn("call f, 0", saida)

    def test_argumentos_avaliados_antes_dos_params(self):
        saida = linhas(tac("INCANTATIO f(a) { EXPELLIARMUS a; } INCANTATIO g(a, b) { EXPELLIARMUS a + b; }"
                           " VARINHA GALLEON r ~> CAST g(CAST f(1), 2);"))
        principal = saida[1:saida.index("halt")]
        self.assertEqual(principal, ["param 1", "t1 = call f, 1", "param t1", "param 2",
                                     "t2 = call g, 2", "r = t2"])

    def test_primitiva_arduino_e_constantes(self):
        saida = linhas(tac("CAST pinMode(2, SAIDA); SORTILEGIO (CAST digitalRead(5) == BAIXO) { LUMOS(1); }"))
        self.assertEqual(saida[1:6], ["param 2", "param SAIDA", "call pinMode, 2",
                                      "param 5", "t1 = call digitalRead, 1"])

    def test_mesmo_nome_em_escopos_diferentes_recebe_nomes_unicos(self):
        saida = tac("VARINHA GALLEON x ~> 1;"
                    " SORTILEGIO (ALWAYS) { VARINHA SICKLE x ~> 2.5; LUMOS(x); }"
                    " LUMOS(x);")
        self.assertEqual(linhas(saida)[1:], [
            "x = 1", "ifFalse true goto L1", "x_1 = 2.5", "print x_1", "L1:", "print x", "halt"])

    def test_parametro_com_nome_de_global_e_renomeado(self):
        saida = tac("VARINHA GALLEON a ~> 1; INCANTATIO f(a) { LUMOS(a); } CAST f(2); LUMOS(a);")
        self.assertIn("function f(a_1):", saida)
        self.assertIn("print a_1", saida)

    def test_anotacao_de_linha_no_cli(self):
        caminho = os.path.join(RAIZ, "exemplos", "pisca_led.potter")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.assertEqual(main([caminho, "--linhas"]), 0)
        self.assertIn("INTERVALO_MS = 500", buf.getvalue())
        self.assertIn("# linha 3", buf.getvalue())


class CurtoCircuitoTests(unittest.TestCase):
    def test_e_logico_usa_desvio(self):
        self.assertEqual(linhas(tac("VARINHA VERITAS v ~> NEVER && ALWAYS;"))[1:6],
                         ["t1 = false", "ifFalse t1 goto L1", "t1 = true", "L1:", "v = t1"])

    def test_ou_logico_usa_desvio(self):
        self.assertIn("if t1 goto L1", tac("VARINHA VERITAS v ~> ALWAYS || NEVER;"))

    def test_lado_direito_nao_executa_quando_desnecessario(self):
        corpo = ("INCANTATIO efeito() { LUMOS(99); EXPELLIARMUS ALWAYS; }"
                 " VARINHA VERITAS a ~> NEVER && CAST efeito();"
                 " VARINHA VERITAS b ~> ALWAYS || CAST efeito();"
                 " VARINHA VERITAS c ~> ALWAYS && CAST efeito();"
                 " LUMOS(a); LUMOS(b); LUMOS(c);")
        self.assertEqual(rodar(corpo), [99, False, True, True])


class ExecucaoTests(unittest.TestCase):
    """O interpretador de TAC confirma que o código gerado calcula o que o fonte descreve."""

    def test_recursao_fatorial(self):
        corpo = ("INCANTATIO fat(n) { SORTILEGIO (n <= 1) { EXPELLIARMUS 1; } EXPELLIARMUS n * CAST fat(n - 1); }"
                 " LUMOS(CAST fat(5)); LUMOS(CAST fat(7));")
        self.assertEqual(rodar(corpo), [120, 5040])

    def test_divisao_e_resto_como_no_c(self):
        corpo = "LUMOS(7 / 2); LUMOS(-7 / 2); LUMOS(-7 % 2); LUMOS(7 % -2); LUMOS(7.5 % 2.0); LUMOS(1 / 4.0);"
        self.assertEqual(rodar(corpo), [3, -3, -1, 1, 1.5, 0.25])

    def test_laco_e_globais_alterados_por_funcao(self):
        corpo = ("VARINHA GALLEON total ~> 0;"
                 " INCANTATIO somar(v) { total ~> total + v; }"
                 " VARINHA GALLEON i ~> 1;"
                 " VIRATEMPO (i <= 4) { CAST somar(i); i ~> i + 1; }"
                 " LUMOS(total);")
        self.assertEqual(rodar(corpo), [10])

    def test_locais_de_chamadas_recursivas_sao_independentes(self):
        corpo = ("INCANTATIO fib(n) { VARINHA GALLEON r ~> n;"
                 " SORTILEGIO (n >= 2) { r ~> CAST fib(n - 1) + CAST fib(n - 2); } EXPELLIARMUS r; }"
                 " LUMOS(CAST fib(10));")
        self.assertEqual(rodar(corpo), [55])

    def test_primitivas_simuladas(self):
        lidos = []
        corpo = "SORTILEGIO (CAST digitalRead(5) == BAIXO) { LUMOS(\"apertado\"); } CAST digitalWrite(2, ALTO);"
        saida = rodar(corpo, primitivas={"digitalRead": lambda p: 0,
                                         "digitalWrite": lambda p, v: lidos.append((p, v))})
        self.assertEqual(saida, ["apertado"])
        self.assertEqual(lidos, [(2, 1)])

    def test_exemplo_grifinoria(self):
        with open(os.path.join(RAIZ, "exemplos", "grifinoria.potter"), encoding="utf-8") as f:
            saida = executar(gerar_tac(f.read()))
        hora = "Usando o Vira-Tempo para a hora número:"
        self.assertEqual(saida, ["Bem-vindo a Hogwarts!", "A Grifinória lidera o campeonato!",
                                 hora, 1, hora, 2, hora, 3, "Voldemort"])


class DueloTests(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(RAIZ, "duelo_arcano.potter"), encoding="utf-8") as f:
            self.codigo = gerar_tac(f.read())

    def test_todo_desvio_aponta_para_rotulo_existente(self):
        rotulos = {i.a for i in self.codigo if i.op == "label"}
        alvos = [i.a if i.op == "goto" else i.b for i in self.codigo if i.op in ("goto", "if", "iffalse")]
        self.assertTrue(alvos)
        self.assertTrue(set(alvos) <= rotulos)
        self.assertEqual(len(rotulos), len([i for i in self.codigo if i.op == "label"]))  # sem duplicados

    def test_toda_chamada_e_funcao_definida_ou_primitiva(self):
        definidas = {i.a for i in self.codigo if i.op == "func"}
        primitivas = {"pinMode", "digitalWrite", "digitalRead", "analogWrite", "analogRead", "delay"}
        chamadas = {i.b for i in self.codigo if i.op == "call"}
        self.assertTrue(chamadas <= definidas | primitivas, chamadas - definidas - primitivas)

    def test_funcoes_do_duelo(self):
        definidas = [i.a for i in self.codigo if i.op == "func"]
        self.assertEqual(len(definidas), 11)
        self.assertIn("venceMagia", definidas)

    def test_setup_do_duelo_executa_ate_o_laco(self):
        # sem ninguém apertar nada, o programa fica no VIRATEMPO (ALWAYS) para sempre
        modos = []
        with self.assertRaises(Exception) as ctx:
            executar(self.codigo, primitivas={"pinMode": lambda p, m: modos.append((p, m))},
                     max_passos=20_000)
        self.assertEqual(type(ctx.exception).__name__, "LimiteDePassos")
        self.assertIn((11, 2), modos)   # BTN_INICIAR em ENTRADA_PULLUP
        self.assertIn((2, 1), modos)    # LED_DANO_J1 em SAIDA


class ErrosTests(unittest.TestCase):
    def test_programa_invalido_nao_gera_tac(self):
        with self.assertRaises(SemanticError):
            tac("x ~> 1;")

    def test_cli_retorna_1_em_erro(self):
        caminho = os.path.join(RAIZ, "exemplos", "erros", "erro_voto_constante.potter")
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertEqual(main([caminho]), 1)
        self.assertIn("Erro Semântico", err.getvalue())


if __name__ == "__main__":
    unittest.main()
