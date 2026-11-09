/*
 * simular_vm.js  --  simulador de linha de comando para a VM de TAC (tac_vm.js).
 *
 * Mesma interface e mesma saida de sim/sim_main.cpp, para os testes poderem rodar
 * os cenarios do Duelo Arcano sem g++:
 *
 *   node web/simular_vm.js <programa.json> <limite_ms> [pino:inicio_ms:fim_ms ...]
 *
 * Saida:  T=<ms> WRITE <pino> <0|1>   e   T=<ms> SERIAL <texto>
 */
'use strict';
const fs = require('fs');
const path = require('path');
const { PotterVM } = require(path.join(__dirname, 'tac_vm.js'));

const [arquivo, limiteTxt, ...eventos] = process.argv.slice(2);
if (!arquivo || !limiteTxt) {
  console.error('uso: node simular_vm.js <programa.json> <limite_ms> [pino:inicio:fim ...]');
  process.exit(2);
}
const programa = JSON.parse(fs.readFileSync(arquivo, 'utf8'));
const limite = Number(limiteTxt);
const roteiro = eventos.map((e) => {
  const [pino, inicio, fim] = e.split(':').map(Number);
  return { pino, inicio, fim };
});

let ms = 0;
const saidas = {};
const linhas = [];
const vm = new PotterVM(programa, {
  imprimir: (v) => linhas.push(`T=${ms} SERIAL ${typeof v === 'boolean' ? (v ? 1 : 0) : v}`),
  primitivas: {
    pinMode() {},
    digitalWrite(pino, valor) {
      const v = valor ? 1 : 0;
      if (saidas[pino] !== v) {
        saidas[pino] = v;
        linhas.push(`T=${ms} WRITE ${pino} ${v}`);
      }
    },
    digitalRead(pino) {
      return roteiro.some((p) => p.pino === pino && ms >= p.inicio && ms < p.fim) ? 0 : 1;
    },
    analogRead: () => 0,
    analogWrite() {},
    delay() {},
    millis: () => ms,
  },
});

// Como o sim_main.cpp: delay avanca o relogio; um laco sem delay avanca 1 ms.
while (ms < limite) {
  const r = vm.executar(5000);
  if (r.tipo === 'fim') break;
  ms += r.tipo === 'delay' ? r.ms : 1;
}
process.stdout.write(linhas.join('\n') + (linhas.length ? '\n' : ''));
