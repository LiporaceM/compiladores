/*
 * tac_vm.js  --  maquina virtual do codigo de tres enderecos (TAC) da PotterLang.
 *
 * Porta em JavaScript do interpretador de potter_tac.py (executar), com uma diferenca:
 * a execucao PAUSA em cada `delay(ms)`, para o host (pagina web ou simulador) controlar
 * o tempo. Formato do programa: lista de [op, a, b, c, d, linha], gerada por
 * web/gerar_web.py; constantes vem como {"k": valor}.
 *
 * Limitacao: JSON nao distingue 2 de 2.0, entao divisao entre "floats" inteiros
 * (ex.: 5.0 / 2.0) vira divisao inteira. O Duelo Arcano so usa GALLEON (inteiros).
 */
(function (raiz) {
  'use strict';

  var VALORES_ARDUINO = { ALTO: 1, BAIXO: 0, ENTRADA: 0, SAIDA: 1, ENTRADA_PULLUP: 2, LED_EMBUTIDO: 13 };

  // Em Python True == 1; em JS true !== 1. Normaliza antes de comparar/calcular.
  function num(v) { return typeof v === 'boolean' ? (v ? 1 : 0) : v; }

  function aritmetica(op, x, y) {
    x = num(x); y = num(y);
    if (op === '+') return x + y;
    if (op === '-') return x - y;
    if (op === '*') return x * y;
    if (typeof x === 'number' && typeof y === 'number' && Number.isInteger(x) && Number.isInteger(y)) {
      var q = Math.trunc(x / y);                 // como no C: trunca em direcao a zero
      return op === '/' ? q : x - y * q;
    }
    return op === '/' ? x / y : x % y;           // % do JS ja e fmod
  }

  function binaria(op, x, y) {
    if (op === '+' || op === '-' || op === '*' || op === '/' || op === '%') return aritmetica(op, x, y);
    x = num(x); y = num(y);
    switch (op) {
      case '==': return x === y;
      case '!=': return x !== y;
      case '<': return x < y;
      case '>': return x > y;
      case '<=': return x <= y;
      case '>=': return x >= y;
    }
    throw new Error('operador desconhecido: ' + op);
  }

  /**
   * new PotterVM(codigo, host)
   *   host.primitivas : { nome: function(...args) }  (digitalRead, digitalWrite, pinMode, ...)
   *   host.imprimir   : function(valor)              (LUMOS)
   *   host.linha      : function(numeroDaLinha)      (opcional: linha do .potter em execucao)
   */
  function PotterVM(codigo, host) {
    this.codigo = codigo;
    this.host = host || {};
    this.rotulos = Object.create(null);
    this.funcoes = Object.create(null);
    for (var k = 0; k < codigo.length; k++) {
      var i = codigo[k];
      if (i[0] === 'label') this.rotulos[i[1]] = k;
      if (i[0] === 'func') this.funcoes[i[1]] = { inicio: k, params: i[2] };
    }
    this.reiniciar();
  }

  PotterVM.prototype.reiniciar = function () {
    this.globais = Object.create(null);
    for (var n in VALORES_ARDUINO) this.globais[n] = VALORES_ARDUINO[n];
    this.pilha = [];
    this.quadro = null;      // null = programa principal (usa os globais)
    this.params = [];
    this.pc = 0;
    this.terminou = false;
    this.passos = 0;
  };

  PotterVM.prototype.ler = function (end) {
    if (end !== null && typeof end === 'object') return end.k;
    if (this.quadro !== null && end in this.quadro) return this.quadro[end];
    if (!(end in this.globais)) throw new Error('variavel sem valor: ' + end);
    return this.globais[end];
  };

  PotterVM.prototype.escrever = function (nome, valor) {
    if (this.quadro !== null && !(nome in this.globais)) this.quadro[nome] = valor;
    else this.globais[nome] = valor;
  };

  /**
   * Executa ate `delay(ms)`, fim do programa ou estourar o orcamento de instrucoes.
   * Devolve {tipo: 'delay', ms} | {tipo: 'fim'} | {tipo: 'orcamento'}.
   */
  PotterVM.prototype.executar = function (orcamento) {
    var codigo = this.codigo, prims = this.host.primitivas || {}, aoLinha = this.host.linha;
    for (var n = 0; n < orcamento; n++) {
      if (this.terminou) return { tipo: 'fim' };
      var i = codigo[this.pc++];
      var op = i[0], a = i[1], b = i[2], c = i[3], d = i[4];
      this.passos++;
      if (aoLinha && i[5] != null) aoLinha(i[5]);
      switch (op) {
        case 'label': case 'func': case 'program':
          break;
        case 'halt':
          this.terminou = true;
          return { tipo: 'fim' };
        case 'copy':
          this.escrever(a, this.ler(b));
          break;
        case 'bin':
          this.escrever(a, binaria(c, this.ler(b), this.ler(d)));
          break;
        case 'un': {
          var v = this.ler(c);
          this.escrever(a, b === '!' ? !v : (b === '-' ? -num(v) : v));
          break;
        }
        case 'goto':
          this.pc = this.rotulos[a];
          break;
        case 'if':
          if (this.ler(a)) this.pc = this.rotulos[b];
          break;
        case 'iffalse':
          if (!this.ler(a)) this.pc = this.rotulos[b];
          break;
        case 'param':
          this.params.push(this.ler(a));
          break;
        case 'print':
          if (this.host.imprimir) this.host.imprimir(this.ler(a));
          break;
        case 'call': {
          var args = this.params.splice(this.params.length - c, c);
          var f = this.funcoes[b];
          if (f) {
            this.pilha.push({ pc: this.pc, quadro: this.quadro, destino: a });
            var quadro = Object.create(null);
            for (var p = 0; p < f.params.length; p++) quadro[f.params[p]] = args[p];
            this.quadro = quadro;
            this.pc = f.inicio + 1;
          } else {
            var prim = prims[b];
            var r = prim ? prim.apply(null, args) : undefined;
            if (a) this.escrever(a, r === undefined ? null : r);
            if (b === 'delay') return { tipo: 'delay', ms: Number(args[0]) };
          }
          break;
        }
        case 'return': case 'endfunc': {
          var valor = (op === 'return' && a != null) ? this.ler(a) : null;
          var volta = this.pilha.pop();
          this.pc = volta.pc;
          this.quadro = volta.quadro;
          if (volta.destino) this.escrever(volta.destino, valor);
          break;
        }
        default:
          throw new Error('instrucao desconhecida: ' + op);
      }
    }
    return { tipo: 'orcamento' };
  };

  var api = { PotterVM: PotterVM, binaria: binaria };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else raiz.PotterTAC = api;
})(typeof self !== 'undefined' ? self : this);
