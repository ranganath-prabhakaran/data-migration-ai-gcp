from google.cloud import secretmanager
import os

class SecretManager:
    """
    A client for securely accessing secrets from Google Cloud Secret Manager.
    Caches secrets to avoid repeated API calls.
    """
    _instance = None
    _secrets_cache = {}

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(SecretManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        # The project ID for Secret Manager is itself a secret, fetched once.
        self.project_id = os.environ.get("GCP_PROJECT_ID")
        if not self.project_id:
            # Fallback for local testing if env var not set
            try:
                client = secretmanager.SecretManagerServiceClient()
                # A common convention could be to store the project_id in a known project
                # but for simplicity, we assume it's set in the environment on the VM.
                # Here we will hardcode a fallback for local simulation.
                # On the VM, the gcloud command will set this env var.
                self.project_id = "your-gcp-project-id" 
            except Exception:
                # If credentials aren't configured, we can't proceed.
                self.project_id = None
        
        if self.project_id:
            self.client = secretmanager.SecretManagerServiceClient()

    def get_secret(self, secret_id: str, version: str = "latest") -> str | None:
        """
        Retrieves a secret value from Secret Manager.
        
        Args:
            secret_id: The ID of the secret.
            version: The version of the secret (default is 'latest').

        Returns:
            The secret value as a string, or None if not found.
        """
        if not self.project_id:
            return None
            
        if secret_id in self._secrets_cache:
            return self._secrets_cache[secret_id]

        try:
            name = self.client.secret_version_path(self.project_id, secret_id, version)
            response = self.client.access_secret_version(request={"name": name})
            payload = response.payload.data.decode("UTF-8")
            self._secrets_cache[secret_id] = payload
            return payload
        except Exception as e:
            print(f"Could not access secret '{secret_id}': {e}")
            return None