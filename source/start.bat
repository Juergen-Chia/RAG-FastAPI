@echo off
REM Agentic RAG Application Startup Script for Windows

echo Starting Agentic RAG Application...

REM Check if .env exists
if not exist .env (
    echo Error: .env file not found
    echo Please copy .env.example to .env and configure it
    echo    copy .env.example .env
    pause
    exit /b 1
)

REM Check if virtual environment exists
REM if not exist venv (
REM    echo Creating virtual environment...
REM    python -m venv venv
REM    echo Virtual environment created
REM)

REM Activate virtual environment
REM echo Activating virtual environment...
REM call venv\Scripts\activate.bat

REM Install requirements if needed
REM if not exist venv\.requirements_installed (
REM    echo Installing dependencies...
REM    pip install -r requirements.txt
REM    type nul > venv\.requirements_installed
REM    echo Dependencies installed
REM )

REM Start Docker services
echo Starting Docker services (PostgreSQL ^& Redis)...
docker-compose up -d

REM Wait for services
echo Waiting for services to be ready...
timeout /t 5 /nobreak > nul

echo.
echo ==========================================
echo All services are ready!
echo ==========================================
echo.
echo Starting application servers...
echo.
echo FastAPI will be available at: http://localhost:8000
echo API Documentation at: http://localhost:8000/docs
echo Streamlit UI will be available at: http://localhost:8501
echo.
echo Press Ctrl+C to stop
echo.

REM Create logs directory
if not exist logs mkdir logs

REM Start FastAPI
start /B python -m app.main > logs\fastapi.log 2>&1

REM Wait a bit
timeout /t 3 /nobreak > nul

REM Start Streamlit
start /B streamlit run streamlit_app.py > logs\streamlit.log 2>&1

echo.
echo Application is running!
echo.
echo Logs are in logs\ directory
echo.

pause
