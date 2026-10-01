<!-- Generated from docs/Reference/Command-Line.md; edit the canonical repository source. -->

# Command line

The command line exposes the same validation, generation, verification, and
replay surface as Python. It reads local JSON specifications and optional NumPy
sources; it does not evaluate code in an input document.

## Entry points and arguments

Installation provides `chances`; `python -m chances` invokes the same entry point.
No optional command-line extras are required.

| Command | Required arguments | Optional arguments | Result on standard output |
| --- | --- | --- | --- |
| `catalog` | None | None | Catalog JSON. |
| `inspect` | `spec` JSON path | `--source` NPY path | Resolved profile JSON. |
| `generate` | `spec`, `--output` new directory | `--source` NPY path | `output` destination and `receipt` JSON. |
| `verify` | `bundle` directory | None | `verified: true` and `receipt` JSON. |
| `replay` | `bundle` directory | `--output` new directory | `verified: true` and regenerated `receipt` JSON. |

`generate` publishes a bundle. `verify` reads its archived values; `replay`
regenerates under the recorded compatibility envelope. Omitting replay's output
keeps the regenerated result in memory for checking and publishes no new files.

## Execute a bounded file workflow

This standalone Python example writes a JSON recipe and invokes the CLI using
the current interpreter. All files are temporary and deleted on completion.

```python
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import subprocess
import sys

with TemporaryDirectory() as temporary:
    root = Path(temporary)
    recipe = root / "recipe.json"
    recipe.write_text(json.dumps({
        "operation": "normal",
        "parameters": {"size": 8},
        "randomness": {"seed": 42, "stream": "cli/example"},
    }), encoding="utf-8")
    bundle = root / "batch"

    def command(*arguments):
        completed = subprocess.run(
            [sys.executable, "-m", "chances", *map(str, arguments)],
            check=True, capture_output=True, text=True,
        )
        return json.loads(completed.stdout)

    assert command("inspect", recipe)["output"]["shape"] == [8]
    generated = command("generate", recipe, "--output", bundle)
    checked = command("verify", bundle)
    repeated = command("replay", bundle)
    assert checked["verified"] is True
    assert repeated["verified"] is True
    assert generated["receipt"] == checked["receipt"] == repeated["receipt"]
    assert "normal" in command("catalog")["operations"]
```

Once a recipe exists, the equivalent shell sequence is:

```bash
python -m chances inspect recipe.json
python -m chances generate recipe.json --output new-batch
python -m chances verify new-batch
python -m chances replay new-batch
python -m chances catalog
```

## Failures and adjacent surfaces

Successful commands emit JSON and exit with status 0. A `ChancesError` emits
`{"error": {"code": ..., "message": ..., "details": ...}}` on standard error
and exits with status 2. Invalid command syntax produces argparse usage text
on standard error and status 2 instead of the structured error object.

Arrays load without pickle. Existing output directories, invalid sources,
changed evidence, and incompatible replay fail under the
[same specification rules](Specifications-and-Receipts.md) as the Python API.
Command output reports evidence; arrays remain in the bundle's `data.npy`.

## Read next

Use [the Python API](README.md) when an analysis needs in-memory arrays, or the
[batch guide](../Guides/README.md) for the archival workflow and its boundaries.
