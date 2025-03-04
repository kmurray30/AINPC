import textwrap

# Define the 4 levels of logging
class Level:
    DEBUG = 0
    VERBOSE = 1
    INFO = 2
    WARNING = 3
    ERROR = 4

def color_map(log_level):
    # Map the log level to the color
    return {
        Level.DEBUG: "\033[90m",
        Level.VERBOSE: "\033[94m",
        Level.INFO: "\033[0m",
        Level.WARNING: "\033[93m",
        Level.ERROR: "\033[91m"
    }[log_level]

window_width = 90
indent = 0
level = Level.VERBOSE

def increment_indent(n = 1):
    global indent
    indent += n

def decrement_indent(n = 1):
    global indent
    indent -= n

def log(message, log_level=Level.INFO):
    # Print the message if the given log level is greater than or equal to the global level
    # Add indent tabs equal to the global indent level
    # Print in the following colors: gray for DEBUG, blue for VERBOSE, white for INFO, yellow for WARNING, red for ERROR
    global indent
    global window_width
    if log_level >= level:
        color = color_map(log_level)
        indent_str = ' ' * (4 * indent)
        # wrapped_message = textwrap.fill(message, width=window_width, initial_indent=indent_str, subsequent_indent=indent_str)
        # print(f"{color}{wrapped_message}\033[0m")
        # # print(f"{color}{indent_str}{message}\033[0m")
        lines = message.replace('\t', '    ').split('\n')
        wrapped_lines = [textwrap.fill(line, width=window_width, initial_indent=indent_str, subsequent_indent=indent_str) for line in lines]
        wrapped_message = '\n'.join(wrapped_lines)
        print(f"{color}{wrapped_message}\033[0m")

