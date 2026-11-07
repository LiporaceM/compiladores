// ======================================================
// DueloArcano.ino  --  gerado pelo compilador PotterLang
// NAO EDITE: altere o .potter e compile novamente.
// ======================================================

const int LED_DANO_J1 = 2;
const int LED_EMPATE = 3;
const int LED_DANO_J2 = 4;
const int BTN_J1_EXPELLIARMUS = 5;
const int BTN_J1_PROTEGO = 6;
const int BTN_J1_BOMBARDA = 7;
const int BTN_J2_EXPELLIARMUS = 8;
const int BTN_J2_PROTEGO = 9;
const int BTN_J2_BOMBARDA = 10;
const int BTN_INICIAR = 11;
const int NENHUMA = 0;
const int F_EXPELLIARMUS = 1;
const int F_PROTEGO = 2;
const int F_BOMBARDA = 3;
const int TICK_MS = 20;
const int JANELA_TICKS = 15;
const int LIMITE_TICKS = 150;
int escolhaJ1 = 0;
int escolhaJ2 = 0;
int tickJ1 = 0;
int tickJ2 = 0;
int tickAtual = 0;
bool rodadaAtiva = false;

// INCANTATIO apagarLeds
void apagarLeds() {
    digitalWrite(LED_DANO_J1, LOW);
    digitalWrite(LED_DANO_J2, LOW);
    digitalWrite(LED_EMPATE, LOW);
}

// INCANTATIO sinalVisual
void sinalVisual() {
    int i = 0;
    while (i < 3) {
        digitalWrite(LED_EMPATE, HIGH);
        delay(150);
        digitalWrite(LED_EMPATE, LOW);
        delay(150);
        i = (i + 1);
    }
}

// INCANTATIO iniciarRodada
void iniciarRodada() {
    apagarLeds();
    escolhaJ1 = NENHUMA;
    escolhaJ2 = NENHUMA;
    tickJ1 = 0;
    tickJ2 = 0;
    tickAtual = 0;
    sinalVisual();
    rodadaAtiva = true;
    Serial.println(F("DUELO VALENDO!"));
}

// INCANTATIO lerBotoesJ1
void lerBotoesJ1() {
    if (escolhaJ1 == NENHUMA) {
        if (digitalRead(BTN_J1_EXPELLIARMUS) == LOW) {
            escolhaJ1 = F_EXPELLIARMUS;
            tickJ1 = tickAtual;
        } else {
            if (digitalRead(BTN_J1_PROTEGO) == LOW) {
                escolhaJ1 = F_PROTEGO;
                tickJ1 = tickAtual;
            } else {
                if (digitalRead(BTN_J1_BOMBARDA) == LOW) {
                    escolhaJ1 = F_BOMBARDA;
                    tickJ1 = tickAtual;
                }
            }
        }
    }
}

// INCANTATIO lerBotoesJ2
void lerBotoesJ2() {
    if (escolhaJ2 == NENHUMA) {
        if (digitalRead(BTN_J2_EXPELLIARMUS) == LOW) {
            escolhaJ2 = F_EXPELLIARMUS;
            tickJ2 = tickAtual;
        } else {
            if (digitalRead(BTN_J2_PROTEGO) == LOW) {
                escolhaJ2 = F_PROTEGO;
                tickJ2 = tickAtual;
            } else {
                if (digitalRead(BTN_J2_BOMBARDA) == LOW) {
                    escolhaJ2 = F_BOMBARDA;
                    tickJ2 = tickAtual;
                }
            }
        }
    }
}

// INCANTATIO venceMagia
bool venceMagia(int a, int b) {
    return ((((a == F_EXPELLIARMUS) && (b == F_BOMBARDA)) || ((a == F_BOMBARDA) && (b == F_PROTEGO))) || ((a == F_PROTEGO) && (b == F_EXPELLIARMUS)));
}

// INCANTATIO mostrarFeitico
void mostrarFeitico(int id) {
    if (id == F_EXPELLIARMUS) {
        Serial.println(F("Expelliarmus"));
    } else {
        if (id == F_PROTEGO) {
            Serial.println(F("Protego"));
        } else {
            if (id == F_BOMBARDA) {
                Serial.println(F("Bombarda"));
            } else {
                Serial.println(F("Nenhum"));
            }
        }
    }
}

// INCANTATIO exibirSelecao
void exibirSelecao() {
    Serial.println(F("J1:"));
    mostrarFeitico(escolhaJ1);
    Serial.println((tickJ1 * TICK_MS));
    Serial.println(F("J2:"));
    mostrarFeitico(escolhaJ2);
    Serial.println((tickJ2 * TICK_MS));
}

// INCANTATIO validarVantagemMagica
void validarVantagemMagica() {
    if (escolhaJ1 == escolhaJ2) {
        Serial.println(F("EMPATE (Priori Incantatem)!"));
        digitalWrite(LED_EMPATE, HIGH);
    } else {
        if (venceMagia(escolhaJ1, escolhaJ2)) {
            Serial.println(F("J1 venceu por afinidade magica!"));
            digitalWrite(LED_DANO_J2, HIGH);
        } else {
            Serial.println(F("J2 venceu por afinidade magica!"));
            digitalWrite(LED_DANO_J1, HIGH);
        }
    }
}

// INCANTATIO resolverDuelo
void resolverDuelo() {
    if (escolhaJ1 == NENHUMA) {
        Serial.println(F("J1 demorou demais! J2 venceu por velocidade!"));
        digitalWrite(LED_DANO_J1, HIGH);
    } else {
        if (escolhaJ2 == NENHUMA) {
            Serial.println(F("J2 demorou demais! J1 venceu por velocidade!"));
            digitalWrite(LED_DANO_J2, HIGH);
        } else {
            int diff = (tickJ1 - tickJ2);
            if (diff < 0) {
                diff = (0 - diff);
            }
            if (diff > JANELA_TICKS) {
                if (tickJ1 < tickJ2) {
                    Serial.println(F("J1 foi muito mais rapido!"));
                    digitalWrite(LED_DANO_J2, HIGH);
                } else {
                    Serial.println(F("J2 foi muito mais rapido!"));
                    digitalWrite(LED_DANO_J1, HIGH);
                }
            } else {
                validarVantagemMagica();
            }
        }
    }
}

// INCANTATIO verificarFimRodada
void verificarFimRodada() {
    bool alguemEscolheu = ((escolhaJ1 != NENHUMA) || (escolhaJ2 != NENHUMA));
    bool ambosEscolheram = ((escolhaJ1 != NENHUMA) && (escolhaJ2 != NENHUMA));
    bool tempoEsgotado = (alguemEscolheu && (tickAtual > LIMITE_TICKS));
    if (ambosEscolheram || tempoEsgotado) {
        exibirSelecao();
        resolverDuelo();
        delay(3000);
        apagarLeds();
        rodadaAtiva = false;
        Serial.println(F("Pressione o botao 11 para a proxima rodada!"));
    }
}

void setup() {
    Serial.begin(9600);
    pinMode(BTN_INICIAR, INPUT_PULLUP);
    pinMode(BTN_J1_EXPELLIARMUS, INPUT_PULLUP);
    pinMode(BTN_J1_PROTEGO, INPUT_PULLUP);
    pinMode(BTN_J1_BOMBARDA, INPUT_PULLUP);
    pinMode(BTN_J2_EXPELLIARMUS, INPUT_PULLUP);
    pinMode(BTN_J2_PROTEGO, INPUT_PULLUP);
    pinMode(BTN_J2_BOMBARDA, INPUT_PULLUP);
    pinMode(LED_DANO_J1, OUTPUT);
    pinMode(LED_DANO_J2, OUTPUT);
    pinMode(LED_EMPATE, OUTPUT);
    Serial.println(F("--- DUELO MAGICO INICIADO ---"));
    Serial.println(F("Pressione o botao no pino 11 para iniciar!"));
}

void loop() {
    if (!rodadaAtiva) {
        if (digitalRead(BTN_INICIAR) == LOW) {
            iniciarRodada();
        }
    } else {
        lerBotoesJ1();
        lerBotoesJ2();
        verificarFimRodada();
        tickAtual = (tickAtual + 1);
        delay(TICK_MS);
    }
}
