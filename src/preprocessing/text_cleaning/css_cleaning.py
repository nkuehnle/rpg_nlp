import re
from typing import List

WRAPPER_OPEN_PATTERN: re.Pattern = re.compile(r"^{{([)(#\w:\s-]*[,]*)*")


def check_for_css(line: str, noisy_css: List[re.Pattern]) -> bool:
    line = line.strip()
    # Check for known CSS
    css = any([bool(css.findall(line)) for css in noisy_css])
    # If no known CSS, check if this is a plausible single line CSS element
    # Typically of the form:
    # .element {variable: value}
    if line == "":
        return css
    elif not (css) and (line[0] == "."):
        css = ("{" in line) and ("}" in line)

    return css


def clean_standard_css(
    lines: List[str], noisy_css: List[re.Pattern], warn_limit: int = 7
) -> List[str]:
    """
    Cleans standard CSS. Not optimized to ignore content wrappd by CSS.
    clean_wrapper_css() should be run first.

    Parameters
    ----------
    lines : List[str]
        _description_
    noisy_css : List[re.Pattern]
        _description_
    warn_limit : int, optional
        _description_, by default 7

    Returns
    -------
    List[str]
        _description_

    Raises
    ------
    ValueError
        _description_
    """
    clean_lines = []
    suspiscious_lines = []
    net_opens = 0
    warning_counter = 0

    for line in lines:
        # Calculate current/previous bracket count
        # Used to check if we are inside a multi-line CSS block
        open_brackets = line.count("{")
        close_brackets = line.count("}")
        prev_net_opens = net_opens
        net_opens = net_opens + (open_brackets - close_brackets)

        if net_opens < 0:
            net_opens = 0

        # Check if there is any plausible CSS in this line
        css = check_for_css(line, noisy_css)

        # app = False

        if not css:
            # Keep if no known CSS & no ongoing multi-line CSS block
            if not (prev_net_opens > 0) and not (net_opens > 0):
                clean_lines.append(line)
                # app = True
            # Check for mistakes #
            # If there is an ongoing multi-line block with no known CSS
            elif prev_net_opens > 0:
                # And the line is not space or a closing bracket
                if not (line == "") or not line.isspace() or not (line == "}"):
                    # Flag it as suspiscious
                    warning_counter += 1
                    suspiscious_lines.append(line)
        else:
            warning_counter = 0
            suspiscious_lines = []

        # print(f"{'CSS' if css else 'Not CSS'}/{app} ({net_opens}): {line}")

        # Check for mistakes #####
        # If we just closed a multi-line CSS block, reset the warning counter
        if (prev_net_opens > 0) and not (net_opens > 0):
            suspiscious_lines = []
            warning_counter = 0
        # If we have have >warn_limit suspicious lines, raise an error
        if warning_counter > warn_limit:
            css_err = "\n".join(suspiscious_lines)
            css_err = f">{warn_limit} lines without known CSS found:\n{css_err}"
            raise ValueError(css_err)

    return clean_lines


def clean_wrapper_css(lines: List[str], noisy_css: List[re.Pattern]) -> List[str]:
    """_summary_

    Parameters
    ----------
    lines : List[str]
        _description_
    noisy_css : List[re.Pattern]
        _description_

    Returns
    -------
    List[str]
        _description_
    """
    clean_lines = []
    wrappers = 0

    for line in lines:
        net_brackets = line.count("{") - line.count("}")
        if WRAPPER_OPEN_PATTERN.findall(line.strip()) and net_brackets > 0:
            wrappers = wrappers + 1
            wrapped_text = False  # Not necessary, just here for diagnostics
        else:
            if line.strip() == "}}":
                wrappers = wrappers - 1
                wrapped_text = False  # Not necessary, just here for diagnostics
            else:
                contains_css = check_for_css(line, noisy_css)
                wrapped_text = (wrappers > 0) and not (contains_css)

                if wrapped_text:
                    clean_lines.append(line)
                elif not (wrappers > 0):
                    clean_lines.append(line)

    return clean_lines
