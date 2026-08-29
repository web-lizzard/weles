---
description: Public interface at the top of a file, private helpers at the bottom
paths: ["backend/**", "tui/**"]
globs: "{backend,tui}/**"
alwaysApply: false
---

# Code ordering

## Public before private

Within a file, the public interface comes first; private/internal helpers come last.

- **Public**: whatever a consumer imports or calls from outside the module — exported classes, exported functions, public methods on an exported class.
- **Private**: internal-only helpers — Python names prefixed with `_`, TypeScript symbols that aren't exported (or are explicitly `private`/module-local).

A private helper may be declared after its first use in the file — ordering here is for the reader, not the interpreter. Python resolves names at call time and TypeScript function declarations hoist, so a public class or function is free to call a private helper defined further down.

Rationale: a reader opening the file sees what it offers before how it's implemented.

### Example (Python)

```python
class CoreException(Exception):
    @classmethod
    def code(cls) -> str:
        return _to_snake_case(cls.__name__)


def _to_snake_case(name: str) -> str:
    ...
```
