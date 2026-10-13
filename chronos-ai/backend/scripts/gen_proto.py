#!/usr/bin/env python
"""Generate Python gRPC stubs from the .proto files.

Run from the backend/ directory:

    python scripts/gen_proto.py

Outputs *_pb2.py and *_pb2_grpc.py into app/grpc_gen/ and rewrites imports so the
generated modules import each other as a package (grpcio-tools emits flat imports).
"""
from __future__ import annotations

import pathlib
import re
import subprocess
import sys

BACKEND = pathlib.Path(__file__).resolve().parent.parent
PROTO_DIR = BACKEND / "proto"
OUT_DIR = BACKEND / "app" / "grpc_gen"


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "__init__.py").write_text("")

    protos = sorted(str(p.name) for p in PROTO_DIR.glob("*.proto"))
    if not protos:
        print("No .proto files found.", file=sys.stderr)
        return 1

    cmd = [
        sys.executable, "-m", "grpc_tools.protoc",
        f"-I{PROTO_DIR}",
        f"--python_out={OUT_DIR}",
        f"--grpc_python_out={OUT_DIR}",
        *protos,
    ]
    print("Running:", " ".join(cmd))
    result = subprocess.run(cmd, cwd=PROTO_DIR)
    if result.returncode != 0:
        return result.returncode

    _fix_imports(OUT_DIR)
    print(f"Generated stubs into {OUT_DIR}")
    return 0


def _fix_imports(out_dir: pathlib.Path) -> None:
    """grpcio-tools emits `import common_pb2 as ...`; make them package-relative."""
    modules = {p.stem for p in out_dir.glob("*_pb2.py")}
    modules |= {p.stem for p in out_dir.glob("*_pb2_grpc.py")}
    pattern = re.compile(r"^import (\w+_pb2)(?:_grpc)? as", re.MULTILINE)

    for py in list(out_dir.glob("*_pb2.py")) + list(out_dir.glob("*_pb2_grpc.py")):
        text = py.read_text()

        def repl(m: re.Match) -> str:
            return m.group(0).replace("import ", "from . import ", 1).replace(
                f" {m.group(1)}", f" {m.group(1)}"
            )

        # Convert "import X_pb2 as Y" -> "from . import X_pb2 as Y"
        text = re.sub(r"^import (\w+_pb2(?:_grpc)?) as (\w+)$",
                      r"from . import \1 as \2", text, flags=re.MULTILINE)
        py.write_text(text)


if __name__ == "__main__":
    raise SystemExit(main())
