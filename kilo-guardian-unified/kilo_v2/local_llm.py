# kilo_v2/local_llm.py
import os

try:
    from llama_cpp import Llama
except Exception:
    Llama = None


class LocalLlm:
    """
    A class to interact with a locally hosted GGUF model using llama-cpp-python.
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(LocalLlm, cls).__new__(cls)
        return cls._instance

    def __init__(self, model_path: str, n_ctx: int = 4096, n_gpu_layers: int = 0):
        """
        Initializes the LocalLlm singleton.

        Args:
            model_path (str): The absolute path to the GGUF model file.
            n_ctx (int): The context window size for the model.
            n_gpu_layers (int): The number of layers to offload to GPU.
                                Set to 0 to run entirely on CPU.
        """
        if hasattr(self, "_initialized") and self._initialized:
            return

        if Llama is None:
            raise RuntimeError("llama_cpp is not installed; local LLM is unavailable")

        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Model file not found at: {model_path}. "
                "Please download the model and update the path in your config."
            )

        self.model_path = model_path
        self.llm = Llama(
            model_path=self.model_path,
            n_ctx=n_ctx,
            n_gpu_layers=n_gpu_layers,
            verbose=False,  # Set to True for detailed logging
        )
        self._initialized = True
        print("LocalLlm initialized successfully.")

    def call(self, prompt: str, stop: list = None, max_tokens: int = 512) -> str:
        """
        Calls the local LLM with a given prompt.

        Args:
            prompt (str): The prompt to send to the model.
            stop (list, optional): A list of strings to stop generation at. Defaults to None.
            max_tokens (int): The maximum number of tokens to generate.

        Returns:
            str: The model's response text.
        """
        if stop is None:
            stop = ["\n"]

        output = self.llm(prompt, max_tokens=max_tokens, stop=stop, echo=False)

        return output["choices"][0]["text"].strip()


# Example Usage (for demonstration)
if __name__ == "__main__":
    # This block shows how you would use the LocalLlm class.
    # IMPORTANT: You must download the model file first and provide the correct path.
    # For example: '/home/kilo/models/Phi-3-mini-4k-instruct.Q4_K_M.gguf'

    MODEL_PATH = os.environ.get("LOCAL_LLM_MODEL_PATH")

    if not MODEL_PATH:
        print(
            "Skipping LocalLlm example: LOCAL_LLM_MODEL_PATH environment variable not set."
        )
        print(
            "Please set this variable to the full path of your downloaded GGUF model file."
        )
    else:
        try:
            local_model = LocalLlm(model_path=MODEL_PATH)

            test_prompt = "Question: What is the capital of France? Answer:"
            response = local_model.call(test_prompt)

            print(f"\n--- Local LLM Test ---")
            print(f"Prompt: {test_prompt}")
            print(f"Response: {response}")

        except FileNotFoundError as e:
            print(f"Error: {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
