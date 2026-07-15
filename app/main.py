from fastapi import FastAPI

app = FastAPI(
    title="Personal AI Assistant API",
    description="An AI-powered personal knowledge management system",
    version="0.1.0"
)


@app.get("/")
def home():
    return {
        "message": "Personal AI Assistant API is running",
        "version": "0.1.0"
    }