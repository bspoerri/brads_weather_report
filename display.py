"""
Plain-text presentation helpers: the report greeting and the centered
section headers. These return strings (despite the print_* names) so
the caller can assemble the full report before printing.
"""
MAX_LEN = 75


def print_greeting():
    """Return the report's title line."""
    greeting = ("BRAD'S DAILY WEATHER REPORT " + "\u2615"
                + "\n"
    )
    return greeting


def print_header(report_name):
    """Return `report_name` centered within MAX_LEN columns and framed
    with dashes (e.g. '----- Marine Forecast -----')."""
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
