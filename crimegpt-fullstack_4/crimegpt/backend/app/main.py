from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import IntegrityError

from app.config import FRONTEND_DIST_PATH
from app.database import Base, engine, SessionLocal
from app.services.seed_service import seed_database, seed_lookup_tables

from app.routes import auth, cases, criminals, analytics, users, assistant, profile

app = FastAPI(title="CrimeGPT Backend", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# The frontend's api.ts reads `errorData.error`, not FastAPI's default `detail` key.
# These handlers translate every error response into the shape it expects.
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"error": "Invalid request data.", "details": exc.errors()})


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request, exc: IntegrityError):
    # Safety net for any database constraint violation not already caught by
    # explicit validation in a route (e.g. a foreign key or uniqueness rule).
    return JSONResponse(status_code=400, content={"error": "That request conflicts with existing data (invalid reference or duplicate value)."})


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_lookup_tables(db)
        seed_database(db)
    finally:
        db.close()


app.include_router(auth.router)
app.include_router(cases.router)
app.include_router(criminals.router)
app.include_router(analytics.router)
app.include_router(users.router)
app.include_router(assistant.router)
app.include_router(profile.router)


if FRONTEND_DIST_PATH.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST_PATH / "assets"), name="assets")

    @app.get("/{full_path:path}")
    def serve_frontend(full_path: str):
        index_file = FRONTEND_DIST_PATH / "index.html"
        return FileResponse(index_file)
