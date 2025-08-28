from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from fernlabs_api.routes import projects
from fernlabs_api.settings import APISettings

settings = APISettings()

# CORS origins
allowed_origins = [
    "http://localhost:8080",
    "http://localhost:5173",
    "http://localhost:8000",
]

app = FastAPI(
    title="FernLabs API",
    description="AI-powered workflow generation tool for developers",
    version="0.1.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health_check")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "service": "fernlabs-api"}


@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Welcome to FernLabs API", "version": "0.1.0", "docs": "/docs"}


# Include routers
app.include_router(projects.router, prefix="/api/v1/projects", tags=["projects"])
