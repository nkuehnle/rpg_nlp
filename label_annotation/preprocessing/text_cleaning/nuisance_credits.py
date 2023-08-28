import re
from pathlib import Path
import pandas as pd
from typing import Dict
from .credit_identification_helpers import pat_in_text

# Find path to this module
MOD_PATH = Path(__file__).parent
NUISSANCE_PATTERNS: Dict[str, str] = pd.read_csv(
    MOD_PATH / "nuisance_credits.csv", index_col="append"
)["pattern"].to_dict()

INT = 0


def fix_known_nuisance_credits(text: str) -> str:
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

    for append, pattern in NUISSANCE_PATTERNS.items():
        if pat_in_text(pattern, text):
            # print(pattern)
            append = append.replace("\\" + "n", "\n")
            text = re.sub(pattern=pattern, repl="\n", string=text, flags=re.IGNORECASE)
            text = text.rstrip() + f"\n__\n{append}"
    return text
