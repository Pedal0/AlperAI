# 🚀 MorphAIus - AI Application Generator

MorphAIus is an intelligent application generator that uses AI to create complete, functional applications based on your descriptions. It leverages the OpenRouter API to access multiple AI models (GPT-4, Claude, Llama, etc.) and generates applications with a modern Flask web interface.

## ✨ Features

- **AI-powered code generation**: Describe your app, get complete working code
- **Modern web interface**: Responsive dashboard with real-time preview
- **Multi-technology support**: Static sites, web apps, REST APIs, and more
- **MCP integration**: Enhanced generation with web search and documentation tools
- **Built-in frameworks**: Bootstrap, Tailwind CSS, Material Design support
- **Code validation**: Automatic verification and error correction

## 📋 Prerequisites

- **Python 3.8+**
- **Node.js 16+** and **npm** - Required for RepoMix codebase analysis
  - Download from [Node.js official website](https://nodejs.org/)
  - Verify installation: `node --version` and `npm --version`
- **RepoMix** (required for codebase analysis)
  - Install globally: `npm install -g repomix`
  - Verify installation: `repomix --help`
- **OpenRouter API Key** - Get one at [OpenRouter](https://openrouter.ai/)
- **Git** (optional, for cloning)

## 🛠️ Installation

### 0. Install RepoMix (required for codebase analysis)

Before running the project, make sure RepoMix is installed globally:

```bash
npm install -g repomix
```

You can verify the installation with:

```bash
repomix --help
```

### Option 1: Using Pipenv (Recommended)

1. **Clone and setup**:
   ```bash
   git clone https://github.com/Pedal0/MorphAIus.git
   cd MorphAIus
   pip install pipenv  # If you don't have pipenv
   pipenv install
   ```

2. **Configure API key**:
   Create a `.env` file:
   ```bash
   OPENROUTER_API_KEY=your_openrouter_api_key
   ```

### Option 2: Using pip

1. **Clone and setup**:
   ```bash
   git clone https://github.com/Pedal0/MorphAIus.git
   cd MorphAIus
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   # Linux/macOS
   source venv/bin/activate
   
   pip install -r requirements.txt
   ```

2. **Configure API key**:
   Create a `.env` file:
   ```bash
   OPENROUTER_API_KEY=your_openrouter_api_key
   ```

## 🚀 Usage

### With Pipenv
```bash
pipenv shell
python run.py
```

### With pip
```bash
# Activate virtual environment first (if using)
# Windows: venv\Scripts\activate
# Linux/macOS: source venv/bin/activate

python run.py
```

**Access the app**: Open `http://localhost:5000` in your browser

## 📖 How it Works

1. **Describe your app**: Use the web interface to describe what you want to build
2. **Configure options**: Choose UI framework, project type, and other settings
3. **AI generation**: The system generates complete, working code
4. **Preview & download**: Review your app and download the generated files

## 🔧 Technologies Used

- **Backend**: Flask, OpenRouter API, MCP (Model Context Protocol)
- **Frontend**: Bootstrap 5, JavaScript ES6+, Font Awesome
- **AI Models**: GPT-4, Claude, Llama (via OpenRouter)
- **Tools**: Web search, documentation lookup, code validation

## 🎯 Supported Application Types

MorphAIus can generate various types of applications:

- **Static Websites**: Portfolios, landing pages, business sites, blogs
- **Web Applications**: CRUD apps, dashboards, e-commerce, social platforms
- **APIs & Services**: REST APIs, microservices, authentication systems
- **Templates**: Responsive designs with modern UI frameworks

## 💡 Example Prompts

### Portfolio Website
```
Create a modern portfolio website for a web developer with:
- Homepage with intro and photo
- Projects section with interactive gallery
- About page with skills and experience
- Contact form
- Responsive design
```

### Task Management App
```
Build a task management application with:
- User authentication
- Create, edit, delete tasks
- Categories and priorities
- Due dates and notifications
- Modern Trello-like interface
```

## 🔧 Troubleshooting

**API Key Error**:
- Check your OpenRouter API key in the `.env` file
- Ensure the key is valid and active

**Dependency Issues**:
```bash
# With Pipenv
pipenv install flask openai python-dotenv

# With pip
pip install flask openai python-dotenv
```

**Port Already in Use**:
- Default port is 5000, modify in `run.py` if needed

**Generation Problems**:
- Check internet connection
- Try simpler prompts first
- Check logs in `logs/app_flask.log`

## 📦 Building Executable (Optional)

Create a standalone executable:

```bash
pipenv install pyinstaller
pipenv shell
pyinstaller launcher.spec
```

The executable will be in `dist/MorphAIus.exe`

## 📄 License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](./LICENSE.md) file for details.

## 🤝 Contributing

Contributions are welcome! Feel free to:
- Report bugs
- Suggest new features

## 🔗 Useful Links

- [OpenRouter](https://openrouter.ai/) - AI API Platform
- [Flask Documentation](https://flask.palletsprojects.com/) - Web Framework
- [Bootstrap 5](https://getbootstrap.com/) - CSS Framework
- [Model Context Protocol](https://modelcontextprotocol.io/) - MCP Protocol

---

⭐ **Don't forget to star the project if you find it useful!**
