# Guia: jogando o Duelo Arcano no Arduino

Este guia é para quem vai montar, testar, gravar ou apresentar o jogo na placa.
Os detalhes técnicos (esquema elétrico, consumo de memória, checklist completo)
estão em [hardware.md](hardware.md).

## 1. Como as peças se encaixam

```
duelo_arcano.potter              o jogo, escrito em PotterLang
        │  python potter_arduino.py duelo_arcano.potter
        ▼
DueloArcano/DueloArcano.ino      C++ gerado pelo nosso compilador (não editar à mão)
        │  arduino-cli compile + upload   (compilar_e_gravar.py ou a Potter IDE)
        ▼
Arduino UNO + protoboard         7 botões de entrada, 3 LEDs de saída, mensagens no Serial
```

Depois de gravada, a placa roda o jogo sozinha e só precisa de energia (cabo USB ou
fonte). O computador serve para gravar o programa e para ler o Monitor Serial.

O jogo web ([web/duelo_arcano.html](../web/duelo_arcano.html)) executa o mesmo
programa numa placa virtual, com os mesmos pinos e LEDs. Hoje ele **não se comunica**
com a placa física: apertar um botão na protoboard não mexe na página, e vice-versa
(ver a [seção 9](#9-placa-física-e-jogo-web)).

## 2. Material

| Qtd | Item | Para quê |
|----:|------|----------|
| 1 | Arduino UNO + cabo USB | roda o jogo; o USB alimenta a placa e leva o Serial |
| 1 | Protoboard | montagem sem solda |
| 3 | LEDs (vermelho, cinza ou branco, verde) | resultado da rodada |
| 3 | Resistores de 220 Ω a 330 Ω | um em série com cada LED |
| 7 | Botões táteis (push-button) | 3 do J1, 3 do J2, 1 de iniciar |
| ~20 | Jumpers | ligações |

Os botões **não levam resistor**. O programa liga o resistor de pull-up que já existe
dentro do Arduino (`ENTRADA_PULLUP` no `.potter`, `INPUT_PULLUP` no C++).

## 3. Montagem

### 3.1 Pinagem

Os números saem das constantes `VOTO GALLEON` do topo de `duelo_arcano.potter`.

| Pino | Peça | Função no jogo |
|-----:|------|----------------|
| 2 | LED vermelho | acende quando o **J1 perde** a rodada |
| 3 | LED cinza/branco | pisca 3 vezes na contagem; aceso no fim = **empate** |
| 4 | LED verde | acende quando o **J2 perde** a rodada |
| 5 | Botão | J1 · Expelliarmus |
| 6 | Botão | J1 · Protego |
| 7 | Botão | J1 · Bombarda |
| 8 | Botão | J2 · Expelliarmus |
| 9 | Botão | J2 · Protego |
| 10 | Botão | J2 · Bombarda |
| 11 | Botão | iniciar a rodada |
| GND | trilho da protoboard | terra comum de todos os LEDs e botões |

### 3.2 LEDs

```
pino ──[ resistor 220–330 Ω ]──► perna longa do LED (ânodo)
                                 perna curta do LED (cátodo) ──► GND
```

LED ao contrário não queima, só não acende. Se um LED não acender, gire-o primeiro.

### 3.3 Botões

```
pino ──[ botão ]── GND
```

Os botões de 4 pernas têm as pernas ligadas aos pares por dentro. Use duas pernas em
**diagonal**, uma para o fio do pino e outra para o GND, e coloque o botão
atravessando o canal central da protoboard. Se as duas pernas usadas forem do mesmo
par, o pino fica sempre no GND e o jogo acha que o botão está apertado o tempo todo.

### 3.4 GND

Ligue um pino **GND** do Arduino ao trilho de terra da protoboard e leve até ele o
cátodo de cada LED e a segunda perna de cada botão. Se usar os trilhos de cima e de
baixo, ligue um ao outro com um fio. Algumas protoboards também têm o trilho cortado
no meio, e aí as duas metades precisam de uma ponte.

### 3.5 Dicas de organização

- Uma ordem que facilita jogar, da esquerda para a direita: J1 Expelliarmus, J1
  Protego, J1 Bombarda, **Iniciar**, J2 Expelliarmus, J2 Protego, J2 Bombarda. Cada
  jogador fica de um lado da protoboard.
- Cole uma etiqueta em cada botão (E, P, B e "Iniciar"). Na apresentação, ninguém
  precisa decorar os pinos.
- Use a mesma ordem de cores dos LEDs da tabela (vermelho, cinza, verde) para que o
  lado do LED combine com o lado do jogador que perdeu.

## 4. Testar no Tinkercad, sem placa

O Tinkercad simula o Arduino rodando o código que o nosso compilador gera:

1. Abra [DueloArcano/DueloArcano.ino](../DueloArcano/DueloArcano.ino) e copie todo o conteúdo.
2. No circuito do Tinkercad, clique em **Código**, troque **Blocos** por **Texto** e
   aceite apagar os blocos.
3. Apague o exemplo e cole o código copiado.
4. Clique em **Iniciar simulação**.
5. Abra o **Monitor serial**, na parte de baixo do painel de código. Deve aparecer
   `--- DUELO MAGICO INICIADO ---`.
6. Clique no botão do pino 11, espere as 3 piscadas do LED cinza e clique nos botões
   dos jogadores.

Para descobrir em que pino cada fio entra, passe o mouse sobre o fio ou sobre o pino
do Arduino. Se um botão não fizer nada ou o LED errado acender, compare com a
[tabela de pinagem](#31-pinagem).

Sempre que o `.potter` mudar, gere o `.ino` de novo e cole outra vez no Tinkercad.
O relógio da simulação pode andar mais devagar que o real, então os tempos de reação
no Tinkercad não são confiáveis. As regras continuam valendo.

## 5. Gravar na placa real

Pré-requisito: `arduino-cli` e o core do UNO instalados (passo a passo no
[README](../README.md#1-instalação-windows)). Conecte a placa no USB e escolha uma
das opções:

**Pela Potter IDE**

```powershell
python potter_ide.py duelo_arcano.potter
```

Escolha a porta na lista (o botão ↻ atualiza) e clique em **🔥 Gravar na placa** (F9).

**Pela linha de comando**

```powershell
python compilar_e_gravar.py --listar-portas                  # descobre a porta, ex.: COM3
python compilar_e_gravar.py duelo_arcano.potter --porta COM3
```

**Pela Arduino IDE**

Abra `DueloArcano/DueloArcano.ino`, escolha **Ferramentas > Placa > Arduino Uno** e a
porta em **Ferramentas > Porta**, e clique em **Carregar**.

Para ver as mensagens, abra o Monitor Serial a **9600 baud**:

```powershell
arduino-cli monitor -p COM3 -c baudrate=9600
```

Ou use **Ferramentas > Monitor Serial** na Arduino IDE. Só um programa por vez usa
a porta COM: feche o Monitor Serial antes de gravar de novo.

## 6. Jogando

Cada jogador fica com os seus 3 botões. Uma rodada funciona assim:

1. Aperte **Iniciar** (pino 11).
2. O LED cinza pisca 3 vezes (cerca de 0,9 s). Espere.
3. Logo depois da terceira piscada, o Serial mostra `DUELO VALENDO!`: cada jogador
   aperta **um** feitiço.
4. O resultado aparece na hora e o LED fica aceso por 3 s:

| LED aceso | Significa |
|-----------|-----------|
| vermelho (pino 2) | o J1 perdeu a rodada |
| verde (pino 4) | o J2 perdeu a rodada |
| cinza (pino 3) | empate (*Priori Incantatem*) |

5. Os LEDs apagam. Aperte Iniciar para a próxima rodada.

### Regras

Avaliadas nesta ordem:

1. Se só um jogador apertou e passaram 3 s desde o `DUELO VALENDO!`, ele vence.
2. Se um jogador apertou **mais de 300 ms** antes do outro, ele vence pela
   velocidade, seja qual for o feitiço.
3. Se a diferença foi de até 300 ms, vale a afinidade:
   **Expelliarmus vence Bombarda, Bombarda vence Protego, Protego vence Expelliarmus.**
   Feitiços iguais empatam.

O programa não conta vidas nem placar. Cada rodada é independente, e quem estiver
jogando combina o placar (por exemplo, melhor de 5).

### O que aparece no Monitor Serial

Exemplo de uma rodada (J1 Expelliarmus, J2 Bombarda):

```
DUELO VALENDO!
J1:
Expelliarmus
300
J2:
Bombarda
400
J1 venceu por afinidade magica!
Pressione o botao 11 para a proxima rodada!
```

Os números são o tempo de reação de cada jogador, em ms, contado a partir de
`DUELO VALENDO!`. São sempre múltiplos de 20, porque a placa lê os botões a cada
20 ms (1 *tick*).

### Comportamentos que vale conhecer

- **Só o primeiro botão de cada jogador conta.** Apertar outro depois não muda nada.
- **Apertar durante as piscadas não conta**, porque a placa ainda não está lendo os
  botões dos jogadores. Mas **segurar** um botão desde a contagem conta como 0 ms
  assim que a rodada começa: a placa lê se o botão *está* apertado, e não o momento
  em que foi apertado. Na apresentação, combinem de soltar tudo antes do Iniciar.
  Para impedir isso no programa, o `.potter` precisaria exigir que o botão estivesse
  solto no começo da rodada.
- **Se ninguém apertar nada, a rodada não termina.** O limite de 3 s conta desde o
  `DUELO VALENDO!`, mas só encerra a rodada se alguém já tiver lançado. Para sair,
  alguém aperta um feitiço ou usa o botão de reset do Arduino.
- **O botão de reset da placa** (o botão vermelho no Arduino) reinicia o jogo do zero.
- Durante os 3 s em que o resultado fica aceso, os botões são ignorados.

## 7. Problemas comuns

| Sintoma | Causa provável | O que fazer |
|---------|----------------|-------------|
| Monitor Serial vazio ou com caracteres estranhos | velocidade diferente de 9600 | configure o monitor em 9600 baud |
| Um LED nunca acende | LED invertido, resistor fora da fileira certa ou fio no pino errado | gire o LED; confira resistor e pino |
| Um botão não faz nada | pernas do mesmo par, fio no pino errado ou perna sem GND | use pernas em diagonal; confira o pino e o trilho GND |
| A rodada começa sozinha | o botão do pino 11 está sempre ligado ao GND | reposicione o botão (pernas em diagonal) |
| Um jogador sempre vence com 0 ms | botão dele preso ou ligado direto ao GND, ou alguém segurando o botão desde a contagem | confira a montagem do botão; soltar antes do Iniciar |
| Gravação falha com "porta ocupada" ou "acesso negado" | Monitor Serial ou outro programa usando a porta | feche o monitor e grave de novo |
| A porta não aparece na lista | cabo só de energia, sem dados, ou driver faltando | troque o cabo; reconecte; rode `--listar-portas` de novo |
| `arduino-cli` não encontrado | não instalado ou terminal aberto antes da instalação | instale (README) e abra um terminal novo |

## 8. Mudando o jogo

Toda mudança começa no `duelo_arcano.potter`, nunca no `.ino`:

1. Edite o `.potter`. As constantes do topo controlam o jogo:
   - pinos: `LED_DANO_J1`, `BTN_J1_EXPELLIARMUS` etc.;
   - `TICK_MS`: intervalo de leitura dos botões (20 ms);
   - `JANELA_TICKS`: janela da afinidade, em ticks (15 × 20 ms = 300 ms);
   - `LIMITE_TICKS`: duração máxima da rodada, contada desde o `DUELO VALENDO!`
     (150 × 20 ms = 3 s); só encerra a rodada se alguém já tiver lançado.
2. Gere o `.ino` de novo: `python potter_arduino.py duelo_arcano.potter`.
3. Grave na placa (seção 5) ou cole no Tinkercad (seção 4).
4. Atualize o jogo web: `python web/gerar_web.py`.
5. Rode os testes: `python -m unittest`.

Exemplo: para passar o LED vermelho para o pino 12, troque
`VOTO GALLEON LED_DANO_J1 ~> 2;` por `~> 12;`, mude o fio na protoboard e grave de novo.

## 9. Placa física e jogo web

| | Placa (Arduino + protoboard) | Jogo web (`web/duelo_arcano.html`) |
|---|---|---|
| Programa | `DueloArcano.ino`, gerado do `.potter` | TAC gerado do mesmo `.potter`, executado numa VM em JavaScript |
| Botões | botões físicos nos pinos 5 a 11 | cartas clicáveis ou teclado; no torneio, o oponente é o computador |
| Resultado | LEDs nos pinos 2, 3 e 4 + Monitor Serial | animações; o painel **Placa** mostra os mesmos LEDs e o Serial |
| Extras | só as rodadas | vidas, oponentes, pontos e estrelas (ficam na página, fora do `.potter`) |

Uma evolução possível: o Arduino já manda pelo USB as mesmas mensagens que a página
usa para animar (`DUELO VALENDO!`, `J1:`, feitiços, tempos e resultado). Uma versão
local da página, aberta no Chrome ou no Edge, poderia ler a porta USB pela Web Serial
e animar o que acontece na protoboard. Isso não funciona no Tinkercad, que é só
simulação.

## 10. Depois de testar na placa

- Preencha a coluna **Placa real** do checklist em [hardware.md](hardware.md#6-checklist-de-teste-físico),
  com data, quem testou e observações.
- Tire uma foto da protoboard montada, salve em `docs/img/montagem.jpg` e coloque
  o link em `hardware.md`, onde há um `TODO(equipe)`.
