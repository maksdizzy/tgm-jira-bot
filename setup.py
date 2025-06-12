#!/usr/bin/env python3
"""Setup script for TG-Jira bot development environment."""

import os
import sys
import subprocess
from pathlib import Path


def run_command(cmd, description):
    """Run a command and handle errors."""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        if e.stdout:
            print(f"   stdout: {e.stdout}")
        if e.stderr:
            print(f"   stderr: {e.stderr}")
        return False


def main():
    """Main setup function."""
    print("🚀 Setting up TG-Jira Bot development environment...")
    
    # Check Python version
    if sys.version_info < (3, 11):
        print("❌ Python 3.11+ is required")
        sys.exit(1)
    
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected")
    
    # Create virtual environment if it doesn't exist
    venv_path = Path("venv")
    if not venv_path.exists():
        if not run_command("python -m venv venv", "Creating virtual environment"):
            sys.exit(1)
    else:
        print("✅ Virtual environment already exists")
    
    # Determine activation script based on OS
    if os.name == 'nt':  # Windows
        activate_script = "venv\\Scripts\\activate"
        pip_cmd = "venv\\Scripts\\pip"
        python_cmd = "venv\\Scripts\\python"
    else:  # Unix/Linux/macOS
        activate_script = "source venv/bin/activate"
        pip_cmd = "venv/bin/pip"
        python_cmd = "venv/bin/python"
    
    # Install dependencies
    if not run_command(f"{pip_cmd} install --upgrade pip", "Upgrading pip"):
        sys.exit(1)
    
    if not run_command(f"{pip_cmd} install -r requirements-dev.txt", "Installing dependencies"):
        sys.exit(1)
    
    # Create .env file if it doesn't exist
    env_file = Path(".env")
    env_example = Path("config/.env.example")
    
    if not env_file.exists() and env_example.exists():
        print("📝 Creating .env file from template...")
        env_file.write_text(env_example.read_text())
        print("✅ .env file created")
        print("⚠️  Please edit .env file with your actual credentials!")
    elif env_file.exists():
        print("✅ .env file already exists")
    else:
        print("❌ Could not find config/.env.example template")
    
    # Create logs directory
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    print("✅ Logs directory created")
    
    # Run basic tests
    print("\n🧪 Running basic tests...")
    if run_command(f"{python_cmd} -m pytest tests/test_message_processor.py -v", "Running tests"):
        print("✅ All tests passed!")
    else:
        print("⚠️  Some tests failed, but setup can continue")
    
    print("\n🎉 Setup completed successfully!")
    print("\n📋 Next steps:")
    print("1. Edit .env file with your credentials:")
    print("   - TELEGRAM_BOT_TOKEN (from @BotFather)")
    print("   - OPENROUTER_API_KEY (from openrouter.ai)")
    print("   - JIRA_* credentials (OAuth 2.0 setup)")
    print("   - SECRET_KEY (generate a secure random string)")
    print("\n2. Activate virtual environment:")
    if os.name == 'nt':
        print("   venv\\Scripts\\activate")
    else:
        print("   source venv/bin/activate")
    print("\n3. Start development server:")
    print("   python run_dev.py")
    print("\n4. Visit http://localhost:8000/auth/jira to authenticate with Jira")
    print("\n5. Test the bot by sending messages with #ticket in Telegram")
    
    print("\n📚 Documentation:")
    print("   - README.md for detailed setup instructions")
    print("   - http://localhost:8000/docs for API documentation")
    print("   - config/.env.example for configuration reference")


if __name__ == "__main__":
    main()