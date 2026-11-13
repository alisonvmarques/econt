"""Tema Conforto: cores e estilos do ECont, com os mesmos nomes do Figma."""

from importlib import resources
from pathlib import Path

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
QCheckBox { spacing: 10px; background: transparent; }
QCheckBox::indicator { width: 16px; height: 16px; border: 1px solid $border/input;
  border-radius: 4px; background: $bg/surface; }
QCheckBox::indicator:hover { border-color: $accent/default; }
QCheckBox::indicator:checked { background: $accent/default; border-color: $accent/default;
  image: url($marca); }
QCheckBox:focus { outline: none; }
QCheckBox::indicator:focus { border: 2px solid $text/primary; width: 14px; height: 14px; }
QCheckBox::indicator:disabled { background: $bg/surface-alt; border-color: $border/default; }
QCheckBox::indicator:checked:disabled { background: $text/placeholder;
  border-color: $text/placeholder; }
QComboBox, QDateTimeEdit, QSpinBox { background: $bg/surface; border: 1px solid $border/input;
  border-radius: 6px; padding: 7px 11px; min-height: 20px; }
QComboBox:focus, QDateTimeEdit:focus, QSpinBox:focus { border: 2px solid $accent/default;
  padding: 6px 10px; }
QComboBox[erro="true"], QDateTimeEdit[erro="true"] { border: 2px solid $status/danger;
  padding: 6px 10px; }
QComboBox QLineEdit { border: none; padding: 0; background: transparent; }
QComboBox::drop-down, QDateTimeEdit::drop-down { border: none; width: 28px; }
QComboBox::down-arrow, QDateTimeEdit::down-arrow { image: url($seta); width: 16px;
  height: 16px; }
QComboBox QAbstractItemView { background: $bg/surface; selection-background-color: $bg/selected;
  selection-color: $text/primary; border: 1px solid $border/default; }
QDialog#dialogo { background: $bg/surface; }
QTabWidget::pane { border: none; border-top: 1px solid $border/default; top: -1px; }
QTabBar::tab { background: transparent; border: none; border-bottom: 2px solid transparent;
  padding: 8px 2px; margin-right: 20px; color: $text/secondary; }
QTabBar::tab:selected { color: $text/primary; font-weight: 500;
  border-bottom: 2px solid $accent/default; }
QTabBar::tab:hover { color: $text/primary; }
QTabBar::tab:focus { text-decoration: underline; }
QTableWidget { background: $bg/surface; border: 1px solid $border/default; border-radius: 8px;
  alternate-background-color: $bg/surface; selection-background-color: $bg/selected;
  selection-color: $text/primary; outline: none; }
QTableWidget::item { padding: 10px 12px; border-bottom: 1px solid $border/default; }
QTableWidget::item:selected { background: $bg/selected; color: $text/primary; }
QTableWidget:focus { border: 2px solid $accent/default; }
QHeaderView::section { background: $bg/surface; color: $text/secondary; font-size: 13px;
  font-weight: 500; border: none; border-bottom: 1px solid $border/default;
  padding: 10px 12px; }
QLabel#confirmacao { background: $text/primary; color: $text/on-accent; border-radius: 8px;
  padding: 12px 18px; font-weight: 500; }
QLabel[etiqueta] { border-radius: 11px; padding: 2px 10px; font-size: 13px; }
QLabel[etiqueta="neutra"] { background: $bg/surface-alt; color: $text/secondary;
  border: 1px solid $border/default; }
QLabel[etiqueta="atencao"] { background: $status/warning-bg; color: $status/warning;
  border: 1px solid $status/warning-bg; }
QLabel[etiqueta="perigo"] { background: $status/danger-bg; color: $status/danger;
  border: 1px solid $status/danger; }
QLabel[etiqueta="sucesso"] { background: $status/success-bg; color: $status/success;
  border: 1px solid $status/success-bg; }
QPlainTextEdit { background: $bg/surface; border: 1px solid $border/input; border-radius: 6px;
  padding: 6px 8px; }
QPlainTextEdit:focus { border: 2px solid $accent/default; padding: 5px 7px; }
QScrollArea { background: transparent; border: none; }
QScrollArea > QWidget > QWidget { background: transparent; }
QMenu { background: $bg/surface; border: 1px solid $border/default; padding: 4px; }
QMenu::item { padding: 6px 20px 6px 12px; border-radius: 4px; }
QMenu::item:selected { background: $bg/selected; color: $text/primary; }
QMenu::item:disabled { color: $text/placeholder; }
QMenu::separator { height: 1px; background: $border/default; margin: 4px 8px; }
#coluna_quadro { background: $bg/sidebar; border: 1px solid $border/default; border-radius: 8px; }
#cartao_atividade { background: $bg/surface; border: 1px solid $border/default;
  border-radius: 6px; }
#cartao_atividade:hover { border-color: $border/input; }
#cartao_atividade:focus { border: 2px solid $accent/default; }
#cartao_atividade[prazo="atrasada"] { border-left: 4px solid $status/danger; }
#cartao_atividade[prazo="hoje"] { border-left: 4px solid $status/warning; }
#cartao_atividade[prazo="atrasada"]:focus, #cartao_atividade[prazo="hoje"]:focus {
  border-top: 2px solid $accent/default; border-right: 2px solid $accent/default;
  border-bottom: 2px solid $accent/default; }
#indicador_soltar { background: $accent/default; border: none; border-radius: 2px; }
QToolButton[papel="opcoes"] { background: transparent; border: 1px solid transparent;
  border-radius: 6px; padding: 2px 8px; color: $text/secondary; font-weight: 600; }
QToolButton[papel="opcoes"]:hover { background: $bg/surface-alt; color: $text/primary; }
QToolButton[papel="opcoes"]:focus { border: 2px solid $accent/default; }
QToolButton[papel="opcoes"]::menu-indicator { image: none; width: 0; }
"""


def folha_de_estilo() -> str:
    """Troca cada $token pela cor do tema (os maiores primeiro, para não cortar nomes)."""
    pasta = resources.files("econt.interface")
    seta = Path(str(pasta.joinpath("seta.svg"))).as_posix()
    marca = Path(str(pasta.joinpath("marca.svg"))).as_posix()
    qss = QSS.replace("$fontes", FONTES).replace("$seta", seta).replace("$marca", marca)
    for nome in sorted(CORES, key=len, reverse=True):
        qss = qss.replace(f"${nome}", CORES[nome])
    return qss
