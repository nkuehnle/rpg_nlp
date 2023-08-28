from typing import List
import re
from pathlib import Path

# Find path to this module
MOD_PATH = Path(__file__).parent

FORMATTERS: List[str] = ["\\pagebreak", "\\columnbreak", "\\page", "\\column"]

with open(MOD_PATH / "url_regex.txt", "r") as url_regex:
    URL_REGEX_PATTERN: str = url_regex.read().strip("\n")

PARENTHETICAL_URL_PATTERN: str = r"\(" + URL_REGEX_PATTERN + r"\)"
SPECIAL_PARENTHETICAL_URL_PATTERN: str = r"\(" + URL_REGEX_PATTERN + r' ?(".*")?\)'

URL_PATTERN: str = URL_REGEX_PATTERN

LINK_PATTERNS: List[re.Pattern] = [
    re.compile(r"(?i)\[.*\]" + SPECIAL_PARENTHETICAL_URL_PATTERN),
    re.compile(r"(?i)" + SPECIAL_PARENTHETICAL_URL_PATTERN + r"\[.*\]"),
]

NOISY_METADATA: List[str] = ["title:", "description:", "tags:", "systems:", "renderer:"]

NOISY_HTML: List[str] = [
    "head",
    "img",
    "script",
    "campaign-manager-header",
    "campaign-manager-footer",
    "style",
    "br",
]

HTML_TAG_PATTERN: str = r"<[A-Za-z][^>]*/?>"

NOISY_CSS_PATTERNS: List[str] = [
    r"table tr",
    r" td ",
    r"nth-child",
    r"a:link",
    r"last-child",
    r"th,?[ \t]*td",
    r"[0-9]*\% {",
    r"(?i)div\.[a-z]+",
    r":root",
    r"\.subclassSpells",
    r"\.presence",
    r"\.large-tablet",
    r"\.noborder",
    r"\.attribution",
    r"\.equation",
    r"\.proccingPresence",
    r"\.presenceEffect",
    r"\.phb",
    r"\.centered",
    r"\.TFtableCol",
    r"\.comment",
    r"\.decoration",
    r"\.signature",
    r"\.frontcredit",
    r"\.partcover",
    r"\.chapter",
    r"\.logo",
    r"\.decal",
    r"\.backcover",
    r"\.monster",
    r"\.pageNumber",
    r"\.coverSplotch",
    r"\.small-tablet",
    r"\.note",
    r"\.back",
    r"\.left",
    r"\.wide",
    r"\.stain",
    r"\.fullpage",
    r"\.insidecover",
    r"\.classTable",
    r"\.footer",
    r"\.block",
    r"\.footnote",
    r"\.hardcover",
    r"\.toc",
    r"\.regular",
    r"\.page",
    r"table\.table",
    r"@import",
    r"@keyframes",
    r"margin-top[ \t]*:[ \t]*",
    r"margin-bottom[ \t]*:[ \t]*",
    r"padding-bottom[ \t]*:[ \t]*",
    r"padding-top[ \t]*:[ \t]*",
    r"padding-right[ \t]*:[ \t]*",
    r"padding-left[ \t]*:[ \t]*",
    r"text-justify[ \t]*:[ \t]*",
    r"table-layout[ \t]*:[ \t]*[A-Za-z]*",
    r"position[ \t]*:[ \t]*static",
    r"position[ \t]*:[ \t]*relative",
    r"position[ \t]*:[ \t]*absolute",
    r"position[ \t]*:[ \t]*fixed.subclassSpells",
    r"position[ \t]*:[ \t]*sticky",
    r"text-align[ \t]*:[ \t]*",
    r"background-image[ \t]*:[ \t]*",
    r"background-position[ \t]*:[ \t]*",
    r"font-weight[ \t]*:[ \t]*",
    r"font-style[ \t]*:[ \t]*",
    r"font-family[ \t]*:[ \t]*",
    r"font-size[ \t]*:[ \t]*",
    r"padding[ \t]*:[ \t]*",
    r"border[ \t]*:[ \t]*",
    r"box-shadow[ \t]*:[ \t]*",
    r"border-image[ \t]*:[ \t]*",
    r"border-image-outset[ \t]*:[ \t]*",
    r"text-decoration[ \t]*:[ \t]*",
    r"border-image-slice[ \t]*:[ \t]*",
    r"border-image-width[ \t]*:[ \t]*",
    r"border-style[ \t]*:[ \t]*",
    r"main-color-dark[ \t]*:[ \t]*",
    r"main-color-light[ \t]*:[ \t]*",
    r"main-color-lighter[ \t]*:[ \t]*",
    r"main-color-lightest[ \t]*:[ \t]*",
    r"main-color-stripe1[ \t]*:[ \t]*",
    r"main-color-stripe2[ \t]*:[ \t]*",
    r"background-size[ \t]*:[ \t]*",
    r"line-height[ \t]*:[ \t]*",
    r"background-repeat[ \t]*:[ \t]*",
    r"text-shadow[ \t]*:[ \t]*",
    r"mix-blend-mode[ \t]*:[ \t]*",
    r"width[ \t]*:[ \t]*[pxem\%0-9\-]*",
    r"height[ \t]*:[ \t]*[pxem\%0-9\-]*",
    r"top[ \t]*:[ \t]*[pxem\%0-9\-]*",
    r"bottom[ \t]*:[ \t]*[pxem\%0-9\-]*",
    r"z-index[ \t]*:[ \t]*",
    r"letter-spacing[ \t]*:[ \t]*",
    r"text-index[ \t]*:[ \t]*",
    r"text-transform[ \t]*:[ \t]*",
    r"margin-right[ \t]*:[ \t]*",
    r"margin-left[ \t]*:[ \t]*",
    r"color[ \t]*:[ \t]*#",
    r"color[ \t]*:[ \t]*[A-Za-z]*\(?",
    r"font-variant[ \t]*:[ \t]",
    r"webkit-text-stroke[ \t]*:[ \t]*",
    r"shadow-x[0-9]*[ \t]*:[ \t]*",
    r"vertical-align[0-9]*[ \t]*:[ \t]*",
    r"hue-rotate\(",
    r"transform:scale",
    r"-?[0-9]*px",  # Pixels
    r"var\([\w-]\)",
    r"rgba?\(",
    r"/\*.*\*/",  # Comments sections
    r"<!--[ \w]*-->",  # Comments sections
    r"(?i)url" + PARENTHETICAL_URL_PATTERN,
    # Last line is for URLs of form url(<URL>)
]

NOISY_CSS: List[re.Pattern] = [re.compile(pat) for pat in NOISY_CSS_PATTERNS]
