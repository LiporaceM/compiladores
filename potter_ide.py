"""
potter_ide.py  --  Potter IDE: ambiente mínimo para escrever, analisar e gravar PotterLang.

    python potter_ide.py [arquivo.potter]

Só usa a biblioteca padrão (Tkinter). Toda a lógica do compilador vem de
potter_api.py (funções puras e testadas); este módulo cuida apenas da interface.

Atalhos: Ctrl+N/O/S  novo/abrir/salvar | F5 compilar .ino | F6 tokens | F7 AST
         F8 tabela de símbolos | F9 gravar na placa
"""
import os
import queue
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import List, Optional

import compilar_e_gravar
import potter_api
from potter_arduino import caminho_sketch, salvar_ino

RAIZ = os.path.dirname(os.path.abspath(__file__))
TITULO = "Potter IDE"

# ---------------------------------------------------------------------
# Tema
# ---------------------------------------------------------------------
FONTE = ("Consolas", 12)
FONTE_SAIDA = ("Consolas", 11)
COR = {
    "fundo": "#1f1d2b", "texto": "#e6e1cf", "cursor": "#ffcc66", "selecao": "#3a3650",
    "linha_atual": "#29263a", "margem": "#18161f", "margem_texto": "#6c6783",
    "saida_fundo": "#15131c", "erro": "#ff6b6b", "aviso": "#ffcc66", "ok": "#a6cc70",
    "info": "#8fa1b3", "erro_linha": "#4a1f28",
}
REALCE = {
    "palavra_chave": {"foreground": "#e5b567", "font": FONTE + ("bold",)},
    "tipo": {"foreground": "#5ccfe6"},
    "constante": {"foreground": "#d4bfff"},
    "primitiva": {"foreground": "#73d0ff"},
    "texto": {"foreground": "#a6cc70"},
    "numero": {"foreground": "#f29e74"},
    "comentario": {"foreground": "#6c7086", "font": FONTE + ("italic",)},
    "operador": {"foreground": "#f28779"},
}

EXEMPLO_INICIAL = """-- Bem-vindo à Potter IDE! Abra um exemplo no menu "Exemplos".
HOGWARTS MeuFeitico {
    CAST pinMode(LED_EMBUTIDO, SAIDA);

    VIRATEMPO (ALWAYS) {
        CAST digitalWrite(LED_EMBUTIDO, ALTO);
        CAST delay(500);
        CAST digitalWrite(LED_EMBUTIDO, BAIXO);
        CAST delay(500);
    }
}
"""


class PotterIDE:
    def __init__(self, root: tk.Tk, arquivo: Optional[str] = None, detectar_portas: bool = True):
        self.root = root
        self.arquivo: Optional[str] = None
        self.modificado = False
        self.fila_log: "queue.Queue[str]" = queue.Queue()
        self.ocupado = False
        self._agendado_realce = None
        self._links_erro: List[potter_api.Diagnostico] = []

        root.title(TITULO)
        root.geometry("1180x800")
        root.minsize(760, 520)
        root.configure(bg=COR["fundo"])
        self._estilo()
        self._menu()
        self._barra_ferramentas()
        self._areas()
        self._barra_status()
        self._atalhos()
        root.protocol("WM_DELETE_WINDOW", self.sair)

        if arquivo:
            self.abrir_arquivo(arquivo)
        else:
            self._definir_texto(EXEMPLO_INICIAL)
            self._marcar_modificado(False)
        self.mostrar("Pronto. Use os botões acima para analisar ou compilar o código.", "info")
        if detectar_portas:
            self.atualizar_portas()
        self.root.after(60, self._consumir_log)

    # ------------------------------------------------------------------
    # Construção da interface
    # ------------------------------------------------------------------
    def _estilo(self):
        st = ttk.Style(self.root)
        st.theme_use("clam")
        st.configure("TFrame", background=COR["fundo"])
        st.configure("Barra.TFrame", background=COR["margem"])
        st.configure("TLabel", background=COR["margem"], foreground=COR["texto"])
        st.configure("Status.TLabel", background=COR["margem"], foreground=COR["margem_texto"], padding=(8, 3))
        st.configure("Titulo.TLabel", background=COR["saida_fundo"], foreground=COR["cursor"],
                     font=("Segoe UI", 10, "bold"), padding=(8, 4))
        st.configure("TButton", background="#2d2a3e", foreground=COR["texto"], borderwidth=0,
                     focusthickness=0, padding=(10, 6), font=("Segoe UI", 10))
        st.map("TButton", background=[("active", "#3d3955"), ("disabled", "#24212f")],
               foreground=[("disabled", "#5d5872")])
        st.configure("Gravar.TButton", background="#7a2e3a", font=("Segoe UI", 10, "bold"))
        st.map("Gravar.TButton", background=[("active", "#9a3a4a"), ("disabled", "#3a2a30")])
        st.configure("TCombobox", fieldbackground="#2d2a3e", background="#2d2a3e",
                     foreground=COR["texto"], arrowcolor=COR["texto"])

    def _menu(self):
        barra = tk.Menu(self.root)
        arq = tk.Menu(barra, tearoff=False)
        arq.add_command(label="Novo", accelerator="Ctrl+N", command=self.novo)
        arq.add_command(label="Abrir...", accelerator="Ctrl+O", command=self.abrir)
        arq.add_command(label="Salvar", accelerator="Ctrl+S", command=self.salvar)
        arq.add_command(label="Salvar como...", accelerator="Ctrl+Shift+S", command=self.salvar_como)
        arq.add_separator()
        arq.add_command(label="Sair", command=self.sair)
        barra.add_cascade(label="Arquivo", menu=arq)

        ex = tk.Menu(barra, tearoff=False)
        duelo = os.path.join(RAIZ, "duelo_arcano.potter")
        if os.path.isfile(duelo):
            ex.add_command(label="⚔ Duelo Arcano (jogo do Arduino)", command=lambda: self.abrir_exemplo(duelo))
            ex.add_separator()
        pasta = os.path.join(RAIZ, "exemplos")
        for nome in self._listar_potter(pasta):
            caminho = os.path.join(pasta, nome)
            ex.add_command(label=nome, command=lambda c=caminho: self.abrir_exemplo(c))
        erros = os.path.join(pasta, "erros")
        nomes_erro = self._listar_potter(erros)
        if nomes_erro:
            sub = tk.Menu(ex, tearoff=False)
            for nome in nomes_erro:
                caminho = os.path.join(erros, nome)
                sub.add_command(label=nome, command=lambda c=caminho: self.abrir_exemplo(c))
            ex.add_cascade(label="Programas com erro", menu=sub)
        barra.add_cascade(label="Exemplos", menu=ex)

        comp = tk.Menu(barra, tearoff=False)
        comp.add_command(label="Tokens (léxico)", accelerator="F6", command=self.acao_tokens)
        comp.add_command(label="AST (sintático)", accelerator="F7", command=self.acao_ast)
        comp.add_command(label="Tabela de símbolos (semântico)", accelerator="F8", command=self.acao_tabela)
        comp.add_command(label="Compilar para .ino", accelerator="F5", command=self.acao_compilar)
        comp.add_separator()
        comp.add_command(label="Gravar na placa", accelerator="F9", command=self.acao_gravar)
        comp.add_command(label="Atualizar portas", command=self.atualizar_portas)
        barra.add_cascade(label="Compilador", menu=comp)

        ajuda = tk.Menu(barra, tearoff=False)
        ajuda.add_command(label="Sobre", command=lambda: messagebox.showinfo(
            "Sobre", "Potter IDE\nCompilador PotterLang -> Arduino (C++)\n"
                     "Disciplina de Linguagens Formais e Compiladores"))
        barra.add_cascade(label="Ajuda", menu=ajuda)
        self.root.config(menu=barra)

    @staticmethod
    def _listar_potter(pasta: str) -> List[str]:
        if not os.path.isdir(pasta):
            return []
        return sorted(n for n in os.listdir(pasta) if n.endswith(".potter"))

    def _barra_ferramentas(self):
        bar = ttk.Frame(self.root, style="Barra.TFrame", padding=(6, 6))
        bar.pack(side=tk.TOP, fill=tk.X)

        def botao(texto, cmd, estilo="TButton"):
            b = ttk.Button(bar, text=texto, command=cmd, style=estilo)
            b.pack(side=tk.LEFT, padx=2)
            return b

        botao("📂 Abrir", self.abrir)
        botao("💾 Salvar", self.salvar)
        ttk.Separator(bar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=6)
        self.botoes_analise = [
            botao("⚡ Tokens", self.acao_tokens),
            botao("🌳 AST", self.acao_ast),
            botao("📜 Tabela de Símbolos", self.acao_tabela),
            botao("🛠 Compilar .ino", self.acao_compilar),
        ]
        ttk.Separator(bar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=6)

        self.botao_gravar = ttk.Button(bar, text="🔥 Gravar na placa", command=self.acao_gravar,
                                       style="Gravar.TButton")
        self.botao_gravar.pack(side=tk.RIGHT, padx=2)
        ttk.Button(bar, text="↻", width=3, command=self.atualizar_portas).pack(side=tk.RIGHT, padx=2)
        self.porta = tk.StringVar()
        self.combo_porta = ttk.Combobox(bar, textvariable=self.porta, width=22)
        self.combo_porta.pack(side=tk.RIGHT, padx=2)
        ttk.Label(bar, text="Porta:").pack(side=tk.RIGHT, padx=(8, 2))

    def _areas(self):
        painel = tk.PanedWindow(self.root, orient=tk.VERTICAL, sashwidth=6, bg=COR["margem"], bd=0)
        painel.pack(fill=tk.BOTH, expand=True)

        # --- editor com números de linha ---
        quadro = tk.Frame(painel, bg=COR["fundo"])
        self.margem = tk.Canvas(quadro, width=52, bg=COR["margem"], highlightthickness=0)
        self.margem.pack(side=tk.LEFT, fill=tk.Y)
        rolagem = ttk.Scrollbar(quadro, orient=tk.VERTICAL)
        rolagem.pack(side=tk.RIGHT, fill=tk.Y)
        self.editor = tk.Text(
            quadro, font=FONTE, undo=True, wrap=tk.NONE, bg=COR["fundo"], fg=COR["texto"],
            insertbackground=COR["cursor"], selectbackground=COR["selecao"], bd=0,
            padx=8, pady=6, tabs=("1c",), highlightthickness=0,
        )
        self.editor.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        def rolar(*args):
            rolagem.set(*args)
            self._desenhar_margem()

        self.editor.configure(yscrollcommand=rolar)
        rolagem.configure(command=self.editor.yview)
        for tag, opcoes in REALCE.items():
            self.editor.tag_configure(tag, **opcoes)
        self.editor.tag_configure("linha_atual", background=COR["linha_atual"])
        self.editor.tag_configure("erro_linha", background=COR["erro_linha"])
        self.editor.tag_raise("sel")
        self.editor.bind("<<Modified>>", self._ao_modificar)
        self.editor.bind("<KeyRelease>", lambda e: self._atualizar_cursor())
        self.editor.bind("<ButtonRelease-1>", lambda e: self._atualizar_cursor())
        self.editor.bind("<Configure>", lambda e: self._desenhar_margem())
        self.editor.bind("<Tab>", self._tab)
        self.editor.bind("<Return>", self._enter)
        painel.add(quadro, minsize=200, stretch="always")

        # --- painel de saída ---
        saida = tk.Frame(painel, bg=COR["saida_fundo"])
        self.titulo_saida = ttk.Label(saida, text="Saída", style="Titulo.TLabel")
        self.titulo_saida.pack(side=tk.TOP, fill=tk.X)
        rol_saida = ttk.Scrollbar(saida, orient=tk.VERTICAL)
        rol_saida.pack(side=tk.RIGHT, fill=tk.Y)
        self.saida = tk.Text(saida, font=FONTE_SAIDA, bg=COR["saida_fundo"], fg=COR["texto"], bd=0,
                             padx=10, pady=6, wrap=tk.NONE, state=tk.DISABLED, height=12,
                             yscrollcommand=rol_saida.set, highlightthickness=0,
                             selectbackground=COR["selecao"])
        self.saida.pack(fill=tk.BOTH, expand=True)
        rol_saida.configure(command=self.saida.yview)
        for tag in ("erro", "aviso", "ok", "info"):
            self.saida.tag_configure(tag, foreground=COR[tag])
        self.saida.tag_configure("link", underline=True)
        self.saida.tag_bind("link", "<Enter>", lambda e: self.saida.configure(cursor="hand2"))
        self.saida.tag_bind("link", "<Leave>", lambda e: self.saida.configure(cursor=""))
        painel.add(saida, minsize=120)
        self.root.after(50, lambda: painel.sash_place(0, 0, int(self.root.winfo_height() * 0.62)))

    def _barra_status(self):
        bar = ttk.Frame(self.root, style="Barra.TFrame")
        bar.pack(side=tk.BOTTOM, fill=tk.X)
        self.status_arquivo = ttk.Label(bar, text="", style="Status.TLabel")
        self.status_arquivo.pack(side=tk.LEFT)
        self.status_cursor = ttk.Label(bar, text="Ln 1, Col 1", style="Status.TLabel")
        self.status_cursor.pack(side=tk.RIGHT)
        self.status_msg = ttk.Label(bar, text="", style="Status.TLabel")
        self.status_msg.pack(side=tk.RIGHT, padx=12)

    def _atalhos(self):
        r = self.root
        r.bind("<Control-n>", lambda e: self.novo())
        r.bind("<Control-o>", lambda e: self.abrir())
        r.bind("<Control-s>", lambda e: self.salvar())
        r.bind("<Control-S>", lambda e: self.salvar_como())
        r.bind("<F5>", lambda e: self.acao_compilar())
        r.bind("<F6>", lambda e: self.acao_tokens())
        r.bind("<F7>", lambda e: self.acao_ast())
        r.bind("<F8>", lambda e: self.acao_tabela())
        r.bind("<F9>", lambda e: self.acao_gravar())

    # ------------------------------------------------------------------
    # Editor: realce, margem, cursor
    # ------------------------------------------------------------------
    def codigo(self) -> str:
        return self.editor.get("1.0", "end-1c")

    def _definir_texto(self, texto: str):
        self.editor.delete("1.0", tk.END)
        self.editor.insert("1.0", texto)
        self.editor.edit_reset()
        self.editor.edit_modified(False)  # carregar texto não conta como alteração
        self.editor.mark_set(tk.INSERT, "1.0")
        self.editor.see("1.0")
        self._realcar()
        self._atualizar_cursor()

    def _ao_modificar(self, _evento=None):
        if not self.editor.edit_modified():
            return
        self.editor.edit_modified(False)
        self._marcar_modificado(True)
        self.editor.tag_remove("erro_linha", "1.0", tk.END)
        if self._agendado_realce is not None:
            self.root.after_cancel(self._agendado_realce)
        self._agendado_realce = self.root.after(150, self._realcar)

    def _realcar(self):
        self._agendado_realce = None
        for tag in REALCE:
            self.editor.tag_remove(tag, "1.0", tk.END)
        for tag, ini, fim in potter_api.realce(self.codigo()):
            self.editor.tag_add(tag, f"1.0+{ini}c", f"1.0+{fim}c")
        self._desenhar_margem()

    def _desenhar_margem(self):
        self.margem.delete("all")
        indice = self.editor.index("@0,0")
        while True:
            info = self.editor.dlineinfo(indice)
            if info is None:
                break
            linha = indice.split(".")[0]
            self.margem.create_text(44, info[1], anchor="ne", text=linha,
                                    fill=COR["margem_texto"], font=FONTE)
            proximo = self.editor.index(f"{indice}+1line")
            if proximo == indice:
                break
            indice = proximo

    def _atualizar_cursor(self):
        linha, col = self.editor.index(tk.INSERT).split(".")
        self.status_cursor.configure(text=f"Ln {linha}, Col {int(col) + 1}")
        self.editor.tag_remove("linha_atual", "1.0", tk.END)
        self.editor.tag_add("linha_atual", f"{linha}.0", f"{linha}.0+1line")
        self.editor.tag_lower("linha_atual")
        self._desenhar_margem()

    def _tab(self, _evento):
        self.editor.insert(tk.INSERT, "    ")
        return "break"

    def _enter(self, _evento):
        linha = self.editor.get("insert linestart", "insert")
        recuo = linha[: len(linha) - len(linha.lstrip(" "))]
        if linha.rstrip().endswith("{"):
            recuo += "    "
        self.editor.insert(tk.INSERT, "\n" + recuo)
        self.editor.see(tk.INSERT)
        self._atualizar_cursor()
        return "break"

    def ir_para(self, linha: int, coluna: Optional[int] = None):
        """Leva o cursor ao ponto do erro e destaca a linha."""
        indice = f"{linha}.{max((coluna or 1) - 1, 0)}"
        self.editor.mark_set(tk.INSERT, indice)
        self.editor.see(indice)
        self.editor.tag_remove("erro_linha", "1.0", tk.END)
        self.editor.tag_add("erro_linha", f"{linha}.0", f"{linha}.0+1line")
        self.editor.focus_set()
        self._atualizar_cursor()

    # ------------------------------------------------------------------
    # Painel de saída
    # ------------------------------------------------------------------
    def limpar_saida(self, titulo: str):
        self.titulo_saida.configure(text=titulo)
        self.saida.configure(state=tk.NORMAL)
        self.saida.delete("1.0", tk.END)
        self.saida.configure(state=tk.DISABLED)
        self._links_erro = []
        self.editor.tag_remove("erro_linha", "1.0", tk.END)

    def mostrar(self, texto: str, tag: Optional[str] = None):
        self.saida.configure(state=tk.NORMAL)
        self.saida.insert(tk.END, texto + "\n", (tag,) if tag else ())
        self.saida.configure(state=tk.DISABLED)
        self.saida.see(tk.END)

    def mostrar_diagnostico(self, d: potter_api.Diagnostico, tag: str):
        rotulo = "ERRO" if tag == "erro" else "AVISO"
        if d.linha is None:
            self.mostrar(f"[{rotulo} {d.fase}] {d.mensagem}", tag)
            return
        n = len(self._links_erro)
        self._links_erro.append(d)
        link = f"link_{n}"
        self.saida.tag_bind(link, "<Button-1>", lambda e, d=d: self.ir_para(d.linha, d.coluna))
        self.saida.configure(state=tk.NORMAL)
        self.saida.insert(tk.END, f"[{rotulo} {d.fase}] ", (tag,))
        pos = f"Linha {d.linha}" + (f", Coluna {d.coluna}" if d.coluna else "")
        self.saida.insert(tk.END, f"▶ {pos}", (tag, "link", link))
        self.saida.insert(tk.END, f"   {d.descricao}\n", (tag,))
        self.saida.configure(state=tk.DISABLED)
        self.saida.see(tk.END)

    def _exibir(self, titulo: str, r: potter_api.Resultado, sucesso: str) -> bool:
        self.limpar_saida(titulo)
        if not r.ok:
            for d in r.erros:
                self.mostrar_diagnostico(d, "erro")
            self.mostrar("\nClique na posição sublinhada para ir até o erro.", "info")
            if r.erros and r.erros[0].linha:
                self.ir_para(r.erros[0].linha, r.erros[0].coluna)
            self.status_msg.configure(text=f"✖ erro {r.erros[0].fase.lower()}" if r.erros else "✖ erro")
            return False
        for d in r.avisos:
            self.mostrar_diagnostico(d, "aviso")
        self.mostrar(r.texto)
        self.saida.see("1.0")  # resultado é lido de cima para baixo
        self.status_msg.configure(text=f"✔ {sucesso}")
        return True

    # ------------------------------------------------------------------
    # Ações do compilador
    # ------------------------------------------------------------------
    def acao_tokens(self):
        self._exibir("⚡ Análise Léxica — Tokens", potter_api.obter_tokens(self.codigo()), "léxico ok")

    def acao_ast(self):
        self._exibir("🌳 Análise Sintática — AST", potter_api.obter_ast(self.codigo()), "sintático ok")

    def acao_tabela(self):
        self._exibir("📜 Análise Semântica — Tabela de Símbolos",
                     potter_api.obter_tabela_simbolos(self.codigo()), "semântico ok")

    def acao_compilar(self) -> bool:
        r = potter_api.gerar_ino(self.codigo())
        if not self._exibir("🛠 Back-end — Sketch Arduino (.ino)", r, "compilado"):
            return False
        nome, ino = r.dados
        if self.arquivo:
            destino = caminho_sketch(self.arquivo, nome)
            salvar_ino(destino, ino)
            self.mostrar(f"\n✔ Gravado em {destino}", "ok")
        else:
            self.mostrar("\n(salve o .potter para gravar o .ino em disco)", "info")
        self.saida.see("1.0")
        self.status_msg.configure(text=f"✔ compilado: {nome}.ino")
        return True

    def acao_gravar(self):
        if self.ocupado:
            return
        porta = self.porta.get().split(" ")[0].strip()
        if not porta:
            messagebox.showwarning(TITULO, "Escolha a porta da placa (ex.: COM3). Use ↻ para procurar.")
            return
        if not self.arquivo or self.modificado:
            if not self.salvar():
                return
        if not potter_api.gerar_ino(self.codigo()).ok:
            self.acao_compilar()  # mostra os erros com links
            return
        self.limpar_saida(f"🔥 Gravando na placa ({porta})")
        self._ocupado(True)
        arquivo = self.arquivo

        def trabalho():
            try:
                cod = compilar_e_gravar.compilar_e_gravar(arquivo, porta, log=self.fila_log.put)
            except Exception as e:  # noqa: BLE001
                self.fila_log.put(f"[erro] {e}")
                cod = 1
            self.fila_log.put(("FIM", cod))

        threading.Thread(target=trabalho, daemon=True).start()

    def _consumir_log(self):
        try:
            while True:
                item = self.fila_log.get_nowait()
                if isinstance(item, tuple) and item[0] == "FIM":
                    self._ocupado(False)
                    ok = item[1] == 0
                    self.status_msg.configure(text="✔ gravado na placa" if ok else "✖ falha na gravação")
                    self.mostrar("\n✔ Concluído." if ok else "\n✖ Falhou (veja as mensagens acima).",
                                 "ok" if ok else "erro")
                elif isinstance(item, tuple) and item[0] == "PORTAS":
                    self._preencher_portas(item[1])
                else:
                    tag = "erro" if "[erro]" in item or "Error" in item else (
                        "aviso" if "[aviso]" in item else None)
                    self.mostrar(item, tag)
        except queue.Empty:
            pass
        self.root.after(60, self._consumir_log)

    def _ocupado(self, sim: bool):
        self.ocupado = sim
        estado = ["disabled"] if sim else ["!disabled"]
        for b in self.botoes_analise + [self.botao_gravar]:
            b.state(estado)
        self.root.configure(cursor="watch" if sim else "")

    def atualizar_portas(self):
        self.status_msg.configure(text="procurando placas...")
        threading.Thread(
            target=lambda: self.fila_log.put(("PORTAS", compilar_e_gravar.portas_detectadas())),
            daemon=True).start()

    def _preencher_portas(self, portas):
        valores = [f"{p}  ({d})" for p, d in portas]
        self.combo_porta.configure(values=valores)
        if valores and not self.porta.get():
            self.porta.set(valores[0])
        self.status_msg.configure(text=f"{len(portas)} porta(s) encontrada(s)" if portas
                                  else "nenhuma placa encontrada (arduino-cli instalado?)")

    # ------------------------------------------------------------------
    # Arquivos
    # ------------------------------------------------------------------
    def _marcar_modificado(self, sim: bool):
        self.modificado = sim
        nome = os.path.basename(self.arquivo) if self.arquivo else "sem título"
        self.root.title(f"{'● ' if sim else ''}{nome} — {TITULO}")
        self.status_arquivo.configure(text=self.arquivo or "arquivo não salvo")

    def _confirmar_descarte(self) -> bool:
        if not self.modificado:
            return True
        resp = messagebox.askyesnocancel(TITULO, "Salvar as alterações antes de continuar?")
        if resp is None:
            return False
        return self.salvar() if resp else True

    def novo(self):
        if not self._confirmar_descarte():
            return
        self.arquivo = None
        self._definir_texto(EXEMPLO_INICIAL)
        self._marcar_modificado(False)

    def abrir(self):
        if not self._confirmar_descarte():
            return
        caminho = filedialog.askopenfilename(
            title="Abrir programa PotterLang", initialdir=RAIZ,
            filetypes=[("PotterLang", "*.potter"), ("Todos os arquivos", "*.*")])
        if caminho:
            self.abrir_arquivo(caminho)

    def abrir_exemplo(self, caminho: str):
        if self._confirmar_descarte():
            self.abrir_arquivo(caminho)

    def abrir_arquivo(self, caminho: str):
        try:
            with open(caminho, encoding="utf-8") as f:
                texto = f.read()
        except OSError as e:
            messagebox.showerror(TITULO, f"Não foi possível abrir:\n{e}")
            return
        self.arquivo = os.path.abspath(caminho)
        self._definir_texto(texto)
        self._marcar_modificado(False)
        self.limpar_saida("Saída")
        self.mostrar(f"Aberto: {self.arquivo}", "info")

    def salvar(self) -> bool:
        if not self.arquivo:
            return self.salvar_como()
        try:
            with open(self.arquivo, "w", encoding="utf-8") as f:
                f.write(self.codigo())
        except OSError as e:
            messagebox.showerror(TITULO, f"Não foi possível salvar:\n{e}")
            return False
        self._marcar_modificado(False)
        self.status_msg.configure(text="✔ salvo")
        return True

    def salvar_como(self) -> bool:
        caminho = filedialog.asksaveasfilename(
            title="Salvar programa PotterLang", initialdir=RAIZ, defaultextension=".potter",
            filetypes=[("PotterLang", "*.potter")])
        if not caminho:
            return False
        self.arquivo = os.path.abspath(caminho)
        return self.salvar()

    def sair(self):
        if self._confirmar_descarte():
            self.root.destroy()


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if sys.platform == "win32":
        try:  # texto nítido em monitores com escala (125%, 150%...)
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except (AttributeError, OSError):
            pass
    root = tk.Tk()
    PotterIDE(root, argv[0] if argv else None)
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
