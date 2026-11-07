"""Teste de fumaça da Potter IDE: cria a janela (oculta) e executa o fluxo pelo código."""
import os
import shutil
import tempfile
import unittest

try:
    import tkinter as tk
    _root = tk.Tk()
    _root.destroy()
    TK_OK = True
except Exception:  # noqa: BLE001 -- sem display/Tk
    TK_OK = False

RAIZ = os.path.dirname(os.path.abspath(__file__))


@unittest.skipUnless(TK_OK, "Tkinter indisponível")
class PotterIDETests(unittest.TestCase):
    def setUp(self):
        from potter_ide import PotterIDE
        self.tmp = tempfile.mkdtemp(prefix="potter_ide_")
        self.duelo = os.path.join(self.tmp, "duelo_arcano.potter")
        shutil.copy(os.path.join(RAIZ, "duelo_arcano.potter"), self.duelo)
        self.root = tk.Tk()
        self.root.withdraw()
        self.ide = PotterIDE(self.root, self.duelo, detectar_portas=False)
        self.root.update()

    def tearDown(self):
        self.ide.modificado = False
        self.root.destroy()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def saida(self):
        return self.ide.saida.get("1.0", "end-1c")

    def test_abre_duelo_sem_marcar_modificado(self):
        self.assertIn("HOGWARTS DueloArcano", self.ide.codigo())
        self.assertFalse(self.ide.modificado)
        self.assertIn("duelo_arcano.potter", self.root.title())

    def test_realce_aplicado(self):
        self.root.update()
        self.assertTrue(self.ide.editor.tag_ranges("palavra_chave"))
        self.assertTrue(self.ide.editor.tag_ranges("comentario"))

    def test_fluxo_completo_do_duelo(self):
        self.ide.acao_tokens()
        self.assertIn("HOGWARTS", self.saida())
        self.ide.acao_ast()
        self.assertIn("INCANTATIO (Feitiço): venceMagia(a, b)", self.saida())
        self.ide.acao_tabela()
        self.assertIn("bool venceMagia(int a, int b)", self.saida())
        self.assertTrue(self.ide.acao_compilar())
        self.assertIn("void loop() {", self.saida())
        ino = os.path.join(self.tmp, "DueloArcano", "DueloArcano.ino")
        self.assertTrue(os.path.isfile(ino))

    def test_erro_vira_link_que_leva_a_linha(self):
        self.ide._definir_texto("HOGWARTS A {\n  VARINHA GALLEON x ~> 1;\n  LUMOS(y);\n}")
        self.assertFalse(self.ide.acao_compilar())
        self.assertIn("Linha 3, Coluna 9", self.saida())
        self.assertEqual(self.ide.editor.index("insert"), "3.8")  # cursor já levado ao erro
        self.ide.editor.mark_set("insert", "1.0")
        self.ide.ir_para(self.ide._links_erro[0].linha, self.ide._links_erro[0].coluna)
        self.assertEqual(self.ide.editor.index("insert"), "3.8")
        self.assertTrue(self.ide.editor.tag_ranges("erro_linha"))

    def test_edicao_marca_modificado_e_salvar_grava(self):
        self.ide.editor.insert("end", "\n-- comentario novo")
        self.root.update()
        self.assertTrue(self.ide.modificado)
        self.assertTrue(self.ide.salvar())
        self.assertFalse(self.ide.modificado)
        with open(self.duelo, encoding="utf-8") as f:
            self.assertTrue(f.read().endswith("-- comentario novo"))


if __name__ == "__main__":
    unittest.main()
