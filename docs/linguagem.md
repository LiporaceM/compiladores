# A linguagem PotterLang

Referência extraída do código do compilador: `LexerPotter`, `ParserPotter` e
`ParserPotterArduino`, em [potter_lang.py](../potter_lang.py) e [potter_arduino.py](../potter_arduino.py).

## 1. Léxico

### 1.1 Regras gerais

| Elemento | Regra |
|----------|-------|
| Espaços e quebras de linha | ignorados (contam para linha/coluna) |
| Comentário | `--` até o fim da linha |
| Identificador | letra ou `_`, seguido de letras, dígitos ou `_`. Diferencia maiúsculas de minúsculas. Letras acentuadas são aceitas |
| Inteiro (`GALLEON`) | um ou mais dígitos ASCII: `0`, `42`, `32767` |
| Real (`SICKLE`) | dígitos com **um** ponto: `2.5`, `299792.458`, `1.` (`.5` não é válido) |
| Texto (`PARCHMENT`) | entre aspas duplas `"..."`. Pode ocupar várias linhas e não tem sequências de escape |
| Sinal negativo | não faz parte do número: `-5` é o operador unário `-` aplicado a `5` |

Erros léxicos: símbolo desconhecido (`@`, `$`, `²`...), `=` sozinho (a atribuição é `~>`),
`&` ou `|` sozinhos, número com dois pontos (`1.2.3`) e texto sem a aspa de fechamento.
Todos são reportados como `💥 [Erro Léxico] Linha L, Coluna C: ...`.

### 1.2 Tabela de tokens

| Categoria | Lexema | Token (`TokenType`) | Significado |
|-----------|--------|---------------------|-------------|
| Programa  | `HOGWARTS` | `HOGWARTS` | início do programa |
| Comando   | `VARINHA` | `VARINHA` | declaração de variável |
|           | `VOTO` | `VOTO` | declaração de constante (Voto Perpétuo) |
|           | `SORTILEGIO` / `SENAO` | `SORTILEGIO` / `SENAO` | if / else |
|           | `VIRATEMPO` | `VIRATEMPO` | while |
|           | `INCANTATIO` | `INCANTATIO` | declaração de função (feitiço) |
|           | `CAST` | `CAST` | chamada de função |
|           | `EXPELLIARMUS` | `EXPELLIARMUS` | return |
|           | `LUMOS` | `LUMOS` | imprimir |
| Tipo      | `GALLEON` | `TYPE_GALLEON` | inteiro |
|           | `SICKLE` | `TYPE_SICKLE` | real |
|           | `PARCHMENT` | `TYPE_PARCHMENT` | texto |
|           | `VERITAS` | `TYPE_VERITAS` | booleano |
| Literal   | `ALWAYS` / `NEVER` | `ALWAYS` / `NEVER` | verdadeiro / falso |
|           | `42` | `INT_LITERAL` | inteiro |
|           | `2.5` | `FLOAT_LITERAL` | real |
|           | `"texto"` | `STRING_LITERAL` | texto |
|           | `nome` | `IDENTIFIER` | identificador |
| Atribuição| `~>` | `WAND_ASSIGN` | aceno de varinha |
| Aritmético| `+ - * / %` | `PLUS MINUS STAR_MULT SLASH MOD` | |
| Relacional| `== != < > <= >=` | `EQ NEQ LT GT LTE GTE` | |
| Lógico    | `&& \|\| !` | `AND OR NOT` | |
| Delimitador | `( ) { } , ;` | `LPAREN RPAREN LBRACE RBRACE COMMA SEMICOLON` | |
| Fim       | | `EOF` | fim do arquivo |

## 2. Sintaxe (EBNF)

O parser é **descendente recursivo LL(1)**: cada comando é escolhido pelo primeiro
token, e cada nível de precedência é uma função com repetição `{ }`, sem recursão à
esquerda. A gramática abaixo corresponde 1:1 aos métodos do parser (indicados nos comentários).

```ebnf
programa        = "HOGWARTS" IDENT "{" { comando } "}" EOF ;          (* parse *)

comando         = declaracao                                           (* statement *)
                | atribuicao
                | lumos
                | sortilegio
                | viratempo
                | incantatio
                | chamada ";"
                | expelliarmus ;

declaracao      = ( "VARINHA" | "VOTO" ) tipo IDENT "~>" expressao ";" ;   (* var_declaration *)
tipo            = "GALLEON" | "SICKLE" | "PARCHMENT" | "VERITAS" ;
atribuicao      = IDENT "~>" expressao ";" ;                           (* assignment_statement *)
lumos           = "LUMOS" "(" expressao ")" ";" ;                      (* lumos_statement *)
sortilegio      = "SORTILEGIO" "(" expressao ")" bloco [ "SENAO" bloco ] ;  (* sortilegio_statement *)
viratempo       = "VIRATEMPO" "(" expressao ")" bloco ;                (* viratempo_statement *)
incantatio      = "INCANTATIO" IDENT "(" [ IDENT { "," IDENT } ] ")" bloco ;  (* incantatio_statement *)
chamada         = "CAST" IDENT "(" [ expressao { "," expressao } ] ")" ;      (* cast_statement *)
expelliarmus    = "EXPELLIARMUS" expressao ";" ;                       (* expelliarmus_statement *)
bloco           = "{" { comando } "}" ;

expressao       = ou ;                                                 (* expression *)
ou              = e          { "||" e } ;                              (* logical_or *)
e               = igualdade  { "&&" igualdade } ;                      (* logical_and *)
igualdade       = relacional { ( "==" | "!=" ) relacional } ;          (* equality *)
relacional      = aditiva    { ( "<" | ">" | "<=" | ">=" ) aditiva } ; (* relational *)
aditiva         = multiplic  { ( "+" | "-" ) multiplic } ;             (* additive *)
multiplic       = unaria     { ( "*" | "/" | "%" ) unaria } ;          (* multiplicative *)
unaria          = ( "!" | "-" | "+" ) unaria | primaria ;              (* unary *)
primaria        = INT_LITERAL | FLOAT_LITERAL | STRING_LITERAL         (* primary *)
                | "ALWAYS" | "NEVER" | IDENT
                | "(" expressao ")"
                | chamada ;                (* extensão do back-end: ParserPotterArduino.primary *)
```

Observações:

- Não existe `SENAO SORTILEGIO` (else-if). Para encadear, aninhe um `SORTILEGIO` dentro do bloco `SENAO`.
- Os parâmetros de `INCANTATIO` **não têm tipo declarado**. O back-end infere o tipo (ver [backend.md](backend.md)).
- No front-end puro (`ParserPotter`), `CAST` só existe como comando. A forma `chamada`
  dentro de `primaria` é a extensão 1 do back-end (seção 5).

### 2.1 Nós da AST

Cada nó guarda `line` e `col` do token que o originou.

| Construção | Nó | Campos |
|------------|----|--------|
| programa | `ProgramNode` | `name`, `body` |
| `VARINHA`/`VOTO` | `VarDeclNode` | `is_const`, `data_type`, `name`, `value_expr` |
| `x ~> e;` | `AssignNode` | `name`, `expr` |
| `LUMOS` | `LumosNode` | `expr` |
| `SORTILEGIO` | `SortilegioNode` | `condition`, `then_branch`, `else_branch` |
| `VIRATEMPO` | `ViraTempoNode` | `condition`, `body` |
| `INCANTATIO` | `FuncDeclNode` | `name`, `params`, `body` |
| `CAST` | `CallNode` | `name`, `args` |
| `EXPELLIARMUS` | `ExpelliarmusNode` | `expr` |
| operadores | `BinaryOpNode` / `UnaryOpNode` | `left`, `op`, `right` / `op`, `operand` |
| folhas | `LiteralNode` / `IdentifierNode` | `value`, `type_name` / `name` |

## 3. Precedência e associatividade

Da menor para a maior. Todos os operadores binários são associativos **à esquerda**
(`a - b - c` = `(a - b) - c`).

| Nível | Operadores | Função do parser |
|------:|------------|------------------|
| 1 | `\|\|` | `logical_or` |
| 2 | `&&` | `logical_and` |
| 3 | `==` `!=` | `equality` |
| 4 | `<` `>` `<=` `>=` | `relational` |
| 5 | `+` `-` | `additive` |
| 6 | `*` `/` `%` | `multiplicative` |
| 7 | `!` `-` `+` (unários, associativos à direita) | `unary` |
| 8 | literais, identificadores, `( )`, `CAST f(...)` | `primary` |

Exemplo do Duelo Arcano: `a == F_EXPELLIARMUS && b == F_BOMBARDA || ...` é agrupado como
`((a == F_EXPELLIARMUS) && (b == F_BOMBARDA)) || ...`.

## 4. Tipos

| Tipo PotterLang | Valores | C++ gerado (Arduino UNO) |
|-----------------|---------|--------------------------|
| `GALLEON` | inteiros de -32768 a 32767 no UNO | `int` (16 bits) |
| `SICKLE`  | reais | `float` (32 bits) |
| `PARCHMENT` | texto | `String` |
| `VERITAS` | `ALWAYS` / `NEVER` | `bool` |

Regras de tipo (detalhes em [semantica.md](semantica.md)):

- `+ - * / %` exigem operandos numéricos. Se algum for `SICKLE`, o resultado é `SICKLE`; senão é `GALLEON`.
- `< > <= >=` exigem numéricos do **mesmo** tipo, e `== !=` exigem o mesmo tipo. Ambos dão `VERITAS`.
- `&& || !` exigem `VERITAS`.
- A declaração e a atribuição exigem que o valor tenha exatamente o tipo da variável (não há conversão implícita).
- As condições de `SORTILEGIO` e `VIRATEMPO` exigem `VERITAS`.

## 5. Extensões introduzidas pelo back-end Arduino

As duas são retrocompatíveis: todo programa válido no front-end puro continua válido.

1. **`CAST` como expressão.** Uma chamada pode ser usada dentro de expressões
   (sem `;`) para aproveitar o valor de retorno:
   ```
   SORTILEGIO (CAST digitalRead(BTN_INICIAR) == BAIXO) { CAST iniciarRodada(); }
   VARINHA VERITAS r ~> CAST venceMagia(escolhaJ1, escolhaJ2);
   ```
   Só podem aparecer em expressões os feitiços que conjuram `EXPELLIARMUS` e as primitivas
   que devolvem valor (`digitalRead`, `analogRead`).

2. **Constantes nativas do Arduino**, pré-declaradas como `VOTO GALLEON`:

   | PotterLang | C++ |
   |------------|-----|
   | `ALTO` | `HIGH` |
   | `BAIXO` | `LOW` |
   | `ENTRADA` | `INPUT` |
   | `SAIDA` | `OUTPUT` |
   | `ENTRADA_PULLUP` | `INPUT_PULLUP` |
   | `LED_EMBUTIDO` | `LED_BUILTIN` |

   Não podem ser reatribuídas nem redeclaradas, em nenhum escopo.

### Primitivas do Arduino

Chamadas com `CAST`, sem precisar declarar. O semântico confere a aridade:

| Primitiva | Parâmetros | Retorno |
|-----------|-----------:|---------|
| `pinMode(pino, modo)` | 2 | – |
| `digitalWrite(pino, valor)` | 2 | – |
| `digitalRead(pino)` | 1 | `GALLEON` |
| `analogWrite(pino, valor)` | 2 | – |
| `analogRead(pino)` | 1 | `GALLEON` |
| `delay(ms)` | 1 | – |
