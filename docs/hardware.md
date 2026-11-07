# Implementação prática: Duelo Arcano no Arduino UNO

Este documento descreve a montagem física do jogo **Duelo Arcano**, escrito em
PotterLang (`duelo_arcano.potter`) e compilado para `DueloArcano/DueloArcano.ino`.

> **TODO(equipe):** inserir foto da protoboard montada em `docs/img/montagem.jpg`
> e referenciá-la aqui: `![Montagem](img/montagem.jpg)`.

## 1. Pinagem

Os valores abaixo saem dos `VOTO GALLEON` do topo de `duelo_arcano.potter`.

| Pino | Constante PotterLang     | Componente                     | Modo (`pinMode`)            |
|-----:|--------------------------|--------------------------------|-----------------------------|
| 2    | `LED_DANO_J1`            | LED "dano no J1" (vermelho)    | `SAIDA` → `OUTPUT`          |
| 3    | `LED_EMPATE`             | LED "empate" (cinza/branco)    | `SAIDA` → `OUTPUT`          |
| 4    | `LED_DANO_J2`            | LED "dano no J2" (verde)       | `SAIDA` → `OUTPUT`          |
| 5    | `BTN_J1_EXPELLIARMUS`    | Botão J1 – Expelliarmus        | `ENTRADA_PULLUP` → `INPUT_PULLUP` |
| 6    | `BTN_J1_PROTEGO`         | Botão J1 – Protego             | `ENTRADA_PULLUP` → `INPUT_PULLUP` |
| 7    | `BTN_J1_BOMBARDA`        | Botão J1 – Bombarda            | `ENTRADA_PULLUP` → `INPUT_PULLUP` |
| 8    | `BTN_J2_EXPELLIARMUS`    | Botão J2 – Expelliarmus        | `ENTRADA_PULLUP` → `INPUT_PULLUP` |
| 9    | `BTN_J2_PROTEGO`         | Botão J2 – Protego             | `ENTRADA_PULLUP` → `INPUT_PULLUP` |
| 10   | `BTN_J2_BOMBARDA`        | Botão J2 – Bombarda            | `ENTRADA_PULLUP` → `INPUT_PULLUP` |
| 11   | `BTN_INICIAR`            | Botão "iniciar rodada"         | `ENTRADA_PULLUP` → `INPUT_PULLUP` |
| GND  | –                        | Terra comum de LEDs e botões   | –                           |
| USB  | –                        | Alimentação + Monitor Serial (9600 baud) | –                 |

As cores dos LEDs seguem o comentário do `.potter`.
**TODO(equipe):** confirmar as cores realmente usadas na montagem.

## 2. Lista de componentes

| Qtd | Componente                                   | Observação |
|----:|----------------------------------------------|------------|
| 1   | Arduino UNO (ATmega328P) + cabo USB          | placa-alvo `arduino:avr:uno` |
| 1   | Protoboard                                   | |
| 3   | LEDs 5 mm                                    | dano J1, empate, dano J2 |
| 3   | Resistores para os LEDs (220 Ω a 330 Ω)      | limitam a corrente em ~10–15 mA a 5 V. **TODO(equipe):** anotar o valor usado |
| 7   | Botões táteis (push-button)                  | 3 do J1, 3 do J2, 1 de iniciar |
| ~20 | Jumpers macho-macho                          | **TODO(equipe):** quantidade real |

Os botões **não precisam de resistor**: o código ativa o pull-up interno do
ATmega328P (`ENTRADA_PULLUP`). O pino fica em `ALTO` em repouso e vai para
`BAIXO` quando o botão o liga ao GND.

## 3. Esquema de ligação

```
                 ARDUINO UNO
              +---------------+
   LED J1  <--| D2            |
   LED EMP <--| D3            |        Cada LED:
   LED J2  <--| D4            |        Dn ---[220Ω]---|>|--- GND
              |               |                      anodo  catodo
 J1 Expel. ---| D5            |                     (perna longa) (curta)
 J1 Prot.  ---| D6            |
 J1 Bomb.  ---| D7            |        Cada botão:
 J2 Expel. ---| D8            |        Dn ---[ botão ]--- GND
 J2 Prot.  ---| D9            |        (pull-up interno, sem resistor)
 J2 Bomb.  ---| D10           |
 Iniciar   ---| D11           |
              |           GND |---- trilho GND da protoboard
              +---------------+
```

Dica para botões de 4 pernas: use pernas em **diagonal**, porque as pernas do
mesmo lado já vêm ligadas internamente.

## 4. Como gravar

```powershell
python compilar_e_gravar.py --listar-portas                 # descobre a porta (ex.: COM3)
python compilar_e_gravar.py duelo_arcano.potter --porta COM3
```

Depois abra o Monitor Serial a **9600 baud** (`arduino-cli monitor -p COM3 -c baudrate=9600`).

## 5. Comportamento esperado

Ao ligar, o Serial mostra `--- DUELO MAGICO INICIADO ---`. O botão **11**
inicia a rodada: o LED de empate pisca 3 vezes (≈0,9 s) e o Serial mostra
`DUELO VALENDO!`. A partir daí, a primeira tecla de cada jogador é registrada,
amostrada a cada 20 ms (1 *tick*).

Regras implementadas, na ordem em que são avaliadas (`resolverDuelo`):

1. Se só um jogador apertou e passaram mais de 150 ticks (≈3 s), ele vence.
2. Se a diferença entre os dois apertos for **maior que 15 ticks (300 ms)**, vence o mais rápido.
3. Caso contrário, vale a afinidade: **Expelliarmus > Bombarda > Protego > Expelliarmus**.
   Feitiços iguais empatam (*Priori Incantatem*).

O LED de **dano** acende do lado de quem **perdeu**. O resultado fica aceso por 3 s
e depois todos os LEDs apagam até o próximo aperto do botão 11.

## 6. Checklist de teste físico

Todos os cenários começam com: apertar **11** e esperar as 3 piscadas.
A coluna "Simulação" registra o resultado no simulador g++
(`test_simulacao_duelo.py`, ver [testes.md](testes.md)). A coluna "Placa real"
deve ser preenchida pela equipe.

| # | Ação dos jogadores                                          | LED esperado          | Mensagem no Serial                    | Simulação | Placa real |
|---|-------------------------------------------------------------|-----------------------|---------------------------------------|-----------|------------|
| 0 | Apertar botões de feitiço **sem** apertar o 11               | nenhum                | nada além do texto inicial            | ✅ passou | TODO(equipe) |
| 1 | J1 **Expelliarmus (5)** e J2 **Bombarda (10)** quase juntos  | **4** (dano J2)       | `J1 venceu por afinidade magica!`     | ✅ passou | TODO(equipe) |
| 2 | J1 **Protego (6)** e J2 **Bombarda (10)** quase juntos       | **2** (dano J1)       | `J2 venceu por afinidade magica!`     | ✅ passou | TODO(equipe) |
| 3a| J1 **Protego (6)**; J2 **Protego (9)** ~0,5 s depois         | **4** (dano J2)       | `J1 foi muito mais rapido!`           | ✅ passou | TODO(equipe) |
| 3b| J2 **Expelliarmus (8)**; J1 **Expelliarmus (5)** ~0,5 s depois | **2** (dano J1)     | `J2 foi muito mais rapido!`           | ✅ passou | TODO(equipe) |
| 4 | J1 **Bombarda (7)** e J2 **Bombarda (10)** quase juntos      | **3** (empate)        | `EMPATE (Priori Incantatem)!`         | ✅ passou | TODO(equipe) |
| 5 | Só J1 aperta **Bombarda (7)** e J2 não aperta nada           | **4** após ~3 s       | `J2 demorou demais! J1 venceu por velocidade!` | ✅ passou | TODO(equipe) |
| 6 | J1 **Protego (6)**; J2 **Bombarda (10)** ~0,5 s depois       | **4** (velocidade vence afinidade) | `J1 foi muito mais rapido!` | ✅ passou | TODO(equipe) |
| 7 | Após qualquer resultado, esperar 3 s                         | todos apagam          | `Pressione o botao 11 para a proxima rodada!` | ✅ passou | TODO(equipe) |

Antes de cada resultado, o Serial também imprime o feitiço de cada jogador e o
tempo de reação em ms (`J1:` / `Expelliarmus` / `300` ...).

**TODO(equipe):** registrar data, quem testou e observações (por exemplo, botão
com mau contato) após o teste na placa real.

## 7. Recursos do UNO (medido)

Saída de `arduino-cli compile --fqbn arduino:avr:uno DueloArcano` (arduino-cli 1.5.1, core arduino:avr 1.8.8):

```
Sketch uses 3726 bytes (11%) of program storage space. Maximum is 32256 bytes.
Global variables use 199 bytes (9%) of dynamic memory, leaving 1849 bytes for local variables. Maximum is 2048 bytes.
```

## 8. Limitações conhecidas

- O tempo é medido em ticks de 20 ms somados a um `delay`, então o tempo real de
  um tick é um pouco maior que 20 ms (inclui o tempo de execução do `loop()`).
- Se um jogador apertar dois botões ao mesmo tempo, vale a prioridade de leitura
  Expelliarmus → Protego → Bombarda (ordem dos `SORTILEGIO` em `lerBotoesJ1/J2`).
- Não há *debounce* explícito. Não é necessário porque só o primeiro aperto de
  cada jogador na rodada é registrado.
- Durante os 3 s de exibição do resultado, o `delay(3000)` bloqueia a leitura dos botões.
