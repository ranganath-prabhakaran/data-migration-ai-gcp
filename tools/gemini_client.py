import google.generativeai as genai
from .secret_manager import SecretManager

class GeminiClient:
    """
    A client for interacting with the Google Gemini API.
    It fetches the API key securely from Secret Manager.
    """
    def __init__(self, secret_manager: SecretManager, model_name: str = "gemini-1.5-flash-latest"):
        self.secret_manager = secret_manager
        self.model_name = model_name
        self._configure()

    def _configure(self):
        """Fetches the API key and configures the genai module."""
        api_key = self.secret_manager.get_secret("gemini_api_key")
        if not api_key:
            raise ValueError("Gemini API key not found in Secret Manager.")
        genai.configure(api_key=api_key)

    def __call__(self, messages: list[dict]) -> str:
        """
        Makes a call to the Gemini API.
        This adapts the AutoGen message format to what Gemini expects.
        """
        # Find the last message from the 'user' to use as the prompt
        prompt = next((m['content'] for m in reversed(messages) if m.get('role') == 'user'), None)

        if not prompt:
            return "No user prompt found in messages."

        model = genai.GenerativeModel(self.model_name)
        try:
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Error calling Gemini API: {e}"