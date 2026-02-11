"""Setup verification script for Agentic RAG application."""
import sys
import os
import subprocess
from pathlib import Path


def check_python_version():
    """Check Python version."""
    print("🐍 Checking Python version...")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 10:
        print(f"   ✅ Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"   ❌ Python {version.major}.{version.minor}.{version.micro} (Need 3.10+)")
        return False


def check_docker():
    """Check if Docker is installed and running."""
    print("\n🐳 Checking Docker...")
    try:
        result = subprocess.run(
            ["docker", "--version"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print(f"   ✅ {result.stdout.strip()}")
            
            # Check if Docker daemon is running
            result = subprocess.run(
                ["docker", "info"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                print("   ✅ Docker daemon is running")
                return True
            else:
                print("   ❌ Docker daemon is not running")
                return False
        else:
            print("   ❌ Docker not found")
            return False
    except FileNotFoundError:
        print("   ❌ Docker not installed")
        return False


def check_docker_compose():
    """Check if Docker Compose is installed."""
    print("\n📦 Checking Docker Compose...")
    try:
        result = subprocess.run(
            ["docker-compose", "--version"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print(f"   ✅ {result.stdout.strip()}")
            return True
        else:
            # Try docker compose (new syntax)
            result = subprocess.run(
                ["docker", "compose", "version"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                print(f"   ✅ {result.stdout.strip()}")
                return True
            else:
                print("   ❌ Docker Compose not found")
                return False
    except FileNotFoundError:
        print("   ❌ Docker Compose not installed")
        return False


def check_files():
    """Check if required files exist."""
    print("\n📁 Checking required files...")
    
    required_files = [
        "requirements.txt",
        "docker-compose.yml",
        ".env.example",
        "app/main.py",
        "streamlit_app.py"
    ]
    
    all_exist = True
    for file in required_files:
        if Path(file).exists():
            print(f"   ✅ {file}")
        else:
            print(f"   ❌ {file} (missing)")
            all_exist = False
    
    return all_exist


def check_env_file():
    """Check if .env file exists and has required variables."""
    print("\n🔧 Checking environment configuration...")
    
    env_path = Path(".env")
    if not env_path.exists():
        print("   ⚠️  .env file not found")
        print("   💡 Copy .env.example to .env and add your API keys:")
        print("      copy .env.example .env  (Windows)")
        print("      cp .env.example .env    (Linux/Mac)")
        return False
    
    print("   ✅ .env file exists")
    
    # Check for required variables
    required_vars = ["OPENAI_API_KEY", "SERPAPI_API_KEY"]
    env_content = env_path.read_text()
    
    missing_vars = []
    for var in required_vars:
        # Check if variable exists in file
        var_found = False
        var_has_value = False
        
        for line in env_content.split('\n'):
            line = line.strip()
            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue
            
            if line.startswith(var):
                var_found = True
                # Get value after =
                if '=' in line:
                    value = line.split('=', 1)[1].strip()
                    # Check if it's a real value (not empty, not placeholder)
                    if value and not value.startswith('your_') and value != 'sk-':
                        var_has_value = True
                break
        
        if not var_found or not var_has_value:
            missing_vars.append(var)
    
    if missing_vars:
        print(f"   ⚠️  Missing or placeholder API keys: {', '.join(missing_vars)}")
        print("   💡 Edit .env file and add your actual API keys")
        print("   Example:")
        print("      OPENAI_API_KEY=sk-proj-...")
        print("      SERPAPI_API_KEY=abc123...")
        return False
    
    print("   ✅ API keys configured")
    return True


def check_docker_services():
    """Check if Docker services are running."""
    print("\n🐳 Checking Docker services...")
    
    try:
        result = subprocess.run(
            ["docker-compose", "ps"],
            capture_output=True,
            text=True
        )
        
        if "rag_postgres" in result.stdout and "Up" in result.stdout:
            print("   ✅ PostgreSQL is running")
        else:
            print("   ⚠️  PostgreSQL is not running")
            print("   💡 Start with: docker-compose up -d")
        
        if "rag_redis" in result.stdout and "Up" in result.stdout:
            print("   ✅ Redis is running")
        else:
            print("   ⚠️  Redis is not running")
            print("   💡 Start with: docker-compose up -d")
        
    except Exception as e:
        print(f"   ⚠️  Could not check services: {e}")


def check_environment():
    """Check if running in a Python environment (conda or venv)."""
    print("\n🏗️  Checking Python environment...")
    
    # Check if in conda environment
    if 'CONDA_DEFAULT_ENV' in os.environ:
        env_name = os.environ['CONDA_DEFAULT_ENV']
        print(f"   ✅ Running in Conda environment: {env_name}")
        return True
    
    # Check if in virtual environment
    if sys.prefix != sys.base_prefix:
        print("   ✅ Running in virtual environment")
        return True
    
    # Not in any environment
    print("   ℹ️  Not in a dedicated environment (optional)")
    print("   💡 Recommended: Create a Conda environment:")
    print("      conda create -n rag-app python=3.11")
    print("      conda activate rag-app")
    print("   Or create a virtual environment:")
    print("      python -m venv venv")
    print("      venv\\Scripts\\activate  (Windows)")
    print("      source venv/bin/activate  (Linux/Mac)")
    return True  # Return True since it's optional


def main():
    """Run all checks."""
    print("=" * 60)
    print("🔍 Agentic RAG Application - Setup Verification")
    print("=" * 60)
    
    checks = [
        ("Python Version", check_python_version()),
        ("Docker", check_docker()),
        ("Docker Compose", check_docker_compose()),
        ("Required Files", check_files()),
        ("Environment Config", check_env_file()),
        ("Python Environment", check_environment()),
    ]
    
    # Optional checks
    check_docker_services()
    
    print("\n" + "=" * 60)
    print("📊 Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in checks if result)
    total = len(checks)
    
    for name, result in checks:
        status = "✅" if result else "❌"
        print(f"{status} {name}")
    
    print(f"\nPassed: {passed}/{total}")
    
    if passed == total:
        print("\n🎉 All checks passed! You're ready to run the application.")
        print("\n🚀 Quick start:")
        print("   start-simple.bat    # Windows (recommended)")
        print("   ./start.sh          # Linux/Mac")
        print("\nOr manually:")
        print("   docker-compose up -d")
        print("   conda activate rag-app  # If using Conda")
        print("   python -m app.main")
        print("   streamlit run streamlit_app.py")
    else:
        print("\n⚠️  Some checks failed. Please fix the issues above before running.")
    
    print("=" * 60)


if __name__ == "__main__":
    main()