"""
Testes do jogo web (web/): geração da página e VM de TAC em JavaScript.

A VM (web/tac_vm.js) roda o duelo_arcano.potter compilado para TAC. Os cenários são
os mesmos de test_simulacao_duelo.py (que usa g++); aqui o simulador é o Node
(web/simular_vm.js), com a mesma interface do sim/sim_main.cpp.
Sem Node no PATH, os testes que precisam dele são pulados.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

RAIZ = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(RAIZ, "web")
sys.path.insert(0, WEB)

from gerar_web import gerar_html, tac_para_lista  # noqa: E402

NODE = shutil.which("node")
LED_DANO_J1, LED_EMPATE, LED_DANO_J2 = 2, 3, 4
J1 = {"expelliarmus": 5, "protego": 6, "bombarda": 7}
J2 = {"expelliarmus": 8, "protego": 9, "bombarda": 10}
INICIAR = "11:0:100"
EVENTO = re.compile(r"T=(\d+) (WRITE|SERIAL) (.*)")


def ler_fonte():
    with open(os.path.join(RAIZ, "duelo_arcano.potter"), encoding="utf-8") as f:
        return f.read()


def apertar(pino, inicio_ms, duracao_ms=100):
    return f"{pino}:{inicio_ms}:{inicio_ms + duracao_ms}"


class GeracaoPaginaTests(unittest.TestCase):
    def setUp(self):
        self.html = gerar_html(ler_fonte())

    def test_html_versionado_e_identico_ao_gerado(self):
        """Garante que web/duelo_arcano.html foi regenerado depois de mudar o .potter ou o modelo."""
        with open(os.path.join(WEB, "duelo_arcano.html"), encoding="utf-8") as f:
            versionado = f.read()
        self.assertEqual(versionado.replace("\r\n", "\n"), self.html,
                         "rode: python web/gerar_web.py")

    def test_marcadores_substituidos(self):
        self.assertNotIn("@@", self.html)
        self.assertIn("PotterVM", self.html)

    def test_documento_completo_e_fragmento(self):
        self.assertTrue(self.html.startswith("<!doctype html>"))
        fragmento = gerar_html(ler_fonte(), documento=False)
        self.assertTrue(fragmento.startswith("<title>"))
        self.assertNotIn("<!doctype", fragmento.lower())

    def test_tac_embutido_e_o_do_compilador(self):
        m = re.search(r'<script id="tac-programa" type="application/json">(.*?)</script>', self.html, re.S)
        self.assertIsNotNone(m)
        self.assertEqual(json.loads(m.group(1)), json.loads(json.dumps(tac_para_lista(ler_fonte()))))

    def test_fonte_embutida_nao_fecha_a_tag_script(self):
        html = gerar_html('HOGWARTS T { LUMOS("</script><b>x</b>"); }', "t.potter")
        m = re.search(r'<script id="fonte-potter" type="application/json">(.*?)</script>', html, re.S)
        self.assertEqual(json.loads(m.group(1))["texto"], 'HOGWARTS T { LUMOS("</script><b>x</b>"); }')

    @unittest.skipIf(NODE is None, "node não encontrado no PATH")
    def test_scripts_da_pagina_sao_javascript_valido(self):
        scripts = re.findall(r"<script>(.*?)</script>", self.html, re.S)
        self.assertEqual(len(scripts), 2)
        with tempfile.TemporaryDirectory() as tmp:
            for i, js in enumerate(scripts):
                caminho = os.path.join(tmp, f"s{i}.js")
                with open(caminho, "w", encoding="utf-8") as f:
                    f.write(js)
                r = subprocess.run([NODE, "--check", caminho], capture_output=True, text=True)
                self.assertEqual(r.returncode, 0, r.stderr)


@unittest.skipIf(NODE is None, "node não encontrado no PATH")
class VmJavaScriptDueloTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="potter_vm_")
        cls.programa = os.path.join(cls.tmp, "duelo.json")
        with open(cls.programa, "w", encoding="utf-8") as f:
            json.dump(tac_para_lista(ler_fonte()), f)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def simular(self, *apertos, limite=9000, iniciar=True):
        args = [NODE, os.path.join(WEB, "simular_vm.js"), self.programa, str(limite)]
        args += ([INICIAR] if iniciar else []) + list(apertos)
        r = subprocess.run(args, capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        return [(int(m.group(1)), m.group(2), m.group(3))
                for m in map(EVENTO.match, r.stdout.splitlines()) if m]

    def resultado(self, eventos):
        idx = next(i for i, (_, tipo, txt) in enumerate(eventos)
                   if tipo == "SERIAL" and any(f in txt for f in ("venceu", "rapido", "EMPATE")))
        acesos = set()
        for _, tipo, txt in eventos[idx + 1:]:
            if tipo != "WRITE":
                continue
            pino, valor = map(int, txt.split())
            if valor == 0:
                break
            acesos.add(pino)
        return eventos[idx][2], acesos

    def assert_duelo(self, apertos, trecho, led):
        eventos = self.simular(*apertos)
        msg, acesos = self.resultado(eventos)
        self.assertIn(trecho, msg)
        self.assertEqual(acesos, {led})
        self.assertTrue(any(t == "SERIAL" and "proxima rodada" in x for _, t, x in eventos))

    def test_sem_iniciar_nada_acontece(self):
        eventos = self.simular(apertar(J1["expelliarmus"], 1000), limite=3000, iniciar=False)
        self.assertFalse(any("DUELO VALENDO" in x for _, _, x in eventos))
        self.assertFalse(any(t == "WRITE" for _, t, _ in eventos))

    def test_tres_piscadas_e_rodada_ativa_em_900ms(self):
        eventos = self.simular()
        piscadas = [t for t, tipo, x in eventos if tipo == "WRITE" and x == f"{LED_EMPATE} 1"]
        self.assertEqual(piscadas, [0, 300, 600])
        self.assertTrue(any(t == 900 and x == "DUELO VALENDO!" for t, _, x in eventos))

    def test_afinidade(self):
        self.assert_duelo([apertar(J1["expelliarmus"], 1200), apertar(J2["bombarda"], 1300)],
                          "J1 venceu por afinidade magica", LED_DANO_J2)
        self.assert_duelo([apertar(J1["protego"], 1200), apertar(J2["bombarda"], 1300)],
                          "J2 venceu por afinidade magica", LED_DANO_J1)

    def test_velocidade_e_janela_de_300ms(self):
        self.assert_duelo([apertar(J1["protego"], 1200), apertar(J2["protego"], 1700)],
                          "J1 foi muito mais rapido", LED_DANO_J2)
        self.assert_duelo([apertar(J1["protego"], 1200), apertar(J2["bombarda"], 1700)],
                          "J1 foi muito mais rapido", LED_DANO_J2)
        self.assert_duelo([apertar(J1["protego"], 1200), apertar(J2["protego"], 1500)],
                          "EMPATE", LED_EMPATE)

    def test_empate(self):
        self.assert_duelo([apertar(J1["bombarda"], 1200), apertar(J2["bombarda"], 1260)],
                          "EMPATE", LED_EMPATE)

    def test_so_um_aperta_vence_apos_3s(self):
        eventos = self.simular(apertar(J1["bombarda"], 1200))
        msg, acesos = self.resultado(eventos)
        self.assertIn("J2 demorou demais", msg)
        self.assertEqual(acesos, {LED_DANO_J2})

    def test_tempos_impressos_sao_os_ticks_do_programa(self):
        eventos = self.simular(apertar(J1["expelliarmus"], 1200), apertar(J2["bombarda"], 1300))
        seriais = [x for _, t, x in eventos if t == "SERIAL"]
        i = seriais.index("J1:")
        self.assertEqual(seriais[i:i + 6], ["J1:", "Expelliarmus", "300", "J2:", "Bombarda", "400"])


@unittest.skipIf(NODE is None, "node não encontrado no PATH")
class VmJavaScriptSemanticaTests(unittest.TestCase):
    """A VM em JS imprime o mesmo que o interpretador Python (potter_tac.executar)."""

    PROGRAMAS = {
        "aritmetica": "LUMOS(7 / 2); LUMOS(-7 / 2); LUMOS(-7 % 3); LUMOS(2 + 3 * 4);",
        "recursao": "INCANTATIO fat(n) { SORTILEGIO (n <= 1) { EXPELLIARMUS 1; } EXPELLIARMUS n * CAST fat(n - 1); }"
                    " LUMOS(CAST fat(6));",
        "sombra": "VARINHA GALLEON x ~> 7; INCANTATIO h() { VARINHA GALLEON x ~> 2; LUMOS(x); } CAST h(); LUMOS(x);",
        "logica": "VARINHA VERITAS a ~> ALWAYS; LUMOS(a && !NEVER); LUMOS(a == ALWAYS);"
                  " VARINHA GALLEON i ~> 0; VIRATEMPO (i < 3) { i ~> i + 1; } LUMOS(i);",
    }

    def test_mesma_saida_que_o_interpretador_python(self):
        from potter_tac import executar, gerar_tac

        def normalizar(v):
            return "1" if v is True else "0" if v is False else str(v)

        with tempfile.TemporaryDirectory() as tmp:
            for nome, corpo in self.PROGRAMAS.items():
                with self.subTest(programa=nome):
                    fonte = f"HOGWARTS T {{ {corpo} }}"
                    esperado = [normalizar(v) for v in executar(gerar_tac(fonte))]
                    caminho = os.path.join(tmp, nome + ".json")
                    with open(caminho, "w", encoding="utf-8") as f:
                        json.dump(tac_para_lista(fonte), f)
                    r = subprocess.run([NODE, os.path.join(WEB, "simular_vm.js"), caminho, "10"],
                                       capture_output=True, text=True, timeout=30)
                    self.assertEqual(r.returncode, 0, r.stderr)
                    obtido = [m.group(3) for m in map(EVENTO.match, r.stdout.splitlines()) if m]
                    self.assertEqual(obtido, esperado)


if __name__ == "__main__":
    unittest.main()
