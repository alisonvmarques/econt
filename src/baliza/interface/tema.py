"""Tema Conforto: cores e estilos do Baliza, com os mesmos nomes do Figma."""

CORES = {
    "bg/window": "#E9EAE6",
    "bg/sidebar": "#E1E3DE",
    "bg/surface": "#F6F6F3",
    "bg/surface-alt": "#EFF0EC",
    "bg/selected": "#D8E6E5",
    "text/primary": "#24282C",
    "text/secondary": "#565D64",
    "text/placeholder": "#656B71",
    "text/on-accent": "#FFFFFF",
    "border/default": "#D3D6D0",
    "border/input": "#8A8F88",
    "accent/default": "#2E6A6E",
    "accent/hover": "#24575A",
    "accent/subtle": "#D8E6E5",
    "status/success": "#2F6B47",
    "status/success-bg": "#DCEBE0",
    "status/warning": "#8A5A0C",
    "status/warning-bg": "#F1E5CC",
    "status/danger": "#A63A3A",
    "status/danger-bg": "#F1DADA",
}

FONTES = '"Inter", "Segoe UI", "Ubuntu", "Helvetica Neue", "Arial", sans-serif'


QSS = """
* { font-family: $fontes; font-size: 15px; color: $text/primary; }
QMainWindow, #fundo { background: $bg/window; }
#cartao { background: $bg/surface; border: 1px solid $border/default; border-radius: 8px; }
QLabel { background: transparent; }
QLabel[papel="titulo"] { font-size: 22px; font-weight: 600; }
QLabel[papel="secao"] { font-size: 17px; font-weight: 600; }
QLabel[papel="apoio"] { color: $text/secondary; }
QLabel[papel="rotulo"] { font-size: 13px; font-weight: 500; color: $text/secondary; }
QLabel[papel="ajuda"] { font-size: 13px; color: $text/secondary; }
QLabel[papel="erro"] { font-size: 13px; color: $status/danger; }
QLabel[papel="marca"] { font-size: 17px; font-weight: 600; }
QLabel#chave { background: $accent/subtle; border-radius: 8px; padding: 16px 20px;
  font-size: 19px; font-weight: 600; }
QLabel[aviso] { border-radius: 6px; padding: 12px 16px; font-weight: 500; }
QLabel[aviso="erro"] { background: $status/danger-bg; color: $status/danger; }
QLabel[aviso="atencao"] { background: $status/warning-bg; color: $status/warning; }
QLabel[aviso="sucesso"] { background: $status/success-bg; color: $status/success; }
QLabel[aviso="info"] { background: $accent/subtle; color: $accent/default; }
QLineEdit { background: $bg/surface; border: 1px solid $border/input; border-radius: 6px;
  padding: 7px 11px; min-height: 20px; }
QLineEdit:focus { border: 2px solid $accent/default; padding: 6px 10px; }
QLineEdit[erro="true"] { border: 2px solid $status/danger; padding: 6px 10px; }
QLineEdit:disabled { background: $bg/surface-alt; border-color: $border/default;
  color: $text/placeholder; }
QPushButton { background: $bg/surface; border: 1px solid $border/input; border-radius: 6px;
  padding: 7px 16px; min-height: 20px; }
QPushButton:hover { background: $bg/surface-alt; }
QPushButton:focus { border: 2px solid $accent/default; padding: 6px 15px; }
QPushButton:disabled { background: $bg/surface-alt; border-color: $border/default;
  color: $text/placeholder; }
QPushButton[tipo="principal"] { background: $accent/default; color: $text/on-accent;
  border: 1px solid $accent/default; font-weight: 500; }
QPushButton[tipo="principal"]:hover { background: $accent/hover; }
QPushButton[tipo="principal"]:focus { border: 2px solid $text/primary; }
QPushButton[tipo="principal"]:disabled { background: $border/default;
  border-color: $border/default; color: $text/secondary; }
QPushButton[tipo="perigo"] { color: $status/danger; border-color: $status/danger; }
QPushButton[tipo="perigo"]:hover { background: $status/danger-bg; }
QPushButton[tipo="link"] { background: transparent; border: none; padding: 2px 0;
  color: $accent/default; font-weight: 500; }
QPushButton[tipo="link"]:focus { border: none; text-decoration: underline; }
#navegacao { background: $bg/sidebar; }
QPushButton[papel="nav"] { text-align: left; background: transparent; border: none;
  border-radius: 6px; padding: 8px 12px; color: $text/secondary; }
QPushButton[papel="nav"]:hover { background: $bg/surface-alt; color: $text/primary; }
QPushButton[papel="nav"]:checked { background: $bg/selected; color: $text/primary;
  font-weight: 500; border-left: 3px solid $accent/default; padding-left: 9px; }
QPushButton[papel="nav"]:focus { border: 2px solid $accent/default; padding: 6px 10px; }
QCheckBox { spacing: 10px; }
QCheckBox::indicator { width: 18px; height: 18px; }
"""


def folha_de_estilo() -> str:
    """Troca cada $token pela cor do tema (os maiores primeiro, para não cortar nomes)."""
    qss = QSS.replace("$fontes", FONTES)
    for nome in sorted(CORES, key=len, reverse=True):
        qss = qss.replace(f"${nome}", CORES[nome])
    return qss
