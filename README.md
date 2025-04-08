# AI Application Generator

This project uses AI to generate complete, functional applications based on user descriptions. It leverages the OpenRouter API to design, generate, and validate application code. The Streamlit interface provides an intuitive way to create applications without writing code.


## Prerequisites

- Python 3.8 or higher
- Pipenv
- OpenRouter API key (you can get one at [OpenRouter](https://openrouter.ai/))

## Installation

1. Clone the repository:

   ```
   git clone https://github.com/Pedal0/bot-project-creator
   cd bot-project-creator
   ```

2. Install dependencies using Pipenv:

   ```
   pipenv install
   ```

3. Create a `.env` file at the project's root and add your OpenRouter API key:
   ```
   OPENROUTER_API_KEY=your_openrouter_api_key
   ```
   If you don't have an OpenRouter API key, you can get one by signing up at [OpenRouter](https://openrouter.ai/).

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

   - Enter your OpenRouter API key in the sidebar (if not already in your .env file)
   - Describe the application you want to build in the text area
   - Set the output directory where you want the application to be generated
   - Configure advanced options if needed:
     - Static website generation (HTML/CSS/JS only)
     - Test generation
     - Docker configuration
     - CI/CD configuration
     - Use sample JSON data instead of a database
     - Extended dependency installation time
   - Click **"Generate Application"** to start the process.

4. Review the AI-reformulated requirements in the next tab and make any needed changes.

5. Click **"Proceed with Generation"** to begin creating your application.

6. When generation is complete, you can download the entire application as a ZIP file.

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

## Troubleshooting

- **API Key Issues**: Make sure your OpenRouter API key is correctly set in the `.env` file.
- **Dependency Errors**: If you encounter any dependency errors, try installing them manually:
  ```
  pienv install streamlit openai python-dotenv
  ```

## API Configuration

The application uses AI models for code generation through OpenRouter's API, with the default model being `google/gemini-2.5-pro-exp-03-25:free`.

You can configure these settings in `src/config/constants.py`:

- Change model names in `DEFAULT_MODEL` variable
- Adjust temperature settings for different generation tasks to control creativity vs precision

## License

This project is licensed under the Creative Commons Attribution-NonCommercial 4.0 International License - see the [LICENSE](LICENSE.md) file for details.

## Notes

- Ensure that the provided output directory is valid and accessible.
- The application generates complete, functional code but may require minor adjustments for complex use cases.
- The quality of the generated application depends on the clarity and detail in your description.
- More complex applications may require additional dependencies to be installed manually.
- Static website generation produces pure HTML/CSS/JS files that can be hosted on any web server.
