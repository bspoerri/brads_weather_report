MAX_LEN = 75


def print_greeting():
    greeting = ("BRAD'S DAILY WEATHER REPORT " + "\u2615"
                + "\n"
    )
    return greeting


def print_header(report_name):
    if len(report_name) > MAX_LEN:
        raise ValueError("Report name limited to 75 characters")
    space_per_side = (MAX_LEN - len(report_name)) // 2
    decor = "-" * (space_per_side // 2)
    free_space = ' ' * (space_per_side - len(decor))
    header = (
        '\n' + free_space
        + decor + report_name + decor
        + free_space + '\n'
    )
    return header
