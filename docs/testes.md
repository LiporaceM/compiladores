# Testes automatizados

Os testes usam só `unittest`, da biblioteca padrão. Para rodar tudo a partir da raiz do repositório:

```powershell
python -m unittest            # descobre todos os test_*.py
python -m unittest -v         # mostra cada teste
python -m unittest test_simulacao_duelo -v   # só uma suíte
```

Resultado em 07/11/2026 (Windows 11, Python 3.13.14, g++ 16.2.0, arduino-cli 1.5.1):

```
Ran 142 tests in 14.517s

OK
```

## Suítes

| Arquivo | Testes | O que cobre |
|---------|------:|-------------|
| [test_potter_lang.py](../test_potter_lang.py) | 24 | **Front-end (núcleo).** Léxico: todos os tokens, comentários, números, Unicode e erros léxicos. Parser: precedência, nós unários, tokens sobrando, falta de `;`. Semântico: escopos, VOTO, tipos, condições, aridade, `EXPELLIARMUS` fora de feitiço. Também confere linha **e coluna** nas mensagens e nos nós da AST |
| [test_potter_arduino.py](../test_potter_arduino.py) | 52 | **Back-end.** Extensões (CAST em expressão, constantes nativas); tradução para C++ (setup/loop, Serial, tipos, parênteses, `fmod`, nomes reservados, escape de strings); inferência de assinaturas e rechecagem de operadores com os tipos inferidos; casos-limite da Etapa de endurecimento (retorno em um ramo só, retornos de tipos diferentes, função sem retorno em expressão, mesmo nome em blocos, GALLEON fora da faixa, macros do Arduino, identificadores com acento, parâmetro não usado); CLI (`--tokens/--ast/--tabela/--stdout`); pinagem e regras do Duelo Arcano |
| [test_simulacao_duelo.py](../test_simulacao_duelo.py) | 13 | **Integração com C++ real.** Garante que o `.ino` versionado é idêntico ao gerado. Compila o `.ino` com **g++** contra o mock [sim/Arduino.h](../sim/Arduino.h) e roda [sim/sim_main.cpp](../sim/sim_main.cpp) com botões simulados (seção abaixo). Compila programas de borda com g++ (`-Werror=return-type`) e compila o duelo com **arduino-cli** para o UNO |
| [test_potter_api.py](../test_potter_api.py) | 20 | **Lógica da IDE** ([potter_api.py](../potter_api.py)): tokens, AST, tabela e `.ino` do duelo; diagnósticos com fase, linha e coluna para cada tipo de erro; nenhuma exceção escapa; todos os `exemplos/` válidos compilam sem aviso e todos os `exemplos/erros/` falham com posição; realce de sintaxe; leitura das portas do arduino-cli |
| [test_potter_ide.py](../test_potter_ide.py) | 5 | **Interface Tkinter (fumaça).** Abre a IDE de verdade (janela oculta), carrega o duelo, aplica o realce, executa o fluxo Tokens → AST → Tabela → Compilar, clica num erro e confere que o cursor vai para a linha, edita e salva |
| [test_web.py](../test_web.py) | 14 | **Jogo web** ([web/](../web/)). Confere que a página embute o TAC do compilador, que o `web/duelo_arcano.html` versionado é idêntico ao gerado e que os scripts são JavaScript válido. Roda os cenários do duelo na VM de TAC em JavaScript via **Node** ([web/simular_vm.js](../web/simular_vm.js), mesma interface do `sim_main.cpp`) e compara a saída da VM com a do interpretador Python em programas de teste |
| [test_potter_tac.py](../test_potter_tac.py) | 28 | **Código de três endereços** ([tac.md](tac.md)): formato de cada construção, curto-circuito, ordem dos `param`, nomes únicos por escopo; um interpretador de TAC confere os resultados (recursão, divisão como no C, saída do exemplo Grifinória); integridade do TAC do duelo (rótulos e chamadas) |

## Simulação do Duelo Arcano

O simulador tem tempo virtual: `delay()` só avança o relógio, e `digitalRead()` devolve `LOW`
enquanto o botão está "apertado" na linha do tempo do cenário. Cada `digitalWrite` e
`Serial.println` é registrado com o instante em que ocorreu, e o teste confere qual LED de
resultado acendeu e qual mensagem saiu.

| Teste | Cenário | Esperado |
|-------|---------|----------|
| `test_sem_iniciar_nada_acontece` | feitiços sem apertar o 11 | nenhum LED |
| `test_rodada_inicia_com_tres_piscadas_do_led_de_empate` | aperta 11 | LED 3 pisca 3× |
| `test_expelliarmus_vence_bombarda_j1_vence` | J1 Expelliarmus × J2 Bombarda | LED 4 (dano J2) |
| `test_bombarda_vence_protego_j2_vence` | J1 Protego × J2 Bombarda | LED 2 (dano J1) |
| `test_mesmo_feitico_com_mais_de_300ms_vence_o_mais_rapido` | mesmo feitiço, > 300 ms de diferença | vence o mais rápido |
| `test_feiticos_iguais_dentro_da_janela_empatam` | mesmo feitiço, quase juntos | LED 3 (empate) |
| `test_vantagem_de_exatamente_300ms_nao_conta_como_velocidade` | mesmo feitiço (Protego), diferença de exatamente 300 ms | LED 3 (empate): só **mais de** 300 ms conta |
| `test_vantagem_de_velocidade_supera_afinidade` | feitiço "perdedor" > 300 ms antes | vence por velocidade |
| `test_so_um_jogador_aperta_vence_apos_3s` | só J1 aperta | J1 vence após 3 s |
| `test_compila_sem_avisos_do_gpp` | – | o `.ino` compila com `g++ -std=c++17 -Wall` sem avisos |

Isso valida a **lógica** gerada pelo compilador. O comportamento elétrico (fiação, pull-ups,
LEDs) só é verificado na placa: ver o checklist em [hardware.md](hardware.md).

## Testes que dependem do ambiente

| Requisito | Suítes afetadas | Sem o requisito |
|-----------|-----------------|-----------------|
| `g++` no PATH | `SimulacaoDueloTests`, `ProgramasDeBordaCompilamTests` | pulados (`skipped`) |
| `arduino-cli` + core `arduino:avr` | `ArduinoCliTests` | pulado |
| Tkinter e uma tela | `PotterIDETests` | pulado |
| `node` no PATH | `VmJavaScriptDueloTests`, `VmJavaScriptSemanticaTests` e a checagem de sintaxe da página | pulados |

Nenhum teste grava na placa: a gravação (`compilar_e_gravar.py --porta COMx`) é sempre manual.

## Como adicionar um teste

1. Para um bug, escreva primeiro o teste que falha (por exemplo, em `EndurecimentoTests` de
   `test_potter_arduino.py`) usando `compilar(fonte)` ou `assertRaises`.
2. Corrija o compilador.
3. Rode `python -m unittest`. Se o `.ino` do duelo mudar, regenere com
   `python potter_arduino.py duelo_arcano.potter` (o teste `test_ino_versionado_e_identico_ao_gerado`
   acusa se você esquecer).
