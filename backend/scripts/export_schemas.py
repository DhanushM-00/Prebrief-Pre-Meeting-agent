"""Write the JSON Schema of every wire model to docs/schemas.json."""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from pydantic import TypeAdapter  # noqa: E402

from app.schemas import (  # noqa: E402
    BriefingRequest, BriefingResult, ChatRequest, ChatResponse, ErrorBody,
    LoginRequest, RegisterRequest, TokenResponse, UserOut,
)

MODELS = [BriefingRequest, BriefingResult, ChatRequest, ChatResponse, ErrorBody,
          RegisterRequest, LoginRequest, TokenResponse, UserOut]
out = {m.__name__: TypeAdapter(m).json_schema(by_alias=True, mode="serialization") for m in MODELS}
dest = pathlib.Path(__file__).resolve().parents[2] / "docs" / "schemas.json"
dest.write_text(json.dumps(out, indent=2) + "\n")
print("wrote", dest, f"({len(out)} schemas)")
