"""
Teste de integração do back-end: duelo_arcano.potter -> .ino -> g++ (mock do
Arduino.h em sim/) -> executável que simula os botões e registra os LEDs.

Sem g++ no PATH, a suíte de simulação é pulada (skip).
"""
import os
import re
import shutil
import subprocess
import tempfile
import unittest

from potter_arduino import compilar

RAIZ = os.path.dirname(os.path.abspath(__file__))
SIM = os.path.join(RAIZ, "sim")
GPP = shutil.which("g++")

# Pinagem do duelo_arcano.potter
LED_DANO_J1, LED_EMPATE, LED_DANO_J2 = 2, 3, 4
J1 = {"expelliarmus": 5, "protego": 6, "bombarda": 7}
J2 = {"expelliarmus": 8, "protego": 9, "bombarda": 10}
BTN_INICIAR = 11

# Linha do tempo simulada: o botão INICIAR é apertado em t=0; o sinal visual
# (3 piscadas de 300 ms) termina em t=900 ms, quando a rodada fica ativa.
INICIAR = f"{BTN_INICIAR}:0:100"
RODADA_ATIVA_MS = 900
LIMITE_MS = 9000

EVENTO = re.compile(r"T=(\d+) (WRITE|SERIAL) (.*)")
FRASES_RESULTADO = ("venceu", "rapido", "EMPATE")


def ler_fonte():
    with open(os.path.join(RAIZ, "duelo_arcano.potter"), encoding="utf-8") as f:
        return f.read()


def apertar(pino, inicio_ms, duracao_ms=100):
    return f"{pino}:{inicio_ms}:{inicio_ms + duracao_ms}"


class InoVersionadoTests(unittest.TestCase):
    def test_ino_versionado_e_identico_ao_gerado(self):
        """Garante que DueloArcano.ino não foi editado à mão nem está desatualizado."""
        _, gerado, _ = compilar(ler_fonte())
        with open(os.path.join(RAIZ, "DueloArcano", "DueloArcano.ino"), encoding="utf-8") as f:
            versionado = f.read()
        self.assertEqual(versionado.replace("\r\n", "\n").strip(), gerado.strip())


@unittest.skipIf(GPP is None, "g++ não encontrado no PATH")
class SimulacaoDueloTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="potter_sim_")
        _, ino, _ = compilar(ler_fonte())
        ino_path = os.path.join(cls.tmp, "DueloArcano.ino")
        with open(ino_path, "w", encoding="utf-8") as f:
            f.write(ino)
        cls.exe = os.path.join(cls.tmp, "sim.exe")
        r = subprocess.run(
            [GPP, "-std=c++17", "-Wall", "-I", SIM, "-include", "Arduino.h",
             "-x", "c++", ino_path, "-x", "none", os.path.join(SIM, "sim_main.cpp"),
             "-o", cls.exe],
            capture_output=True, text=True,
        )
        if r.returncode != 0:
            raise AssertionError("g++ falhou ao compilar o .ino gerado:\n" + r.stderr)
        cls.avisos_gpp = r.stderr

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def simular(self, *apertos):
        r = subprocess.run([self.exe, str(LIMITE_MS), INICIAR, *apertos],
                           capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        eventos = []
        for linha in r.stdout.splitlines():
            m = EVENTO.match(linha)
            if m:
                eventos.append((int(m.group(1)), m.group(2), m.group(3)))
        return eventos

    def resultado(self, eventos):
        """(mensagem do resultado, conjunto de LEDs acesos logo após ela)."""
        idx = next(i for i, (_, tipo, txt) in enumerate(eventos)
                   if tipo == "SERIAL" and any(f in txt for f in FRASES_RESULTADO))
        msg = eventos[idx][2]
        acesos = set()
        for _, tipo, txt in eventos[idx + 1:]:
            if tipo != "WRITE":
                continue
            pino, valor = map(int, txt.split())
            if valor == 0:
                break  # apagarLeds() após os 3 s de exibição
            acesos.add(pino)
        return msg, acesos

    def assert_duelo(self, apertos, trecho_msg, led_esperado):
        eventos = self.simular(*apertos)
        msg, acesos = self.resultado(eventos)
        self.assertIn(trecho_msg, msg)
        self.assertEqual(acesos, {led_esperado})
        # depois do resultado os LEDs são apagados e a rodada termina
        self.assertTrue(any(t == "SERIAL" and "proxima rodada" in x for _, t, x in eventos))

    def test_compila_sem_avisos_do_gpp(self):
        self.assertEqual(self.avisos_gpp.strip(), "")

    def test_sem_iniciar_nada_acontece(self):
        r = subprocess.run([self.exe, "3000", apertar(J1["expelliarmus"], 1000)],
                           capture_output=True, text=True, timeout=30)
        self.assertNotIn("DUELO VALENDO", r.stdout)
        self.assertNotIn("WRITE", r.stdout)

    def test_rodada_inicia_com_tres_piscadas_do_led_de_empate(self):
        eventos = self.simular()
        piscadas = [t for t, tipo, x in eventos if tipo == "WRITE" and x == f"{LED_EMPATE} 1"]
        self.assertEqual(piscadas, [0, 300, 600])
        self.assertTrue(any(t == RODADA_ATIVA_MS and x == "DUELO VALENDO!" for t, _, x in eventos))

    # ----- os 4 cenários pedidos -----
    def test_expelliarmus_vence_bombarda_j1_vence(self):
        self.assert_duelo(
            [apertar(J1["expelliarmus"], 1200), apertar(J2["bombarda"], 1300)],
            "J1 venceu por afinidade magica", LED_DANO_J2)

    def test_bombarda_vence_protego_j2_vence(self):
        self.assert_duelo(
            [apertar(J1["protego"], 1200), apertar(J2["bombarda"], 1300)],
            "J2 venceu por afinidade magica", LED_DANO_J1)

    def test_mesmo_feitico_com_mais_de_300ms_vence_o_mais_rapido(self):
        self.assert_duelo(
            [apertar(J1["protego"], 1200), apertar(J2["protego"], 1700)],
            "J1 foi muito mais rapido", LED_DANO_J2)
        self.assert_duelo(
            [apertar(J2["expelliarmus"], 1200), apertar(J1["expelliarmus"], 1700)],
            "J2 foi muito mais rapido", LED_DANO_J1)

    def test_feiticos_iguais_dentro_da_janela_empatam(self):
        self.assert_duelo(
            [apertar(J1["bombarda"], 1200), apertar(J2["bombarda"], 1260)],
            "EMPATE", LED_EMPATE)

    # ----- regras complementares -----
    def test_vantagem_de_exatamente_300ms_nao_conta_como_velocidade(self):
        self.assert_duelo(
            [apertar(J1["protego"], 1200), apertar(J2["protego"], 1500)],
            "EMPATE", LED_EMPATE)

    def test_vantagem_de_velocidade_supera_afinidade(self):
        # J2 teria vantagem (Bombarda > Protego), mas J1 foi 500 ms mais rápido
        self.assert_duelo(
            [apertar(J1["protego"], 1200), apertar(J2["bombarda"], 1700)],
            "J1 foi muito mais rapido", LED_DANO_J2)

    def test_so_um_jogador_aperta_vence_apos_3s(self):
        eventos = self.simular(apertar(J1["bombarda"], 1200))
        msg, acesos = self.resultado(eventos)
        self.assertIn("J2 demorou demais", msg)
        self.assertEqual(acesos, {LED_DANO_J2})
        t_msg = next(t for t, tipo, x in eventos if "demorou" in x)
        self.assertGreater(t_msg - RODADA_ATIVA_MS, 3000)


PROGRAMAS_DE_BORDA = {
    "MesmoNomeEmBlocos": 'INCANTATIO g(v) { LUMOS(v); } SORTILEGIO (ALWAYS) { VARINHA SICKLE x ~> 1.5; CAST g(x); }'
                         ' SENAO { VARINHA PARCHMENT x ~> "a"; LUMOS(x); }',
    "SombraDeGlobal": "VARINHA GALLEON x ~> 7; INCANTATIO h() { LUMOS(x % 2);"
                      " SORTILEGIO (ALWAYS) { VARINHA SICKLE x ~> 2.5; LUMOS(x % 2.0); } } CAST h();",
    "Recursao": "INCANTATIO fat(n) { SORTILEGIO (n <= 1) { EXPELLIARMUS 1; } EXPELLIARMUS n * CAST fat(n - 1); }"
                " LUMOS(CAST fat(5));",
    "RetornoNosDoisRamos": "INCANTATIO f(x) { SORTILEGIO (x > 0) { EXPELLIARMUS 1.5; } SENAO { EXPELLIARMUS 2.5; } }"
                           " LUMOS(CAST f(3));",
    "NomesDeMacros": "VOTO GALLEON B1 ~> 2; VOTO GALLEON DEC ~> 3; INCANTATIO init() { LUMOS(B1 + DEC); } CAST init();",
    "LimitesGalleon": "VARINHA GALLEON a ~> 32767; VARINHA GALLEON b ~> -32768; LUMOS(a); LUMOS(b);",
    "StringsEspeciais": 'LUMOS("aspas \\ barra ?? trigrafo\ttab Grifinória 100%");',
    "TextoEVeritas": 'INCANTATIO saudar(nome, ok) { SORTILEGIO (ok) { LUMOS(nome); } }'
                     ' CAST saudar("Harry", ALWAYS);',
}


@unittest.skipIf(GPP is None, "g++ não encontrado no PATH")
class ProgramasDeBordaCompilamTests(unittest.TestCase):
    """O C++ gerado para casos-limite válidos compila com g++ estrito (sem -fpermissive)."""

    def test_programas_de_borda_compilam(self):
        with tempfile.TemporaryDirectory(prefix="potter_borda_") as tmp:
            for nome, corpo in PROGRAMAS_DE_BORDA.items():
                with self.subTest(programa=nome):
                    _, ino, _ = compilar(f"HOGWARTS {nome} {{ {corpo} }}")
                    caminho = os.path.join(tmp, nome + ".ino")
                    with open(caminho, "w", encoding="utf-8") as f:
                        f.write(ino)
                    r = subprocess.run(
                        [GPP, "-std=c++17", "-Wall", "-Werror=return-type", "-I", SIM,
                         "-include", "Arduino.h", "-x", "c++", caminho, "-x", "none",
                         os.path.join(SIM, "sim_main.cpp"), "-o", os.path.join(tmp, nome + ".exe")],
                        capture_output=True, text=True)
                    self.assertEqual(r.returncode, 0, r.stderr)


CLI = shutil.which("arduino-cli") or next(
    (c for c in (r"C:\Program Files\Arduino CLI\arduino-cli.exe",) if os.path.isfile(c)), None)


@unittest.skipIf(CLI is None, "arduino-cli não encontrado")
class ArduinoCliTests(unittest.TestCase):
    def test_duelo_compila_para_o_uno(self):
        r = subprocess.run([CLI, "compile", "--fqbn", "arduino:avr:uno", os.path.join(RAIZ, "DueloArcano")],
                           capture_output=True, text=True, timeout=600)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("Sketch uses", r.stdout)


if __name__ == "__main__":
    unittest.main()
