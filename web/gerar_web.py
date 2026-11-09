"""
gerar_web.py  --  gera o jogo web do Duelo Arcano a partir do programa PotterLang.

    python web/gerar_web.py                         # usa duelo_arcano.potter
    python web/gerar_web.py outro.potter -o x.html

Pipeline:  duelo_arcano.potter -> potter_tac.gerar_tac -> JSON
           + web/tac_vm.js + web/duelo_template.html  ->  web/duelo_arcano.html

A pagina gerada nao reimplementa as regras do duelo: ela executa o TAC do programa
na VM (tac_vm.js). A tela faz o papel da placa (botoes, LEDs e Monitor Serial).
Se mudar o .potter, rode este script de novo.
"""
import argparse
import json
import os
import sys

WEB = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(WEB)
sys.path.insert(0, RAIZ)

from potter_tac import Const, gerar_tac  # noqa: E402


def _endereco(x):
    if isinstance(x, Const):
        if isinstance(x.valor, float):
            return {"k": x.valor, "float": True}
        return {"k": x.valor}
    return x


def tac_para_lista(fonte: str) -> list:
    """Compila PotterLang e devolve o TAC como lista JSON-serializavel."""
    return [[i.op, _endereco(i.a), _endereco(i.b), _endereco(i.c), _endereco(i.d), i.linha]
            for i in gerar_tac(fonte)]


def _json_para_script(obj) -> str:
    # dentro de <script> o texto "</" fecharia a tag
    return json.dumps(obj, ensure_ascii=True, separators=(",", ":")).replace("</", "<\\/")


CABECALHO = ('<!doctype html>\n<html lang="pt-BR">\n<head>\n<meta charset="utf-8">\n'
             '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n')


def gerar_html(fonte: str, nome_arquivo: str = "duelo_arcano.potter", documento: bool = True) -> str:
    """Página do jogo. documento=False devolve só o conteúdo (para publicar como artifact)."""
    corpo = _preencher_modelo(fonte, nome_arquivo)
    return CABECALHO + corpo + "\n</html>\n" if documento else corpo


def _preencher_modelo(fonte: str, nome_arquivo: str) -> str:
    with open(os.path.join(WEB, "duelo_template.html"), encoding="utf-8") as f:
        modelo = f.read()
    with open(os.path.join(WEB, "tac_vm.js"), encoding="utf-8") as f:
        vm = f.read()
    tac = tac_para_lista(fonte)
    trocas = {
        "/*@@TAC_VM@@*/": vm,
        "@@TAC_JSON@@": _json_para_script(tac),
        "@@FONTE_JSON@@": _json_para_script({"nome": nome_arquivo, "texto": fonte}),
    }
    for marca, valor in trocas.items():
        if marca not in modelo:
            raise ValueError(f"marcador {marca} ausente em duelo_template.html")
        modelo = modelo.replace(marca, valor)
    return modelo


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Gera o jogo web a partir de um .potter")
    ap.add_argument("arquivo", nargs="?", default=os.path.join(RAIZ, "duelo_arcano.potter"))
    ap.add_argument("-o", "--saida", default=os.path.join(WEB, "duelo_arcano.html"))
    ap.add_argument("--fragmento", action="store_true", help="sem <!doctype>/<html> (para publicar como artifact)")
    args = ap.parse_args(argv)
    with open(args.arquivo, encoding="utf-8") as f:
        fonte = f.read()
    html = gerar_html(fonte, os.path.basename(args.arquivo), documento=not args.fragmento)
    with open(args.saida, "w", encoding="utf-8", newline="\n") as f:
        f.write(html)
    print(f"gerado: {args.saida} ({len(tac_para_lista(fonte))} instrucoes TAC)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
