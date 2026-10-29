
"""HTTP origin server for the P2P LAN CDN."""

from pathlib import Path
from threading import Lock

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse


def create_origin_app(root_dir: str | Path) -> FastAPI:
    """Create an HTTP app serving files from a designated origin directory."""
    root = Path(root_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)

    app = FastAPI(title="P2P CDN Origin Server")

    accounting_lock = Lock()
    accounting = {
        "successful_requests": 0,
        "bytes_served": 0,
    }

    def validate_filename(file_name: str) -> Path:
        """Resolve a filename and prevent path traversal."""
        if (
            file_name in {".", ".."}
            or "/" in file_name
            or "\\" in file_name
            or Path(file_name).name != file_name
        ):
            raise HTTPException(
                status_code=400,
                detail="Invalid filename",
            )

        file_path = (root / file_name).resolve()

        if file_path.parent != root:
            raise HTTPException(
                status_code=400,
                detail="Invalid filename",
            )

        return file_path

    @app.get("/health")
    def health():
        return {
            "status": "ok",
            "service": "p2p-cdn-origin",
        }

    @app.get("/files")
    def list_files():
        """List files available from the origin."""
        files = []

        try:
            for path in sorted(root.iterdir()):
                if path.is_file() and not path.is_symlink():
                    stat = path.stat()

                    files.append({
                        "file_name": path.name,
                        "size_bytes": stat.st_size,
                        "modified_at": stat.st_mtime,
                    })

        except OSError as exc:
            raise HTTPException(
                status_code=500,
                detail="Unable to read the origin catalogue",
            ) from exc

        return {
            "status": "ok",
            "count": len(files),
            "files": files,
        }

    @app.get("/stats")
    def get_stats():
        """Return origin download-request and byte counters."""
        with accounting_lock:
            return {
                "status": "ok",
                "successful_requests": accounting[
                    "successful_requests"
                ],
                "bytes_served": accounting["bytes_served"],
            }

    @app.get("/files/{file_name}")
    def get_file(file_name: str):
        """Serve a file from the origin directory."""
        file_path = validate_filename(file_name)

        if not file_path.is_file():
            raise HTTPException(
                status_code=404,
                detail="File not found",
            )

        try:
            file_size = file_path.stat().st_size
        except OSError as exc:
            raise HTTPException(
                status_code=500,
                detail="Unable to inspect the requested file",
            ) from exc

        # This counter measures bytes in successfully requested files.
        # FileResponse sends the actual file after this handler returns.
        with accounting_lock:
            accounting["successful_requests"] += 1
            accounting["bytes_served"] += file_size

        return FileResponse(
            path=file_path,
            filename=file_path.name,
            media_type="application/octet-stream",
        )

    return app
