// =====================================================================
// sim_main.cpp  --  laco principal do simulador (setup() + loop()).
//
// Uso:  sim.exe <limite_ms> [pino:inicio_ms:fim_ms ...]
//   Cada evento mantem o botao do <pino> pressionado (nivel LOW) no
//   intervalo [inicio_ms, fim_ms). A simulacao termina em <limite_ms>.
// =====================================================================
#include "Arduino.h"

#include <cstdlib>
#include <vector>

unsigned long sim_ms = 0;
SerialMock Serial;

namespace {
struct Pressao {
    int pino;
    unsigned long inicio, fim;
};
std::vector<Pressao> roteiro;
int estado_saida[64] = {0};
}

void pinMode(int, int) {}

void digitalWrite(int pino, int valor) {
    if (pino >= 0 && pino < 64 && estado_saida[pino] != valor) {
        estado_saida[pino] = valor;
        std::printf("T=%lu WRITE %d %d\n", sim_ms, pino, valor ? 1 : 0);
    }
}

int digitalRead(int pino) {
    for (const Pressao &p : roteiro) {
        if (p.pino == pino && sim_ms >= p.inicio && sim_ms < p.fim) {
            return LOW;  // botao no GND
        }
    }
    return HIGH;  // pull-up
}

int analogRead(int) { return 0; }
void analogWrite(int, int) {}
void delay(unsigned long ms) { sim_ms += ms; }
unsigned long millis() { return sim_ms; }

int main(int argc, char **argv) {
    if (argc < 2) {
        std::fprintf(stderr, "uso: %s <limite_ms> [pino:inicio:fim ...]\n", argv[0]);
        return 2;
    }
    unsigned long limite = std::strtoul(argv[1], nullptr, 10);
    for (int i = 2; i < argc; ++i) {
        Pressao p{};
        if (std::sscanf(argv[i], "%d:%lu:%lu", &p.pino, &p.inicio, &p.fim) != 3) {
            std::fprintf(stderr, "evento invalido: %s\n", argv[i]);
            return 2;
        }
        roteiro.push_back(p);
    }

    setup();
    while (sim_ms < limite) {
        unsigned long antes = sim_ms;
        loop();
        if (sim_ms == antes) {
            sim_ms += 1;  // loop() sem delay: avanca 1 ms para o tempo andar
        }
    }
    return 0;
}
