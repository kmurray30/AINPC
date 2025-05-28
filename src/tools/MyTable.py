import re

def get_color_code(value: float) -> str:
    if value < 0 or value > 1:
        raise ValueError("Value must be between 0 and 1")
    ranges = [0, 0.25, 0.5, 1]
    if value < ranges[1]:
        # Red (255,0,0) to Orange (255,165,0)
        ratio = value / ranges[1]
        r = 255
        g = int(165 * ratio)
        b = 0
    elif value < ranges[2]:
        # Orange (255,165,0) to Yellow (255,255,0)
        ratio = (value - ranges[1]) / (ranges[2] - ranges[1])
        r = 255
        g = int(165 + (90 * ratio))
        b = 0
    else:
        # Yellow (255,255,0) to Green (0,255,0)
        ratio = (value - ranges[2]) / (ranges[3] - ranges[2])
        r = int(255 * (1 - ratio))
        g = 255
        b = 0
    return f"\033[38;2;{r};{g};{b}m"

def get_colored_text(text: str, value: float) -> str:
    """
    Print text with a color code based on the value.
    """
    color_code = get_color_code(value)
    return(f"{color_code}{text}\033[0m")

class TableCategory:
    def __init__(self, name, colored=False, custom_width=None):
        self.name = name
        self.colored = colored
        self.width = custom_width if custom_width is not None else len(name)

    def pad_count(self, text: str) -> int:
        """
        Calculate the padding needed for the text based on the category width.
        """    
        ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
        visible_text = ansi_escape.sub('', text)
        return self.width - len(visible_text)

class MyTable:
    categories: list[TableCategory]
    rows: list[list[str | int | float]]

    def __init__(self, categories: list[TableCategory]):
        for cat in categories:
            if not isinstance(cat, TableCategory):
                raise TypeError(f"Expected TableCategory, got {type(cat)}")
        self.categories = categories
        self.rows = []
            
    def add_row(self, row_values: list[str | int | float]):
        """
        Add a row to the table.
        The number of values must match the number of categories.
        """
        if len(row_values) != len(self.categories):
            raise ValueError(f"Expected {len(self.categories)} arguments, got {len(row_values)}")
        self.rows.append(row_values)

    def print_border(self):
        border = "+" + "+".join("-" * (cat.width + 2) for cat in self.categories) + "+"
        print(border)

    def print_header(self):
        # Top border
        self.print_border()
        # Header names
        header = "| " + " | ".join(f"{cat.name}{' ' * (cat.pad_count(cat.name))}" for cat in self.categories) + " |"
        print(header)
        # Divider
        self.print_border()

    def print_row(self, row_index: int):
        if row_index >= len(self.rows):
            raise IndexError("Row index out of range")

        print("|", end="")
        row_vals: list[str] = self.rows[row_index]
        for cat, row_val in zip(self.categories, row_vals):
            if isinstance(row_val, float):
                formatted_text = f"{row_val:.4f}"
            else:
                formatted_text = str(row_val)

            if cat.colored:
                if not isinstance(row_val, (float, int)):
                    raise TypeError("Colored categories can only accept numeric values")
                formatted_text = get_colored_text(formatted_text, row_val)

            print(f" {formatted_text}{' ' * (cat.pad_count(formatted_text))} |", end="")
        print("")
    
    def print_last_row(self):
        """
        Print the last row of the table.
        """
        if not self.rows:
            raise ValueError("No rows to print")
        self.print_row(len(self.rows) - 1)

    def print_footer(self):
        # Bottom border
        self.print_border()

    def print_table(self, sorted: bool = False):
        """
        Print the entire table with header, rows, and footer.
        """
        if not self.rows:
            raise ValueError("No rows to print")
        self.print_header()
        if sorted:
            self.rows.sort(key=lambda x: x[1])
        for row in self.rows:
            self.print_row(*row)
        self.print_footer()