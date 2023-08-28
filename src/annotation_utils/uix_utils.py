from colorama import Fore, Style
from inquirer.themes import Theme, term

RAW = Fore.RED + Style.BRIGHT
ANNOUNCE = Fore.YELLOW + Style.DIM


class Cyans(Theme):
    def __init__(self):
        super().__init__()
        self.Question.mark_color = term.bright_blue
        self.Question.brackets_color = term.bright_red
        self.Question.default_color = term.bright_blue
        self.Checkbox.selection_color = term.bold_red_on_gray
        self.Checkbox.selection_icon = ">"
        self.Checkbox.selected_icon = "X"
        self.Checkbox.selected_color = term.bright_blue
        self.Checkbox.unselected_color = term.normal
        self.Checkbox.unselected_icon = "o"
        self.List.selection_color = term.bold_red_on_gray
        self.List.selection_cursor = ">"
        self.List.unselected_color = term.normal
