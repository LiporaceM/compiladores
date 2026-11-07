# Código intermediário: Três Endereços (TAC)

Implementado em [potter_tac.py](../potter_tac.py). É uma **saída adicional** do compilador:
o caminho AST → C++ ([backend.md](backend.md)) não usa o TAC e não foi alterado.

```
.potter ─► Léxico ─► Sintático ─► Semântico ─┬─► TranspilerArduino ─► .ino     (caminho de produção)
                                             └─► GeradorTAC ─► TAC             (representação intermediária)
```

```powershell
python potter_tac.py duelo_arcano.potter            # imprime o TAC
python potter_tac.py duelo_arcano.potter --linhas   # anota a linha do fonte de cada instrução
```

O gerador recebe a AST **já validada** pelo `SemanticAnalyzerArduino`: um programa com
erro léxico, sintático ou semântico não gera TAC (o código de saída é 1).

## 1. Instruções

| Forma | Significado |
|-------|-------------|
| `x = y` | cópia |
| `x = y op z` | binária: `+ - * / % == != < > <= >=` |
| `x = op y` | unária: `- + !` |
| `L1:` | rótulo |
| `goto L1` | desvio incondicional |
| `if x goto L1` / `ifFalse x goto L1` | desvio condicional |
| `param x` | passa um argumento |
| `call f, n` / `x = call f, n` | chamada com `n` argumentos (com ou sem valor) |
| `return` / `return x` | retorno |
| `print x` | `LUMOS` |
| `program Nome:` … `halt` | programa principal |
| `function f(a, b):` … `end f` | corpo de um `INCANTATIO` |

Os endereços são nomes de variável, temporários `t1, t2…` ou constantes (`5`, `2.5`, `"texto"`,
`true`/`false`). As constantes nativas (`ALTO`, `SAIDA`…) aparecem pelo nome.

## 2. Esquemas de tradução

| PotterLang | TAC |
|------------|-----|
| `VARINHA GALLEON x ~> 2 + 3 * 4;` | `t1 = 3 * 4` · `t2 = 2 + t1` · `x = t2` |
| `SORTILEGIO (c) { A } SENAO { B }` | *c* · `ifFalse tc goto L1` · *A* · `goto L2` · `L1:` · *B* · `L2:` |
| `SORTILEGIO (c) { A }` | *c* · `ifFalse tc goto L1` · *A* · `L1:` |
| `VIRATEMPO (c) { A }` | `L1:` · *c* · `ifFalse tc goto L2` · *A* · `goto L1` · `L2:` |
| `a && b` | `t = a` · `ifFalse t goto L` · `t = b` · `L:` (curto-circuito) |
| `a \|\| b` | `t = a` · `if t goto L` · `t = b` · `L:` |
| `CAST f(x, CAST g(y))` | `param y` · `t1 = call g, 1` · `param x` · `param t1` · `call f, 2` |
| `EXPELLIARMUS e;` | *e* · `return te` |
| `INCANTATIO f(a) { ... }` | `function f(a):` · … · `return` · `end f` (o `return` final é implícito) |

Decisões:

- **Curto-circuito** em `&&` e `||`: um `CAST` no lado direito só é executado se necessário,
  o mesmo comportamento do C++ gerado.
- **Todos os argumentos são avaliados antes dos `param`**, para que chamadas aninhadas não
  intercalem os seus `param`.
- **Nomes únicos por escopo.** O gerador usa o símbolo que o semântico resolveu para cada
  identificador. Se dois escopos declaram `x`, o segundo vira `x_1`, e assim por diante. Um
  parâmetro com o nome de um global também é renomeado.
- Os `INCANTATIO` vêm depois do `halt`, na ordem do fonte. Os temporários e rótulos são
  numerados na ordem de geração (primeiro o programa principal, depois as funções).
- **Sem otimização.** O curto-circuito, por exemplo, gera cópias redundantes (`t23 = t24`).
  Propagação de cópias e eliminação de código morto seriam os próximos passos.

## 3. Exemplo real

`python potter_tac.py exemplos/grifinoria.potter` (trecho):

```
    horas = 0
L3:
    t2 = horas < 3
    ifFalse t2 goto L4
    t3 = horas + 1
    horas = t3
    print "Usando o Vira-Tempo para a hora número:"
    print horas
    goto L3
L4:
    param "Voldemort"
    call saudarMaligno, 1
    halt
function saudarMaligno(nome):
    print nome
    return true
end saudarMaligno
```

O Duelo Arcano inteiro gera 360 linhas de TAC com 11 funções.

## 4. Validação: interpretador de TAC

`executar(codigo)` interpreta o TAC e devolve os valores impressos por `print`. Ele segue o
C++ na divisão inteira (trunca em direção a zero) e no `%`, guarda as variáveis locais de cada
chamada no próprio quadro (o que permite recursão) e aceita primitivas Arduino simuladas. Os
testes em [test_potter_tac.py](../test_potter_tac.py) usam o interpretador para conferir que o
TAC **calcula** o que o fonte descreve, e não apenas que tem o formato esperado:

- fatorial e Fibonacci recursivos (`fat(5) = 120`, `fib(10) = 55`);
- `-7 / 2 = -3`, `-7 % 2 = -1`, `7.5 % 2.0 = 1.5`;
- curto-circuito: o `CAST` do lado direito não roda quando não precisa;
- a saída completa de `exemplos/grifinoria.potter`;
- no Duelo Arcano: todo desvio aponta para um rótulo existente, toda chamada é uma função
  definida ou uma primitiva, e o `setup` configura os pinos (`pinMode(11, ENTRADA_PULLUP)`…)
  antes de entrar no laço infinito.
