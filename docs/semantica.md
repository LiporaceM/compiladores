# Análise semântica e tabela de símbolos

Referência extraída de `SemanticAnalyzerPotter` ([potter_lang.py](../potter_lang.py)) e de
`SemanticAnalyzerArduino` ([potter_arduino.py](../potter_arduino.py)), que estende o primeiro
sem alterá-lo.

## 1. Funcionamento geral

- A análise é feita em **uma única passada** sobre a AST, em ordem de leitura. Cada tipo de
  nó tem um método `visit_<Nó>` e as expressões são tipadas por `infer_type`.
- O primeiro erro interrompe a análise com `SemanticError`, no formato
  `💥 [Erro Semântico] Linha L, Coluna C: mensagem`.
- Todo símbolo declarado também é registrado, na ordem de declaração, em
  `tabela_completa`, que é o que `print_symbol_table()` imprime (seção 4).

## 2. Escopos (pilha de escopos)

Cada `Scope` tem um dicionário de símbolos e um ponteiro para o escopo pai. A busca
(`resolve`) vai do escopo atual até o global, de modo que o escopo léxico mais interno vence.

| Construção | Abre um escopo chamado |
|------------|------------------------|
| programa | `HOGWARTS (Global)` |
| `INCANTATIO f(...)` | `INCANTATIO f`: os parâmetros e o corpo ficam **no mesmo** escopo |
| bloco do `SORTILEGIO` | `SORTILEGIO` |
| bloco do `SENAO` | `SENAO` |
| bloco do `VIRATEMPO` | `VIRATEMPO` |

Consequências:

- Redeclarar um nome **no mesmo escopo** é erro (`'x' já foi declarado na linha N`).
- Um bloco interno pode declarar um nome que já existe fora (*sombreamento*). O back-end
  resolve o tipo pelo símbolo de cada escopo, então `x` GALLEON num bloco e `x` SICKLE em outro
  geram C++ correto (teste `test_mesmo_nome_em_blocos_diferentes_tem_tipos_independentes`).
- Um nome precisa ser declarado **antes** do uso, inclusive feitiços: `CAST f();` antes do
  `INCANTATIO f` é rejeitado. A recursão funciona porque o feitiço é registrado antes do
  seu corpo ser analisado.

## 3. Regras

### 3.1 Núcleo (`SemanticAnalyzerPotter`)

| # | Regra | Exemplo de erro |
|---|-------|-----------------|
| S1 | Identificador precisa estar declarado em algum escopo visível | `Variável 'x' usada antes de ser declarada.` |
| S2 | Sem redeclaração no mesmo escopo | `'x' já foi declarado na linha 3 (redeclaração proibida no mesmo escopo).` |
| S3 | **VOTO é imutável**: não aceita `~>` depois da declaração | `'MAX' é um VOTO Inquebrável (constante na linha 2) e não pode ser alterado.` |
| S4 | Feitiço não aceita atribuição | `'f' é um feitiço e não aceita atribuição.` |
| S5 | **Coerência de tipos** na declaração e na atribuição: o tipo do valor deve ser exatamente o da variável (sem conversão implícita) | `'x' foi declarado como GALLEON mas recebeu tipo PARCHMENT.` |
| S6 | `+ - * / %` só com GALLEON/SICKLE. O resultado é SICKLE se algum operando for SICKLE e GALLEON caso contrário | `Operador '+' exige tipos numéricos (GALLEON/SICKLE), recebidos PARCHMENT e PARCHMENT.` |
| S7 | `< > <= >=` só com numéricos; `== != < > <= >=` exigem o **mesmo** tipo dos dois lados e dão VERITAS | `Comparação entre tipos incompatíveis (GALLEON < SICKLE).` |
| S8 | `&& \|\| !` só com VERITAS; unário `-`/`+` só com numérico | `Operador '&&' exige operandos VERITAS.` |
| S9 | **Condição de `SORTILEGIO` e `VIRATEMPO` deve ser VERITAS** | `Condição do SORTILEGIO exige tipo VERITAS (booleano), encontrado GALLEON.` |
| S10 | **`EXPELLIARMUS` só dentro de `INCANTATIO`** | `EXPELLIARMUS (retorno) só pode ser conjurado dentro de um INCANTATIO.` |
| S11 | `CAST` só em nome declarado como `INCANTATIO` e com o número certo de argumentos | `Feitiço 'f' requer 2 parâmetro(s), recebidos 1.` |
| S12 | **Aridade das primitivas Arduino** (`ARDUINO_BUILTINS`): `pinMode` 2, `digitalWrite` 2, `digitalRead` 1, `analogWrite` 2, `analogRead` 1, `delay` 1 | `Comando Arduino 'pinMode' requer 2 parâmetro(s), recebidos 1.` |

Os parâmetros de `INCANTATIO` não têm tipo declarado: entram na tabela com tipo `None`
(impresso como `(parâmetro)`). Um operando sem tipo faz a checagem do operador ser
**adiada**: o binário devolve `None`, o `!` devolve VERITAS e o `-`/`+` unário devolve `None`.
Quem fecha essa lacuna é o back-end, que infere o tipo do parâmetro e reaplica S6–S8
(seção 3.3).

### 3.2 Extensões do back-end (`SemanticAnalyzerArduino`)

| # | Regra | Exemplo de erro / aviso |
|---|-------|-------------------------|
| A1 | `ALTO`, `BAIXO`, `ENTRADA`, `SAIDA`, `ENTRADA_PULLUP` e `LED_EMBUTIDO` são pré-declarados como `VOTO GALLEON` (S3 impede reatribuir) e não podem ser redeclarados nem usados como nome de feitiço ou parâmetro, em nenhum escopo | `'ALTO' é uma constante nativa do Arduino (HIGH) e não pode ser redeclarada.` |
| A2 | `CAST` como expressão só funciona com feitiços que conjuram `EXPELLIARMUS` | `INCANTATIO 'f' não conjura EXPELLIARMUS (não devolve valor) e não pode ser usado em uma expressão.` |
| A3 | Das primitivas, só `digitalRead` e `analogRead` devolvem valor (GALLEON) | `Comando Arduino 'delay' não devolve valor e não pode ser usado em uma expressão.` |
| A4 | Um `INCANTATIO` que conjura `EXPELLIARMUS` deve retornar em **todos** os caminhos. Conta como retorno: `EXPELLIARMUS`, `SORTILEGIO` com `SENAO` em que os dois ramos retornam, ou `VIRATEMPO (ALWAYS)` | `INCANTATIO 'f' conjura EXPELLIARMUS, mas nem todo caminho termina em EXPELLIARMUS (...)` |
| A5 | Parâmetro nunca lido gera **aviso** (não erro) | `Linha 4, Coluna 5: parâmetro 'x' do INCANTATIO 'f' nunca é usado.` |
| A6 | Cada `IdentifierNode`, `AssignNode` e `VarDeclNode` é anotado com o `Symbol` resolvido (atributo `simbolo`), para que o transpilador saiba o tipo correto em cada escopo | – |

### 3.3 Checagens feitas depois da inferência (transpilador)

Algumas regras só podem ser verificadas depois que o back-end infere os tipos dos
parâmetros e retornos (ver [backend.md](backend.md)). Elas saem como
`💥 [Erro de Transpilação] Linha L, Coluna C: ...`:

- operadores (S6–S8) com operandos cujo tipo só ficou conhecido pela inferência:
  `!p` com `p` GALLEON, `p && ALWAYS`, `p + 1` com `p` PARCHMENT…
  (`operador '!' exige operando VERITAS, encontrado GALLEON.`);
- um feitiço que devolve tipos diferentes em `EXPELLIARMUS` distintos;
- um argumento cujo tipo difere do tipo inferido para o parâmetro na primeira chamada;
- valor de retorno atribuído a variável de outro tipo;
- condição de `SORTILEGIO`/`VIRATEMPO` que, depois da inferência, não é VERITAS;
- literal GALLEON fora de -32768..32767;
- `INCANTATIO` fora do nível do `HOGWARTS` e código depois do `VIRATEMPO (ALWAYS)` principal.

## 4. Tabela de símbolos real do Duelo Arcano

Gerada pelo próprio compilador (`print_symbol_table()` do `SemanticAnalyzerArduino`):

```powershell
python potter_arduino.py --tabela duelo_arcano.potter
```

Saída (copiada sem edição; a coluna Linha é a linha da declaração em
[duelo_arcano.potter](../duelo_arcano.potter)):

```
✅ Nenhum erro semântico encontrado.

Nome                  Categoria     Tipo                  Linha
------------------------------------------------------------------
LED_DANO_J1           VOTO          GALLEON               18
LED_EMPATE            VOTO          GALLEON               19
LED_DANO_J2           VOTO          GALLEON               20
BTN_J1_EXPELLIARMUS   VOTO          GALLEON               22
BTN_J1_PROTEGO        VOTO          GALLEON               23
BTN_J1_BOMBARDA       VOTO          GALLEON               24
BTN_J2_EXPELLIARMUS   VOTO          GALLEON               26
BTN_J2_PROTEGO        VOTO          GALLEON               27
BTN_J2_BOMBARDA       VOTO          GALLEON               28
BTN_INICIAR           VOTO          GALLEON               30
NENHUMA               VOTO          GALLEON               33
F_EXPELLIARMUS        VOTO          GALLEON               34
F_PROTEGO             VOTO          GALLEON               35
F_BOMBARDA            VOTO          GALLEON               36
TICK_MS               VOTO          GALLEON               39
JANELA_TICKS          VOTO          GALLEON               40
LIMITE_TICKS          VOTO          GALLEON               41
escolhaJ1             VARINHA       GALLEON               44
escolhaJ2             VARINHA       GALLEON               45
tickJ1                VARINHA       GALLEON               46
tickJ2                VARINHA       GALLEON               47
tickAtual             VARINHA       GALLEON               48
rodadaAtiva           VARINHA       VERITAS               49
apagarLeds            INCANTATIO    feitiço()             55
sinalVisual           INCANTATIO    feitiço()             61
i                     VARINHA       GALLEON               62
iniciarRodada         INCANTATIO    feitiço()             72
lerBotoesJ1           INCANTATIO    feitiço()             84
lerBotoesJ2           INCANTATIO    feitiço()             103
venceMagia            INCANTATIO    feitiço(a, b)         123
a                     VARINHA       (parâmetro)           123
b                     VARINHA       (parâmetro)           123
mostrarFeitico        INCANTATIO    feitiço(id)           129
id                    VARINHA       (parâmetro)           129
exibirSelecao         INCANTATIO    feitiço()             145
validarVantagemMagica INCANTATIO    feitiço()             154
resolverDuelo         INCANTATIO    feitiço()             169
diff                  VARINHA       GALLEON               178
verificarFimRodada    INCANTATIO    feitiço()             197
alguemEscolheu        VARINHA       VERITAS               198
ambosEscolheram       VARINHA       VERITAS               199
tempoEsgotado         VARINHA       VERITAS               200

Assinaturas inferidas pelo back-end (C++):
  void apagarLeds()
  void sinalVisual()
  void iniciarRodada()
  void lerBotoesJ1()
  void lerBotoesJ2()
  bool venceMagia(int a, int b)
  void mostrarFeitico(int id)
  void exibirSelecao()
  void validarVantagemMagica()
  void resolverDuelo()
  void verificarFimRodada()
```

Leitura da tabela:

- As 17 primeiras linhas são as constantes de pinagem, os códigos de feitiço e os tempos,
  todos `VOTO` no escopo global, de modo que nenhum pode ser alterado por engano.
- `escolhaJ1` … `rodadaAtiva` são o estado global do jogo (`VARINHA`).
- `i` (linha 62) é local de `sinalVisual`; `diff` é local de `resolverDuelo`; as três
  `VERITAS` das linhas 198–200 são locais de `verificarFimRodada`.
- `a`, `b` e `id` são parâmetros: o núcleo os registra sem tipo, e o back-end inferiu `int`
  a partir das chamadas `CAST venceMagia(escolhaJ1, escolhaJ2)` e `CAST mostrarFeitico(escolhaJ1)`.
- As constantes nativas (`ALTO`, `BAIXO`...) estão no escopo global, mas não aparecem aqui
  porque são pré-declaradas direto no escopo, fora de `tabela_completa`.
- O duelo compila **sem avisos**.

## 5. Onde ver cada erro

A pasta [exemplos/erros/](../exemplos/erros) tem um programa por tipo de erro. Todos abrem
pelo menu **Exemplos** da Potter IDE, e o teste `test_exemplos_de_erro_falham_com_posicao`
garante que cada um falha com linha e coluna.
