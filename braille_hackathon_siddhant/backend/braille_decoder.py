"""
BrailleVision - Braille Decoder
Maps 6-dot Braille cell patterns to English characters.
Dot numbering:
  1 4
  2 5
  3 6
"""

# Complete Grade 1 Braille mapping: frozenset of raised dot positions → character
BRAILLE_MAP = {
    frozenset([1]):           'a',
    frozenset([1, 2]):        'b',
    frozenset([1, 4]):        'c',
    frozenset([1, 4, 5]):     'd',
    frozenset([1, 5]):        'e',
    frozenset([1, 2, 4]):     'f',
    frozenset([1, 2, 4, 5]):  'g',
    frozenset([1, 2, 5]):     'h',
    frozenset([2, 4]):        'i',
    frozenset([2, 4, 5]):     'j',
    frozenset([1, 3]):        'k',
    frozenset([1, 2, 3]):     'l',
    frozenset([1, 3, 4]):     'm',
    frozenset([1, 3, 4, 5]):  'n',
    frozenset([1, 3, 5]):     'o',
    frozenset([1, 2, 3, 4]):  'p',
    frozenset([1, 2, 3, 4, 5]): 'q',
    frozenset([1, 2, 3, 5]):  'r',
    frozenset([2, 3, 4]):     's',
    frozenset([2, 3, 4, 5]):  't',
    frozenset([1, 3, 6]):     'u',
    frozenset([1, 2, 3, 6]):  'v',
    frozenset([2, 4, 5, 6]):  'w',
    frozenset([1, 3, 4, 6]):  'x',
    frozenset([1, 3, 4, 5, 6]): 'y',
    frozenset([1, 3, 5, 6]):  'z',
    frozenset():              ' ',  # empty cell = space

    # Numbers (preceded by number indicator dots 3,4,5,6)
    # Capital indicator: dot 6
    frozenset([6]):           '#CAP#',  # capital follows

    # Common punctuation
    frozenset([2, 3, 6]):     ',',
    frozenset([2, 3, 4, 6]):  ';',
    frozenset([2, 3, 4, 5, 6]): ':',
    frozenset([2, 3, 5]):     '!',
    frozenset([2, 3, 5, 6]):  '"',
    frozenset([2, 3]):        '.',
    frozenset([2]):           ',',
    frozenset([2, 5, 6]):     '?',
    frozenset([3, 6]):        '-',
}

# Number map (when preceded by number indicator)
NUMBER_MAP = {
    frozenset([1]):       '1',
    frozenset([1, 2]):    '2',
    frozenset([1, 4]):    '3',
    frozenset([1, 4, 5]): '4',
    frozenset([1, 5]):    '5',
    frozenset([1, 2, 4]): '6',
    frozenset([1, 2, 4, 5]): '7',
    frozenset([1, 2, 5]): '8',
    frozenset([2, 4]):    '9',
    frozenset([2, 4, 5]): '0',
}

NUMBER_INDICATOR = frozenset([3, 4, 5, 6])
CAPITAL_INDICATOR = frozenset([6])


def decode_cell(dots: list) -> str:
    """Decode a single Braille cell from list of raised dot positions."""
    key = frozenset(dots)
    return BRAILLE_MAP.get(key, '?')


def decode_sequence(cells: list) -> str:
    """
    Decode a sequence of Braille cells into a full string.
    Handles capital and number indicators.
    
    Args:
        cells: List of lists, each inner list contains raised dot positions (1-6)
    Returns:
        Decoded English string
    """
    result = []
    capitalize_next = False
    number_mode = False

    for cell_dots in cells:
        key = frozenset(cell_dots)

        if key == CAPITAL_INDICATOR:
            capitalize_next = True
            continue

        if key == NUMBER_INDICATOR:
            number_mode = True
            continue

        if key == frozenset():
            result.append(' ')
            number_mode = False
            capitalize_next = False
            continue

        if number_mode and key in NUMBER_MAP:
            result.append(NUMBER_MAP[key])
            continue
        else:
            number_mode = False

        char = BRAILLE_MAP.get(key, '?')

        if char == '#CAP#':
            capitalize_next = True
            continue

        if capitalize_next and char.isalpha():
            char = char.upper()
            capitalize_next = False

        result.append(char)

    return ''.join(result)


def get_all_patterns() -> dict:
    """Return all Braille patterns for reference chart."""
    patterns = {}
    for dots_frozen, char in BRAILLE_MAP.items():
        if char.isalpha() and char != '#CAP#':
            patterns[char] = sorted(list(dots_frozen))
    return patterns


if __name__ == '__main__':
    # Test
    # "hello" in Braille
    hello = [
        [1, 2, 5],        # h
        [1, 5],           # e
        [1, 2, 3],        # l
        [1, 2, 3],        # l
        [1, 3, 5],        # o
    ]
    print(decode_sequence(hello))  # Should print: hello
