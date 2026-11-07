# Back-end: PotterLang → C++ (Arduino)

Implementado em [potter_arduino.py](../potter_arduino.py). O módulo **estende** as classes
de [potter_lang.py](../potter_lang.py) por herança, sem modificá-las:

```
fonte .potter
  └─ LexerPotter                  (núcleo)
  └─ ParserPotterArduino          (+ CAST como expressão)
  └─ SemanticAnalyzerArduino      (+ constantes nativas, regras de retorno, avisos)
  └─ TranspilerArduino            (inferência de tipos + geração de C++)
  └─ <Programa>/<Programa>.ino
```

Ponto de entrada: `compilar(fonte) -> (nome_do_programa, texto_ino, avisos)`.

## 1. Tabela de tradução

| PotterLang | C++ gerado |
|------------|------------|
| `HOGWARTS Nome { ... }` | arquivo `Nome/Nome.ino` com cabeçalho "NAO EDITE" |
| `VARINHA GALLEON x ~> 5;` | `int x = 5;` |
| `VOTO SICKLE PI2 ~> 6.28;` | `const float PI2 = 6.28f;` |
| `PARCHMENT` / `VERITAS` | `String` / `bool` |
| `ALWAYS` / `NEVER` | `true` / `false` |
| `"texto"` | `"texto"` com `\\`, `\"`, `\n`, `\r`, `\t` escapados |
| `x ~> e;` | `x = e;` |
| `a + b`, `a && b`, ... | `(a + b)`, `(a && b)`: todo binário ganha parênteses, preservando a precedência da AST |
| `a % b` com algum operando SICKLE | `fmod(a, b)` (em C++ o `%` só existe para inteiros) |
| `-32768` | `(-32768)` |
| `LUMOS("texto");` | `Serial.println(F("texto"));` (o texto fica na flash, não na RAM) |
| `LUMOS(expr);` | `Serial.println(expr);` |
| `SORTILEGIO (c) {..} SENAO {..}` | `if (c) {..} else {..}` |
| `VIRATEMPO (c) {..}` | `while (c) {..}` |
| `INCANTATIO f(a, b) {..}` | `<ret> f(<t> a, <t> b) {..}` (tipos inferidos, seção 3) |
| `EXPELLIARMUS e;` | `return e;` |
| `CAST f(x);` / `CAST f(x)` em expressão | `f(x);` / `f(x)` |
| `ALTO BAIXO ENTRADA SAIDA ENTRADA_PULLUP LED_EMBUTIDO` | `HIGH LOW INPUT OUTPUT INPUT_PULLUP LED_BUILTIN` |
| `pinMode digitalWrite digitalRead analogWrite analogRead delay` | as funções homônimas do core Arduino |

### Nomes

`TranspilerArduino.ident` garante que todo identificador gerado seja válido e não colida
com o ambiente Arduino:

- palavras reservadas do C++ e nomes do core (`int`, `loop`, `delay`, `Serial`, `init`, `A0`…)
  recebem o sufixo `_pl`: `VARINHA GALLEON loop` → `int loop_pl`;
- macros do pré-processador do UNO (`B1`, `DEC`, `PORTB`…, 1754 nomes em
  [dados/macros_arduino_uno.txt](../dados/macros_arduino_uno.txt)) também recebem `_pl`;
- letras não ASCII viram `_uXXXX`, porque o avr-gcc 7.3 do core rejeita UTF-8:
  `ação` → `a_u00e7_u00e3o`.

## 2. Estrutura do sketch: `setup()` e `loop()`

O transpilador classifica os comandos do nível do `HOGWARTS`:

| Comando no topo | Destino |
|-----------------|---------|
| `VARINHA`/`VOTO` | variável **global** C++, inicializada na declaração |
| `VARINHA`/`VOTO` cujo valor contém `CAST` | global declarada sem valor; a atribuição vai para o início de `setup()` (o C++ não deixa chamar `digitalRead` na inicialização estática). Nesse caso o `VOTO` perde o `const` |
| `INCANTATIO` | função C++ antes de `setup()` |
| o **primeiro** `VIRATEMPO (ALWAYS)` | o corpo vira `loop()` |
| qualquer outro comando (antes do laço) | `setup()`, na ordem do fonte |

- Se houver algum `LUMOS` no programa, `Serial.begin(9600);` é a primeira linha de `setup()`.
- Sem `VIRATEMPO (ALWAYS)` no topo, o `loop()` fica vazio.
- Código depois do `VIRATEMPO (ALWAYS)` principal é rejeitado, pois nunca seria executado.

Exemplo real do Duelo Arcano:

```
INCANTATIO venceMagia(a, b) {
    EXPELLIARMUS (a == F_EXPELLIARMUS && b == F_BOMBARDA)
              || (a == F_BOMBARDA && b == F_PROTEGO)
              || (a == F_PROTEGO && b == F_EXPELLIARMUS);
}
```

vira ([DueloArcano/DueloArcano.ino](../DueloArcano/DueloArcano.ino), linhas 102–105):

```cpp
// INCANTATIO venceMagia
bool venceMagia(int a, int b) {
    return ((((a == F_EXPELLIARMUS) && (b == F_BOMBARDA)) || ((a == F_BOMBARDA) && (b == F_PROTEGO))) || ((a == F_PROTEGO) && (b == F_EXPELLIARMUS)));
}
```

## 3. Inferência de tipos de parâmetros e retorno

A PotterLang não declara tipos de parâmetros nem de retorno, mas o C++ exige. O
`_infer_signatures` resolve isso por **ponto fixo**:

1. Monta o ambiente de tipos do programa principal (globais + locais de `setup`/`loop`) e de
   cada feitiço (globais + parâmetros já conhecidos + locais).
2. Para cada `CAST f(arg…)`, se o tipo do parâmetro ainda é desconhecido e o tipo do
   argumento é conhecido, o parâmetro recebe esse tipo (**a primeira chamada decide**).
3. Para cada feitiço com `EXPELLIARMUS`, o retorno recebe o tipo do primeiro
   `EXPELLIARMUS` cuja expressão já pode ser tipada.
4. Repete até nada mudar (no máximo `nº de feitiços + 5` voltas), o que resolve cadeias
   como `f` chamando `g` com um parâmetro seu.

O tipo de um identificador vem do `Symbol` anotado pelo semântico (então cada escopo tem o
seu tipo) e, para parâmetros, da assinatura inferida.

Depois da inferência, `_verificar_tipos` reconfere operadores, retornos, argumentos,
atribuições e condições (lista em [semantica.md §3.3](semantica.md)).

Resultados:

| Situação | C++ |
|----------|-----|
| feitiço sem `EXPELLIARMUS` | `void` |
| retorno inferido | `int` / `float` / `String` / `bool` |
| parâmetro de feitiço nunca chamado | `int`, com o aviso `tipo do parametro 'x' nao inferido (nunca lancado); usando int.` |
| retorno impossível de inferir | `int`, com aviso |

No Duelo Arcano, as 11 assinaturas são inferidas sem aviso (`bool venceMagia(int a, int b)`,
`void mostrarFeitico(int id)`, …). Veja-as com `python potter_arduino.py --tabela duelo_arcano.potter`.

## 4. Linha de comando

```powershell
python potter_arduino.py duelo_arcano.potter            # grava DueloArcano/DueloArcano.ino
python potter_arduino.py duelo_arcano.potter -o x.ino   # caminho explícito
python potter_arduino.py duelo_arcano.potter --stdout   # só imprime
python potter_arduino.py duelo_arcano.potter --tokens   # só léxico
python potter_arduino.py duelo_arcano.potter --ast      # até o sintático
python potter_arduino.py duelo_arcano.potter --tabela   # até o semântico + assinaturas
python compilar_e_gravar.py duelo_arcano.potter --porta COM3   # .ino + arduino-cli compile + upload
```

O código de saída é 0 em caso de sucesso e 1 em caso de erro (a mensagem vai para o stderr). Os avisos saem como `[aviso] ...`.

## 5. Limitações conhecidas

Todas foram verificadas rodando o compilador:

- **Overflow em tempo de execução não é detectado.** Literais fora de -32768..32767 são
  rejeitados, mas `32767 + 1` passa pelo compilador PotterLang e gera `int x = (32767 + 1);`,
  que estoura o `int` de 16 bits do UNO (overflow com sinal, comportamento indefinido em C++).
- **Não há conversão de tipo** nem concatenação de texto: `"a" + "b"` é erro semântico (S6), e
  `LUMOS` imprime um valor por vez.
- `LUMOS(ALWAYS)` imprime `1`, porque `Serial.println(true)` imprime o `bool` como número.
- `/` entre dois GALLEON é divisão inteira (`7 / 2` → `3`), como no C++.
- Um feitiço precisa ser declarado **antes** de ser chamado (análise de passada única).
  Recursão direta funciona; recursão mútua, não.
- `INCANTATIO` só no nível do `HOGWARTS` (não há funções aninhadas).
- Parâmetros recebem o tipo da **primeira** chamada; chamar depois com outro tipo é erro
  (não há sobrecarga).
- Primitivas Arduino suportadas: só as seis da tabela 1 (não há `millis`, `tone` etc.). O
  Duelo Arcano mede o tempo com um contador de ticks de `delay(TICK_MS)`.
