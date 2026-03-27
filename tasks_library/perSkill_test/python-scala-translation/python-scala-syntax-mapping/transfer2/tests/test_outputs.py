from pathlib import Path

OUTPUT = Path('/outputs/syntax_mapping_playbook.md')

EXPECTED = """# Python to Scala Migration Playbook

## Declarations
| Python | Scala |
|---|---|
| `x = 5` | `val x = 5` |
| `x: int = 5` | `val x: Int = 5` |
| `x, y = 1, 2` | `val (x, y) = (1, 2)` |

## Control Flow
| Python | Scala |
|---|---|
| `for i in range(10): print(i)` | `for (i <- 0 until 10) println(i)` |
| `while condition: do_something()` | `while (condition) { doSomething() }` |
| `and / or / not` | `&& / || / !` |

## Collections And Strings
| Python | Scala |
|---|---|
| `evens = [x for x in numbers if x % 2 == 0]` | `val evens = numbers.filter(_ % 2 == 0)` |
| `f\"Hello, {name}!\"` | `s\"Hello, $name!\"` |
"""


def test_output_exists() -> None:
    assert OUTPUT.exists(), f'Missing output file: {OUTPUT}'


def test_markdown_exact_match() -> None:
    actual = OUTPUT.read_text(encoding='utf-8')
    assert actual == EXPECTED, 'Playbook markdown content does not match expected output'


if __name__ == '__main__':
    test_output_exists()
    test_markdown_exact_match()
