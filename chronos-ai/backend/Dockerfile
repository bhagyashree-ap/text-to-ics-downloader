FROM python:3.12-slim

WORKDIR /app

# System deps for PyMuPDF are bundled in wheels; keep image lean.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Generate gRPC stubs at build time.
RUN python scripts/gen_proto.py

EXPOSE 8000 50051

# Default command runs the gRPC server; the gateway runs via compose override.
CMD ["python", "-m", "app.grpc_servers.server"]
