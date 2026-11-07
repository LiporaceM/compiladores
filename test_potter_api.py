import glob
import json
import os
import unittest

import potter_api
from compilar_e_gravar import interpretar_portas

RAIZ = os.path.dirname(os.path.abspath(__file__))


def ler(caminho):
    with open(os.path.join(RAIZ, caminho), encoding="utf-8") as f:
        return f.read()


DUELO = ler("duelo_arcano.potter")


class FasesTests(unittest.TestCase):
    def test_tokens_do_duelo(self):
        r = potter_api.obter_tokens(DUELO)
        self.assertTrue(r.ok)
        self.assertEqual(r.dados[0].type.name, "HOGWARTS")
        self.assertIn("INCANTATIO", r.texto)
        self.assertIn("tokens.", r.texto)

    def test_ast_do_duelo(self):
        r = potter_api.obter_ast(DUELO)
        self.assertTrue(r.ok)
        self.assertIn("HOGWARTS (DueloArcano)", r.texto)
        self.assertIn("venceMagia(a, b)", r.texto)

    def test_tabela_de_simbolos_do_duelo(self):
        r = potter_api.obter_tabela_simbolos(DUELO)
        self.assertTrue(r.ok)
        self.assertIn("LED_DANO_J1", r.texto)
        self.assertIn("feitiço(a, b)", r.texto)
        self.assertIn("bool venceMagia(int a, int b)", r.texto)
        self.assertEqual(r.avisos, [])

    def test_gerar_ino_igual_ao_cli(self):
        from potter_arduino import compilar
        r = potter_api.gerar_ino(DUELO)
        self.assertTrue(r.ok)
        self.assertEqual(r.dados, compilar(DUELO)[:2])


class DiagnosticosTests(unittest.TestCase):
    def assert_erro(self, codigo, fase, linha, coluna, funcao=potter_api.gerar_ino):
        r = funcao(codigo)
        self.assertFalse(r.ok)
        self.assertEqual(len(r.erros), 1)
        d = r.erros[0]
        self.assertEqual((d.fase, d.linha, d.coluna), (fase, linha, coluna), d.mensagem)

    def test_erro_lexico(self):
        self.assert_erro("HOGWARTS A {\n  @\n}", "Léxico", 2, 3, potter_api.obter_tokens)

    def test_erro_sintatico(self):
        self.assert_erro("HOGWARTS A {\n  LUMOS(1)\n}", "Sintático", 3, 1, potter_api.obter_ast)

    def test_erro_semantico(self):
        self.assert_erro("HOGWARTS A {\n  LUMOS(x);\n}", "Semântico", 2, 9, potter_api.obter_tabela_simbolos)

    def test_erro_de_transpilacao(self):
        self.assert_erro("HOGWARTS A {\n VARINHA GALLEON x ~> 99999;\n}", "Transpilação", 2, 23)

    def test_erro_lexico_aparece_em_todas_as_fases(self):
        for f in (potter_api.obter_tokens, potter_api.obter_ast,
                  potter_api.obter_tabela_simbolos, potter_api.gerar_ino):
            with self.subTest(fase=f.__name__):
                self.assert_erro("HOGWARTS A { $ }", "Léxico", 1, 14, f)

    def test_aviso_com_posicao(self):
        r = potter_api.gerar_ino("HOGWARTS A { INCANTATIO f(a) { LUMOS(1); } CAST f(2); }")
        self.assertTrue(r.ok)
        self.assertEqual(len(r.avisos), 1)
        self.assertEqual((r.avisos[0].linha, r.avisos[0].coluna), (1, 14))

    def test_descricao_sem_prefixo_e_posicao(self):
        d = potter_api.gerar_ino("HOGWARTS A {\n  LUMOS(x);\n}").erros[0]
        self.assertEqual(d.descricao, "Variável 'x' usada antes de ser declarada.")
        d = potter_api.obter_ast("HOGWARTS A {\n  LUMOS(1)\n}").erros[0]
        self.assertEqual(d.descricao, "próximo a '}': LUMOS precisa terminar com ';'.")

    def test_erro_interno_nao_escapa(self):
        r = potter_api.gerar_ino(None)  # tipo inválido: nunca deve levantar exceção
        self.assertFalse(r.ok)
        self.assertEqual(r.erros[0].fase, "Interno")


class ExemplosTests(unittest.TestCase):
    def test_exemplos_validos_compilam_sem_avisos(self):
        for caminho in sorted(glob.glob(os.path.join(RAIZ, "exemplos", "*.potter"))):
            with self.subTest(exemplo=os.path.basename(caminho)):
                r = potter_api.gerar_ino(ler(caminho))
                self.assertTrue(r.ok, r.texto)
                self.assertEqual(r.avisos, [])

    def test_exemplos_de_erro_falham_com_posicao(self):
        arquivos = sorted(glob.glob(os.path.join(RAIZ, "exemplos", "erros", "*.potter")))
        self.assertGreaterEqual(len(arquivos), 6)
        for caminho in arquivos:
            with self.subTest(exemplo=os.path.basename(caminho)):
                r = potter_api.gerar_ino(ler(caminho))
                self.assertFalse(r.ok)
                self.assertIsNotNone(r.erros[0].linha)
                self.assertIsNotNone(r.erros[0].coluna)


class RealceTests(unittest.TestCase):
    def trechos(self, codigo):
        return {(tipo, codigo[i:f]) for tipo, i, f in potter_api.realce(codigo)}

    def test_categorias(self):
        codigo = 'VARINHA GALLEON x ~> 10; -- nota\nCAST digitalWrite(LED, ALTO); LUMOS("oi");'
        t = self.trechos(codigo)
        for esperado in [("palavra_chave", "VARINHA"), ("tipo", "GALLEON"), ("operador", "~>"),
                         ("numero", "10"), ("comentario", "-- nota"), ("palavra_chave", "CAST"),
                         ("primitiva", "digitalWrite"), ("constante", "ALTO"),
                         ("palavra_chave", "LUMOS"), ("texto", '"oi"')]:
            self.assertIn(esperado, t)
        self.assertNotIn(("palavra_chave", "x"), t)

    def test_palavras_chave_da_linguagem(self):
        for p in ("HOGWARTS", "INCANTATIO", "CAST", "VARINHA", "VOTO", "SORTILEGIO", "SENAO",
                  "VIRATEMPO", "LUMOS", "EXPELLIARMUS"):
            self.assertIn(p, potter_api.PALAVRAS_CHAVE)

    def test_tolerante_a_codigo_com_erro(self):
        self.assertIn(("texto", '"sem fim'), self.trechos('LUMOS("sem fim'))

    def test_comentario_dentro_de_texto_nao_e_comentario(self):
        self.assertEqual(self.trechos('"a -- b"'), {("texto", '"a -- b"')})


class PortasTests(unittest.TestCase):
    def test_interpretar_portas_prioriza_placas_reconhecidas(self):
        saida = json.dumps({"detected_ports": [
            {"port": {"address": "COM1", "protocol": "serial", "protocol_label": "Serial Port"}},
            {"port": {"address": "COM4", "protocol": "serial", "protocol_label": "Serial Port (USB)"},
             "matching_boards": [{"name": "Arduino Uno", "fqbn": "arduino:avr:uno"}]},
            {"port": {"address": "192.168.0.5", "protocol": "network"}},
        ]})
        self.assertEqual(interpretar_portas(saida), [("COM4", "Arduino Uno"), ("COM1", "Serial Port")])

    def test_json_invalido(self):
        self.assertEqual(interpretar_portas("lixo"), [])
        self.assertEqual(interpretar_portas("{}"), [])


if __name__ == "__main__":
    unittest.main()
