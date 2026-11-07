// =====================================================================
// Arduino.h  --  MOCK para simular sketches gerados pela PotterLang no PC
//
// Usado apenas pelos testes (test_simulacao_duelo.py). Implementa o
// subconjunto da API do Arduino que o transpilador gera, com tempo virtual:
//   * delay(ms) avanca o relogio simulado (nao espera de verdade);
//   * digitalRead(pino) devolve LOW enquanto um botao roteirizado esta
//     pressionado (botoes ligados ao GND com INPUT_PULLUP);
//   * digitalWrite e Serial.println geram um log de eventos na saida padrao:
//         T=<ms> WRITE <pino> <0|1>
//         T=<ms> SERIAL <texto>
// Limitacao conhecida: aqui 'int' tem 32 bits (no UNO tem 16).
// =====================================================================
#ifndef POTTER_ARDUINO_MOCK_H
#define POTTER_ARDUINO_MOCK_H

#include <cmath>
#include <cstdio>
#include <string>

#define HIGH 1
#define LOW 0
#define INPUT 0
#define OUTPUT 1
#define INPUT_PULLUP 2
#define LED_BUILTIN 13
#define F(texto) (texto)

using std::fmod;

class String : public std::string {
public:
    String() {}
    String(const char *s) : std::string(s) {}
    String(const std::string &s) : std::string(s) {}
};

extern unsigned long sim_ms;

void pinMode(int pino, int modo);
void digitalWrite(int pino, int valor);
int digitalRead(int pino);
int analogRead(int pino);
void analogWrite(int pino, int valor);
void delay(unsigned long ms);
unsigned long millis();

class SerialMock {
public:
    void begin(long) {}
    void println(const char *s) { std::printf("T=%lu SERIAL %s\n", sim_ms, s); }
    void println(const String &s) { println(s.c_str()); }
    void println(int v) { std::printf("T=%lu SERIAL %d\n", sim_ms, v); }
    void println(long v) { std::printf("T=%lu SERIAL %ld\n", sim_ms, v); }
    void println(unsigned long v) { std::printf("T=%lu SERIAL %lu\n", sim_ms, v); }
    void println(double v) { std::printf("T=%lu SERIAL %.2f\n", sim_ms, v); }
    void println(bool v) { println(v ? 1 : 0); }
};
extern SerialMock Serial;

void setup();
void loop();

#endif
