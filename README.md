# AI Application Generator

This project uses AI to generate complete, functional applications based on user descriptions. It leverages the OpenAI API to design, generate, and validate application code. The Streamlit interface provides an intuitive way to create applications without writing code.

## Features

- **Complete Application Generation**: Creates fully functional applications from text descriptions
- **Multiple Technology Support**: Generates apps in various programming languages and frameworks
- **Static Website Mode**: Option to create simple HTML/CSS/JS websites
- **Validation System**: Tests and validates generated applications to ensure they run correctly
- **AI Agent Team**: Uses a team of specialized AI agents to verify and improve the generated code
- **Auto-fixing Capabilities**: Automatically fixes common issues in the generated code
- **File Download**: Download the complete project as a ZIP file

## Prerequisites

- Python 3.8 or higher
- Pipenv
- OpenAI API key

## Installation

1. Clone the repository or copy the project files to your machine.
2. Open a terminal in the project's root folder.
3. Install the dependencies via Pipenv:

   ```
   pipenv install
   ```

4. Install additional required packages:

   ```
   pipenv install streamlit openai python-dotenv agno duckduckgo-search
   ```
   
   Note: The `agno` package is required for the AI agent team that verifies and improves the generated code.

5. Create a `.env` file at the project's root and add your OpenAI API key:

   ```
   OPENAI_API_KEY=<your_api_key>
   ```

## Usage

1. Activate the Pipenv environment:

   ```
   pipenv shell
   ```

2. Launch the Streamlit application:

   ```
   streamlit run app.py
   ```

3. In the web interface that opens:
   - Describe the application you want to build in the text area
   - Set the output directory where you want the application to be generated
   - Configure advanced options if needed:
     - Static website generation (HTML/CSS/JS only)
     - Test generation
     - Docker configuration
     - CI/CD configuration
     - Use sample JSON data instead of a database
     - Extended dependency installation time

4. Click **"Generate Application"** to start the process.

5. Review the AI-reformulated requirements in the next tab and make any needed changes.

6. Click **"Proceed with Generation"** to begin creating your application.

7. When generation is complete, you can download the entire application as a ZIP file.

## Example Prompts

For best results, try to be specific in your descriptions. Here are some example prompts:

1. **Static Website**:
   ```
   Create a static portfolio website for a photographer with a homepage, gallery, about, and contact pages. Include a responsive design with a modern look.
   ```

2. **Web Application**:
   ```
   Build a task management application with user authentication. Users should be able to create, update, and delete tasks, set due dates, and mark tasks as completed.
   ```

3. **API Service**:
   ```
   Create a RESTful API for a blog platform with endpoints for posts, comments, and users. Include authentication and proper error handling.
   ```

## Advanced Options

- **Static Website**: Generates a simple HTML/CSS/JS website without a backend server.
- **Generate Tests**: Includes test files for the application.
- **Docker Configuration**: Adds Dockerfile and docker-compose.yml files.
- **CI/CD Configuration**: Adds GitHub Actions or similar CI/CD configuration.
- **Use Sample JSON Data**: Uses JSON files for data storage instead of a database.
- **Extended Dependency Wait**: Adds extra delay after installing dependencies to ensure they are properly installed.

## AI Agent Team Verification

The application uses a team of specialized AI agents to verify and improve the generated code:

1. **Project Manager Agent**: Coordinates the validation process and ensures overall project quality.
2. **Frontend Developer Agent**: Focuses on improving UI/UX, HTML, CSS, and JavaScript code.
3. **Backend Developer Agent**: Validates server-side code, APIs, and business logic.

The agent team runs in the background after code generation and creates a `verification_complete.txt` file in the project directory when finished.

## Generation Process

The system follows these steps to create your application:
1. Requirements Analysis: Parses your description into structured requirements
2. Architecture Design: Creates a technical architecture based on the requirements
3. Database Schema Design: Designs database models if needed
4. API Design: Creates API endpoints when required
5. Code Generation: Writes all necessary code files
6. Validation: Tests the generated application for errors
7. Auto-fixing: Automatically corrects common issues
8. Agent Team Verification: Uses specialized AI agents to further improve the code

## Troubleshooting

- **API Key Issues**: Make sure your OpenAI API key is correctly set in the `.env` file.
- **Dependency Errors**: If you encounter any dependency errors, try installing them manually:
  ```
  pip install streamlit openai python-dotenv agno duckduckgo-search
  ```
- **Generation Failures**: For complex applications, try breaking down your request into smaller, more specific parts.
- **Agent Team Errors**: If the agent team verification fails, you can still download and use the generated code.

## API Configuration

The application uses AI models for code generation. By default, it uses OpenRouter's API with the `google/gemini-2.0-flash-001` model, but it can also be configured to use OpenAI's models (default: `gpt-4o-mini`).

You can configure these settings in `src/config/constants.py`:
- Set `USE_OPENROUTER` to `True` or `False` to switch between OpenRouter and OpenAI APIs
- Change model names in `OPENROUTER_MODEL` or `API_MODEL` variables
- Adjust temperature settings for different generation tasks to control creativity vs precision

### OpenRouter Integration

The application integrates with OpenRouter which provides several advantages:
- Access to various AI models from different providers through a single unified API
- Potentially lower costs compared to direct OpenAI API usage
- Support for alternative models like Google's Gemini, Anthropic's Claude, and others

To use OpenRouter:
1. Create an account at [OpenRouter](https://openrouter.ai/)
2. Generate your API key from the OpenRouter dashboard
3. Add it to your `.env` file:
   ```
   OPENROUTER_API_KEY=your_openrouter_api_key
   ```
4. Ensure `USE_OPENROUTER=True` is set in your configuration

The application will automatically fall back to using OpenAI if OpenRouter is enabled but no valid OpenRouter API key is found in the environment variables.

## License

This project is licensed under the Creative Commons Attribution-NonCommercial 4.0 International License - see the [LICENSE](LICENSE.md) file for details.

## Notes

- Ensure that the provided output directory is valid and accessible.
- The application generates complete, functional code but may require minor adjustments for complex use cases.
- The quality of the generated application depends on the clarity and detail in your description.
- More complex applications may require additional dependencies to be installed manually.
- Static website generation produces pure HTML/CSS/JS files that can be hosted on any web server.
- The AI agent team will continue to work in the background after generation is complete to improve the code.
