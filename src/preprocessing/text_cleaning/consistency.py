import re
from .mappers import JARGON


def fix_units(text: str) -> str:
    """_summary_

    Parameters
    ----------
    text : str
        _description_

    Returns
    -------
    str
        _description_
    """

    text = re.sub(
        pattern=r"(?<![A-Z])( ?-? ?)ft\.?(?![A-Z])",
        repl=" foot ",
        string=text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        pattern=r"(?<![A-Z])( ?-? ?)m\.?(?![A-Z])",
        repl=" meters ",
        string=text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        pattern=r"(?<![A-Z])( ?-? ?)lbs?\.?(?![A-Z])",
        repl=" pounds ",
        string=text,
        flags=re.IGNORECASE,
    )

    return text


def fix_dice_and_version(text: str) -> str:
    """_summary_

    Parameters
    ----------
    text : str
        _description_

    Returns
    -------
    str
        _description_
    """

    def _fix_version(match: re.Match) -> str:
        match_str: str = match.group(0)
        num = match_str.lower().strip(" .ver")
        return f"version {num}"

    version_pattern = r"(?<![A-Z])[vV](er)?\.? ?[0-9]"
    text = re.sub(
        pattern=version_pattern, repl=_fix_version, string=text, flags=re.IGNORECASE
    )

    def _fix_dice(match: re.Match) -> str:
        match_str: str = match.group(0)
        match_str = match_str.lower().strip()
        match_str = match_str.rstrip("sS")
        hand = match_str.split("d")
        hand_size = hand[1]

        if len(hand) == 2:
            quant_str = hand[0]
            if any([letter.isdigit() for letter in quant_str]):
                quant = int(quant_str)
                if abs(quant) > 1:
                    d = "dice"
                else:
                    d = "die"
            else:
                d = "die"
            return f"{quant_str} {hand_size} sided {d}"

        else:
            return f" {hand_size} sided die"

    dice_pattern = r"([0-9]*|[ ])[dD][0-9]+[sS]?"
    text = re.sub(pattern=dice_pattern, repl=_fix_dice, string=text)

    return text


def fix_punctuation(text: str) -> str:
    """_summary_

    Parameters
    ----------
    text : str
        _description_

    Returns
    -------
    str
        _description_
    """

    def _fix_punctuation(match: re.Match) -> str:
        match_str: str = match.group(0)
        return f"{match_str[0]} {match_str[1]}"

    text = re.sub(
        pattern=r"[.](?:[^ 0-9])",
        repl=_fix_punctuation,
        string=text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        pattern=r"[,!?](?:[^ ])",
        repl=_fix_punctuation,
        string=text,
        flags=re.IGNORECASE,
    )

    return text


def space_matches(match: re.Match) -> str:
    """_summary_

    Parameters
    ----------
    match : re.Match
        _description_

    Returns
    -------
    str
        _description_
    """
    match_str: str = match.group(0)
    match_size = len(match_str)

    return " ".join([match_str[i] for i in range(match_size)])


def pad_match(match: re.Match) -> str:
    """_summary_

    Parameters
    ----------
    match : re.Match
        _description_

    Returns
    -------
    str
        _description_
    """
    match_str: str = match.group(0)

    return f" {match_str} "


def pad_phrases_separated_by_symbol(text: str) -> str:
    """_summary_

    Parameters
    ----------
    text : str
        _description_

    Returns
    -------
    str
        _description_
    """

    symbols = r"\|\/\+\=\÷\×\*"

    return re.sub(
        pattern=f"[^ {symbols}]?[{symbols}][^ {symbols}]?",
        repl=space_matches,
        string=text,
    )


def add_space_between_number_and_word(text: str) -> str:
    """_summary_

    Parameters
    ----------
    text : str
        _description_

    Returns
    -------
    str
        _description_
    """

    def fix_num_word_rspacing(match: re.Match) -> str:
        match_str: str = match.group(0)
        return f"{match_str[0]} {match_str[1:]}"

    def fix_num_word_lspacing(match: re.Match) -> str:
        match_str: str = match.group(0)
        return f"{match_str[0]} {match_str[1]}"

    text = re.sub(
        pattern=r"[0-9]str",
        repl=fix_num_word_rspacing,
        string=text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        pattern=r"[0-9](?!((st)|(nd)|(rd)|(th)))[^.0-9]",
        repl=fix_num_word_rspacing,
        string=text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        pattern=r"[^.0-9][0-9]",
        repl=fix_num_word_lspacing,
        string=text,
        flags=re.IGNORECASE,
    )

    return text


def strip_excess_whitespace(text: str) -> str:
    """_summary_

    Parameters
    ----------
    text : str
        _description_

    Returns
    -------
    str
        _description_
    """
    text = text.rstrip().lstrip()
    text = re.sub(pattern=r"\n\s*\n\s*\n\s*\n", repl="\n\n\n", string=text)
    text = re.sub(pattern=r"\n\s*\n", repl="\n\n", string=text)
    text = re.sub(pattern=r"  ", repl=" ", string=text)
    return text


def reduce_symbol_runs(text: str) -> str:
    """_summary_

    Parameters
    ----------
    text : str
        _description_

    Returns
    -------
    str
        _description_
    """

    def reduce_repeats(match: re.Match) -> str:
        match_str: str = match.group(0)
        return match_str[0]

    chars = [r"\+{2,}", r"-{2,}", r"\/{2,}", r"\|{2,}", r"\.{2,}", r":{2,}"]
    chars = [f"({c})" for c in chars]
    pattern = r"|".join(chars)
    return re.sub(pattern=pattern, repl=reduce_repeats, string=text)


def fix_lvl(text: str) -> str:
    """_summary_

    Parameters
    ----------
    text : str
        _description_

    Returns
    -------
    str
        _description_
    """

    def _fix_lvl(match: re.Match) -> str:
        match_str: str = match.group(0)
        return f"level {match_str[-1]}"

    def _level_spacing(match: re.Match) -> str:
        match_str: str = match.group(0)
        return match_str[0] + " " + match_str[1:]

    text = re.sub(
        pattern=r"lvl?[^A-Z]", repl=_fix_lvl, string=text, flags=re.IGNORECASE
    )
    text = text.replace("-level", " level")
    text = text.replace("-level", " level-")
    text = re.sub(
        pattern=r"[^ ]level", repl=_level_spacing, string=text, flags=re.IGNORECASE
    )

    return text


def fix_known(text: str) -> str:
    """_summary_

    Parameters
    ----------
    text : str
        _description_

    Returns
    -------
    str
        _description_
    """

    def _known_spacing(match: re.Match) -> str:
        match_str: str = match.group(0)
        return match_str[0] + " " + match_str[1:]

    text = re.sub(
        pattern=r"[^ ]known", repl=_known_spacing, string=text, flags=re.IGNORECASE
    )

    return text


def fix_strength_abbrv_spacing(text: str) -> str:
    def _fix_strength(match: re.Match) -> str:
        match_str: str = match.group(0)

        return match_str[0] + " str"

    text = re.sub(
        pattern=r"[0-9]str", repl=_fix_strength, string=text, flags=re.IGNORECASE
    )

    return text


def fix_abbreviations(text: str) -> str:
    """_summary_

    Parameters
    ----------
    text : str
        _description_

    Returns
    -------
    str
        _description_
    """

    text = re.sub(r"(?<![^\s])w/(?!o)(?![A-Z])", "with ", text, flags=re.IGNORECASE)
    text = re.sub(r"(?<![^\s])w/o(?![A-Z])", "without", text, flags=re.IGNORECASE)
    text = re.sub(
        r"(?<![^\s])a\.?k\.?a\.?(?![A-Z])", "also known as ", text, flags=re.IGNORECASE
    )
    text = re.sub(r"(?<![^\s])i\.?e\.?(?![A-Z])", "ie ", text, flags=re.IGNORECASE)
    text = re.sub(r"(?<![^\s])e\.?g\.?(?![A-Z])", "eg ", text, flags=re.IGNORECASE)
    text = re.sub(
        r"(?<![^\s])ex((\.)|(:))(?![A-Z])", "for example ", text, flags=re.IGNORECASE
    )

    return text


def fix_components(text: str) -> str:
    def _fix_components(match: re.Match) -> str:
        match_str: str = match.group(0)
        match_str = match_str.lower()
        match_str = match_str.replace("v", "Verbal")
        match_str = match_str.replace("m", "Material")
        match_str = match_str.replace("s", "Somatic")
        return match_str

    fixed_lines = []

    for line in text.split("\n"):
        if ("components:" in line.lower()) or ("vsm" in line.lower()):
            line = re.sub(
                pattern=r"(?<![A-Z])([vsm]((, ?)|( ?/ ?))?){2,3}(?![A-Z])",
                repl=_fix_components,
                string=line,
                flags=re.IGNORECASE,
            )

        fixed_lines.append(line)

    return "\n".join(fixed_lines)


def fix_jargon(text: str) -> str:
    """_summary_

    Parameters
    ----------
    text : str
        _description_

    Returns
    -------
    str
        _description_
    """

    def _fix_jargon(match: re.Match, target: str, replacement: str) -> str:
        match_str: str = match.group(0)
        match_str = match_str.lower()

        return match_str.replace(target, replacement)

    for target, replacement in JARGON.items():
        text = re.sub(
            pattern=r"(?<![A-Z0-9])" + target + r"s?(?![A-Z0-9])",
            repl=lambda match: _fix_jargon(match, target, replacement),
            string=text,
            flags=re.IGNORECASE,
        )

    text = text.replace("classs", "classes")
    text = text.replace("piecess", "pieces")
    text = text.replace("increasess", "increases")

    return text


def fix_dmg(text: str) -> str:
    """_summary_

    Parameters
    ----------
    text : str
        _description_

    Returns
    -------
    str
        _description_
    """

    def _fix_dmg(match: re.Match) -> str:
        match_str: str = match.group(0)
        match_str = match_str.lower()
        match_str.replace("dmg", " damage")
        return match_str

    patterns = [
        r"((acid)|(bludgeoning)|(cold)|(fire)|(force)|(lightning)|(necrotic)|(piercing)|(poison)|(psychic)|(radiant)|(slashing)|(thunder)|([0-9])) ?dmg",
        r"dmg ((resistance)|(from)|(to)|(by))",
        r"((take)|(resist)|(deal)|(roll)) dmg",
    ]

    for pattern in patterns:
        text = re.sub(pattern=pattern, repl=_fix_dmg, string=text, flags=re.IGNORECASE)

    return text


def fix_excessive_repeats(text: str) -> str:
    """_summary_

    Parameters
    ----------
    text : str
        _description_

    Returns
    -------
    str
        _description_
    """
    pattern = r"([^#_])\1\1+"
    text = re.sub(
        pattern=pattern,
        repl=lambda x: x.group(0)[0:1],
        string=text,
        flags=re.IGNORECASE,
    )

    return text


def make_consistent(text: str) -> str:
    """_summary_

    Parameters
    ----------
    text : str
        _description_

    Returns
    -------
    str
        _description_
    """
    # Trim any instances of 3+ of a character in a row with only 2 other than #s
    text = fix_excessive_repeats(text)
    text = re.sub(pattern=r"\.\.+", repl=".", string=text)
    # Fix slang
    text = fix_abbreviations(text)
    # Fix common jargon terms
    text = fix_jargon(text)
    # Fix spacing issues with the word "known"
    text = fix_known(text)
    # Go with and over &
    text = text.replace("&", " and ")
    # fix components
    text = fix_components(text)

    # Remove letter lists, i.e. a) ..., b) ..., ...
    text = re.sub(
        pattern=r"(?<![^\s])[A-Z]\)", repl=" ", string=text, flags=re.IGNORECASE
    )
    text = re.sub(pattern=r"\(\s*\)", repl=" ", string=text)

    # Number-associated text
    # Fix feet/ft. and pounds/lbs
    text = fix_units(text)
    # Make the word level consistent
    if "lv" in text:
        text = fix_lvl(text)
    # Fix dmg vs damage
    if "dmg" in text:
        text = fix_dmg(text)
    # Pad phrases separated by certain characters | / + &
    text = pad_phrases_separated_by_symbol(text)
    text = re.sub(r"/ ?u/ ?", "/u/", text, re.IGNORECASE)
    text = re.sub(r"/ ?r/ ?", "/r/", text, re.IGNORECASE)
    # Add space between 'str' as in strength and any number
    text = fix_strength_abbrv_spacing(text)
    # Fix dice phrases
    text = fix_dice_and_version(text)
    # Fix instances of letters training a number (st, nd, rd, and th handled above)
    text = add_space_between_number_and_word(text)

    # Fix instances where punctuation . , ! ? has no space afterwards
    text = fix_punctuation(text)
    # Strip duplicate symbols
    text = reduce_symbol_runs(text)
    # Strip excess whitespaces
    text = strip_excess_whitespace(text)

    # Remove unusual characters
    text = re.sub(
        pattern=r"[^0-9A-Za-zŽžÀ-ÿÀ-ÖØ-öø-ÿ!@#$%&\-\|\/\+\=\÷\×\*\[\];:_'\)(\",./?><\s]",
        repl="",
        string=text,
    )

    return text
