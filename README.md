# Chatbot OpenRouter / OpenAI

This project automatically generates the project structure based on a description provided by the user. It uses the OpenRouter API or OpenAI API to obtain the project structure in JSON format and Streamlit to provide an interactive web interface.

## Prerequisites

- Python 3.8 or higher
- Pipenv

## Installation

1. Clone the repository or copy the project files to your machine.
2. Open a terminal in the project's root folder.
3. Install the dependencies via Pipenv:

   ```
   pipenv install
   ```

4. If, after installation and activating the environment with `pipenv shell`, the dependencies don't seem to be properly installed, you can install them manually:

   ```
   pipenv install streamlit openai python-dotenv
   ```

5. Create a `.env` file at the project's root and add your OpenRouter API key or OpenAI API key:

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

3. In the web interface that opens, you can:

   - Enter the **absolute path** where you wish to create the project structure.
   - Enter a **description** of your project in the text area.

4. Click **"Generate Application"** to generate the code fo each files.

## API Configuration

Ensure you have the appropriate API key set in your `.env` file for the service you choose to use.

## License

This project is licensed under the Creative Commons Attribution-NonCommercial 4.0 International License - see the [LICENSE](LICENSE) file for details.

## Notes

- Ensure that the provided path is valid and accessible.
- The application uses placeholders to indicate the generation status (in progress, success, or error).
- The generated project includes both the project structure and the initial code. However, you'll need to review and refine the code afterwards to ensure everything runs as expected. This setup serves as a solid foundation.
- You can customize and modify the generated files according to your needs.
