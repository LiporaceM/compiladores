import sys

from potter_lang import LexerPotter, ParserPotter, SemanticAnalyzerPotter, SemanticError

# Saída redirecionada no Windows usa cp1252 e quebraria nos emojis.
if not sys.stdout.isatty():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

potter_code = """
HOGWARTS Grifinoria {
    -- Declaração de Votos e Varinhas
    VOTO SICKLE velocidadePomo ~> 299792.458;
    VARINHA GALLEON pontosGrifinoria ~> 100;
    VARINHA PARCHMENT mensagem ~> "Bem-vindo a Hogwarts!";
    VARINHA VERITAS caliceAtivo ~> NEVER;

    LUMOS(mensagem);

    -- Condicional do Chapéu Seletor
    SORTILEGIO (pontosGrifinoria > 0) {
        LUMOS("A Grifinória lidera o campeonato!");
        caliceAtivo ~> ALWAYS;
    } SENAO {
        LUMOS("Força nas próximas partidas!");
    }

    -- Laço Vira-Tempo
    VARINHA GALLEON horas ~> 0;
    VIRATEMPO (horas < 3) {
        horas ~> horas + 1;
        LUMOS("Usando o Vira-Tempo para a hora número:");
        LUMOS(horas);
    }

    -- Feitiço e Lançamento
    INCANTATIO saudarMaligno(nome) {
        LUMOS(nome);
        EXPELLIARMUS ALWAYS;
    }
    CAST saudarMaligno("Voldemort");
}
"""

print("=====================================================================")
print("🏰 CÓDIGO FONTE POTTERLANG ENVIADO AO COMPILADOR")
print("=====================================================================")
print(potter_code)

# 1. ANÁLISE LÉXICA
lexer = LexerPotter(potter_code)
tokens = lexer.tokenize()

print("\n=====================================================================")
print("⚡ RESULTADO DA ANÁLISE LÉXICA (TABELA DE TOKENS)")
print("=====================================================================")
for t in tokens:
    print(t)

# 2. ANÁLISE SINTÁTICA (AST)
parser = ParserPotter(tokens)
ast = parser.parse()

print("\n=====================================================================")
print("🌳 RESULTADO DA ANÁLISE SINTÁTICA (ÁRVORE DE SINTAXE ABSTRATA - AST)")
print("=====================================================================")
print(ast.print_tree())

# 3. ANÁLISE SEMÂNTICA (TABELA DE SÍMBOLOS)
print("\n=====================================================================")
print("🔍 RESULTADO DA ANÁLISE SEMÂNTICA (TABELA DE SÍMBOLOS)")
print("=====================================================================")
analyzer = SemanticAnalyzerPotter()
try:
    analyzer.analyze(ast)
    print("✅ Nenhum erro semântico encontrado. As leis de Hogwarts foram respeitadas!\n")
    print(analyzer.print_symbol_table())
except SemanticError as e:
    print(e)


# =====================================================================
# BATERIA DE TESTES DE ERROS
# =====================================================================

TESTES_ERRO = {
    "Reatribuir VOTO (constante)": """
HOGWARTS Teste {
    VOTO GALLEON id ~> 10;
    id ~> 20;
}
""",
    "Variável não declarada": """
HOGWARTS Teste {
    LUMOS(fantasma);
}
""",
    "Incompatibilidade de Tipo": """
HOGWARTS Teste {
    VARINHA GALLEON idade ~> "dezesseis";
}
""",
    "Redeclaração no mesmo escopo": """
HOGWARTS Teste {
    VARINHA GALLEON x ~> 1;
    VARINHA GALLEON x ~> 2;
}
""",
    "Condição não booleana no SORTILEGIO": """
HOGWARTS Teste {
    VARINHA GALLEON x ~> 5;
    SORTILEGIO (x + 1) {
        LUMOS(x);
    }
}
""",
    "EXPELLIARMUS fora de INCANTATIO": """
HOGWARTS Teste {
    EXPELLIARMUS 10;
}
"""
}

print("\n=====================================================================")
print("🧪 SUÍTE DE TESTES DE ERROS SEMÂNTICOS E SINTÁTICOS")
print("=====================================================================")
for nome_teste, codigo in TESTES_ERRO.items():
    print(f"\n--- TESTE: {nome_teste} ---")
    try:
        toks = LexerPotter(codigo).tokenize()
        tree = ParserPotter(toks).parse()
        SemanticAnalyzerPotter().analyze(tree)
        print("✅ Validação ok.")
    except Exception as e:
        print(f"Caught expected error: {e}")