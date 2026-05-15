# File and JSON handling

Tags: #python #files #json #apis #streaming #backend

File and JSON handling appears constantly in backend interviews because services parse configs, logs, request bodies, exchange messages, and batch files. Production answers should emphasize correctness, streaming, validation, and error handling.

---

## File handling

### Concept

Use `with open(...)` so files close reliably. Choose modes and buffering intentionally.

| Mode | Meaning |
| --- | --- |
| `"r"` | text read |
| `"w"` | text write, truncate |
| `"a"` | text append |
| `"rb"` | binary read |
| `"wb"` | binary write |
| `"x"` | create only, fail if exists |

Why backend systems care:

- Long-running workers leak file descriptors if files are not closed.
- Loading huge files into memory can crash processes.
- Text encoding bugs break logs/configs in production.

### Runnable examples

```python
from pathlib import Path

path = Path("symbols.txt")
path.write_text("AAPL\nMSFT\n", encoding="utf-8")

with path.open("r", encoding="utf-8") as f:
    symbols = [line.strip() for line in f if line.strip()]

print(symbols)
```

Output:

```text
['AAPL', 'MSFT']
```

The example writes a tiny file, reads it back safely with a context manager, strips whitespace, and skips empty lines. This is the same shape as reading symbol lists, config files, and small operational inputs.

Streaming large file:

```python
def read_nonempty_lines(path: str):
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield line
```

Atomic-ish write pattern:

```python
from pathlib import Path
import os

def write_config_atomic(path: Path, content: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)  # atomic replace on same filesystem
```

Writing to a temporary file first avoids leaving a half-written target file if the process crashes mid-write. `os.replace` swaps the completed temp file into place on the same filesystem.

### Edge cases

```python
from pathlib import Path

path = Path("missing.txt")
try:
    data = path.read_text(encoding="utf-8")
except FileNotFoundError:
    data = ""
```

Binary vs text:

```python
payload = b"\x00\x01ORDER"
with open("payload.bin", "wb") as f:
    f.write(payload)
```

### Performance

- Iterate line by line for large files.
- Avoid `read()` / `readlines()` on unbounded files.
- Use binary mode for wire payloads.
- Consider buffering/chunking for large writes.

### Quick revision

- Always use `with`.
- Specify encoding for text files.
- Stream large files.
- Use atomic replace for critical config/output writes.
- Separate text vs binary handling.

---

## JSON handling

### Concept

JSON serialization converts Python objects to JSON text. Deserialization parses JSON text into Python objects.

| Python | JSON |
| --- | --- |
| `dict` | object |
| `list` / `tuple` | array |
| `str` | string |
| `int` / `float` | number |
| `True` / `False` | true / false |
| `None` | null |

Why backend systems care:

- APIs use JSON heavily.
- Bad parsing/error handling becomes 500s or silent data corruption.
- Decimal, datetime, NaN, and large numbers need explicit handling in financial systems.

### Runnable examples

```python
import json

payload = {"symbol": "AAPL", "qty": 100, "urgent": True}
text = json.dumps(payload, separators=(",", ":"))
print(text)

parsed = json.loads(text)
print(parsed["symbol"])
```

Output:

```text
{"symbol":"AAPL","qty":100,"urgent":true}
AAPL
```

`json.dumps` turns Python data into JSON text for APIs or storage. `json.loads` parses that text back into Python values, after which the application should validate required fields and types.

Parsing errors:

```python
import json

raw = '{"symbol": "AAPL", bad}'

try:
    data = json.loads(raw)
except json.JSONDecodeError as exc:
    print("bad JSON", exc.msg, exc.pos)
```

Output:

```text
bad JSON Expecting property name enclosed in double quotes 19
```

The parser tells you where the syntax broke. In an API, translate this into a clean validation error instead of returning a generic server failure.

API validation style:

```python
def parse_order(raw: str) -> dict:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("invalid JSON") from exc

    required = {"symbol", "qty"}
    missing = required - data.keys()
    if missing:
        raise ValueError(f"missing fields: {sorted(missing)}")
    if not isinstance(data["qty"], int) or data["qty"] <= 0:
        raise ValueError("qty must be positive int")
    return data
```

### Edge cases

Datetime:

```python
import json
from datetime import datetime, timezone

event = {"ts": datetime.now(timezone.utc)}

def default(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"not JSON serializable: {type(obj).__name__}")

print(json.dumps(event, default=default))
```

Financial precision:

```python
import json
from decimal import Decimal

raw = '{"price": 100.10}'
data = json.loads(raw, parse_float=Decimal)
print(data["price"], type(data["price"]))
```

Output:

```text
100.10 <class 'decimal.Decimal'>
```

Using `parse_float=Decimal` keeps decimal precision at parse time. This matters for prices, cash, and risk calculations where binary floating-point surprises are unacceptable.

NaN warning:

```python
import json
import math

print(json.dumps({"x": math.nan}))  # {"x": NaN}, not strict JSON

try:
    json.dumps({"x": math.nan}, allow_nan=False)
except ValueError as exc:
    print("strict JSON rejected NaN")
```

Output:

```text
{"x": NaN}
strict JSON rejected NaN
```

Python allows `NaN` by default even though strict JSON does not. Use `allow_nan=False` when the output must be accepted by strict parsers.

### Performance concerns

- `json.dumps`/`loads` allocate objects; avoid unnecessary parse/serialize loops.
- For very high-throughput systems, teams may use `orjson`/`ujson`, but correctness and edge cases matter.
- Stream NDJSON/log files line by line instead of loading massive arrays.

NDJSON example:

```python
import json

def read_ndjson(path: str):
    with open(path, "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            try:
                yield json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"bad JSON on line {line_no}") from exc
```

### Things to keep in mind

- JSON parsing is only syntax validation; still validate required fields, types, ranges, and business rules.
- Be explicit with datetime, `Decimal`, `NaN`, and large files because defaults are often not good enough for backend or finance systems.

### Quick revision

- Use `json.loads` and handle `JSONDecodeError`.
- Validate schema/required fields after parsing.
- Use `Decimal` for financial precision where needed.
- Be explicit with datetime serialization.
- Stream large JSON/NDJSON data.
