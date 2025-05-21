# MorphAIus

This project uses AI to generate complete, functional applications based on user descriptions. It leverages the OpenRouter API to design, generate, and validate application code. The Flask interface provides an intuitive and modern way to create applications without writing code.

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

2. Launch the Flask application:

   ```
   python run.py
   ```

3. Open your browser and navigate to http://localhost:5000

4. Fill in the application description, select your options, and click **"Generate Application"** to begin creating your application.

## Modern UI Features

The application now includes a modern, responsive UI with:

- **Interactive Dashboard**: Easy-to-use interface with modern design elements
- **Real-time Feedback**: Visual indicators show generation progress
- **Animations and Effects**: Smooth transitions and visual feedback
- **Preview Functionality**: View the generated application directly in the interface
- **Responsive Design**: Works seamlessly on desktop and mobile devices

## MCP Tools Enhancement

This application includes Model Context Protocol (MCP) tools integration to enhance code generation:

- **Web Search Tool**: Searches the web for information relevant to your project
- **Documentation Search Tool**: Retrieves documentation for specific technologies and frameworks
- **Frontend Component Tool**: Finds and suggests UI components and patterns for frontend development
- **Frontend Templates Tool**: Locates templates and design inspirations for various application types
- **Animation Resources Tool**: Provides CSS animations and transitions for more engaging UI

These tools allow the AI to access external information when needed, resulting in more accurate and feature-rich code generation.

### Frontend Resource Integration

The application includes a curated collection of frontend resources:

- **UI Frameworks**: Bootstrap, Tailwind CSS, Bulma, Material Design
- **Component Libraries**: Navigation bars, cards, forms, buttons, modals, and tables
- **Animation Libraries**: Animate.css, Hover.css, AOS (Animate On Scroll)
- **Template Websites**: Resources for portfolios, landing pages, dashboards, and e-commerce sites

You can select your preferred UI framework in the sidebar options, or let the AI choose the most appropriate one for your project.

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
  pipenv install flask openai python-dotenv asyncio
  ```

## API Configuration

The application uses AI models for code generation through OpenRouter's API, with the default model being `google/gemini-2.5-pro-exp-03-25:free`.

You can configure these settings in `src/config/constants.py`:

- Change model names in `DEFAULT_MODEL` variable
- Adjust temperature settings for different generation tasks to control creativity vs precision

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](./LICENSE) file for details.

## Notes

- Ensure that the provided output directory is valid and accessible.
- The application generates complete, functional code but may require minor adjustments for complex use cases.
- The quality of the generated application depends on the clarity and detail in your description.
- More complex applications may require additional dependencies to be installed manually.
- Static website generation produces pure HTML/CSS/JS files that can be hosted on any web server.
- MCP tools enhance generation but may require internet access to function properly.

## Compiling the Application (for Desktop Use)

If you want to create a standalone desktop executable (.exe on Windows) from this project, you can use PyInstaller. This project includes a `launcher.py` script and a `launcher.spec` file configured to help package the application with `pywebview` for a native window experience.

**Prerequisites for Compiling:**

*   Ensure all development dependencies are installed:
    ```powershell
    pipenv install
    ```
    (PyInstaller should ideally be listed as a dev dependency in your `Pipfile` if you compile frequently. If not, you can install it in your pipenv environment: `pipenv install pyinstaller`)
*   You will need an icon file in `.ico` format if you want to set a custom icon for the executable (e.g., `static/images/favicon.ico`).

**Compilation Steps:**

1.  **Activate the Pipenv Environment**:
    Open your terminal in the project root directory and run:
    ```powershell
    pipenv shell
    ```

2.  **Clean Previous Builds (Recommended)**:
    Before each compilation, it's good practice to remove any previous build artifacts:
    ```powershell
    Remove-Item -Recurse -Force ./build
    Remove-Item -Recurse -Force ./dist
    ```

3.  **Compile using `launcher.spec`**:
    The `launcher.spec` file contains the configuration for PyInstaller.

    *   **To create a bundled application in a folder** (output in `dist/YourAppName/`):
        ```powershell
        pyinstaller launcher.spec
        ```

4.  **Running the Compiled Application**:
    After a successful compilation, navigate to the `dist/` folder. 
    *   You can run `dist/BotProjectCreator.exe` directly.

A `launcher_debug.log` file will be created in the same directory as the executable, which can be helpful for troubleshooting if the application doesn't start as expected.
