import logging
import os

from fastapi import APIRouter
from huggingface_hub import hf_hub_download

logger = logging.getLogger("ModelManager")

# Default model configuration, with overrides from environment variables
DEFAULT_REPO_ID = os.getenv("LOCAL_LLM_REPO_ID", "MaziyarGoli/Llama-3-8B-Instruct-GGUF")
DEFAULT_FILENAME = os.getenv("LOCAL_LLM_FILENAME", "Llama-3-8B-Instruct-Q4_K_M.gguf")
DEFAULT_MODEL_DIR = os.getenv("LOCAL_LLM_MODEL_DIR", "/home/kilo/models")
DEFAULT_TARGET_NAME = os.getenv("LOCAL_LLM_MODEL_NAME", "local_llm_q4.gguf")

router = APIRouter()


def download_and_install_model(
    repo_id: str = DEFAULT_REPO_ID,
    filename: str = DEFAULT_FILENAME,
    local_dir: str = DEFAULT_MODEL_DIR,
    target_name: str = DEFAULT_TARGET_NAME,
):
    """
    Downloads a quantized GGUF model from Hugging Face Hub and renames it.

    Args:
        repo_id (str): The Hugging Face repository ID.
        filename (str): The specific filename of the model to download.
        local_dir (str): The local directory to save the model.
        target_name (str): The name to rename the downloaded file to.
    """
    logger.info(
        f"Attempting to download model: {repo_id}/{filename} to {local_dir} "
        f"and rename to {target_name}"
    )

    os.makedirs(local_dir, exist_ok=True)
    local_path = os.path.join(local_dir, filename)
    target_path = os.path.join(local_dir, target_name)

    if os.path.exists(target_path):
        logger.info(f"Model already exists at {target_path}. Skipping download.")
        return True
    elif os.path.exists(local_path):
        logger.info(
            f"Model file {filename} exists, but not renamed. Renaming to {target_name}."
        )
        try:
            os.rename(local_path, target_path)
            logger.info(f"Model successfully renamed to {target_path}.")
            return True
        except OSError as e:
            logger.error(
                f"Error renaming existing model file {local_path} to {target_path}: {e}"
            )
            return False

    try:
        hf_hub_download(
            repo_id=repo_id,
            filename=filename,
            local_dir=local_dir,
            local_dir_use_symlinks=False,
            resume_download=True,
        )
        logger.info(f"Model successfully downloaded to {local_path}")
        logger.info(f"Renaming model to '{target_name}' for consistent configuration.")
        os.rename(local_path, target_path)
        logger.info(f"Model renamed successfully to {target_path}.")
        return True
    except Exception as e:
        logger.error(f"ERROR: Model download or rename failed: {e}", exc_info=True)
        logger.error("Please check your internet connection and huggingface.co status.")
        return False


def get_model_status(
    model_path: str = os.path.join(DEFAULT_MODEL_DIR, DEFAULT_TARGET_NAME)
):
    """
    Checks the status of the specified model.

    Args:
        model_path (str): The full path to the model file.

    Returns:
        dict: A dictionary containing the model's status and details.
    """
    status = {
        "model_name": DEFAULT_TARGET_NAME,
        "path": model_path,
        "exists": os.path.exists(model_path),
        "size_bytes": 0,
        "last_modified": None,
        "status": "unavailable",
        "message": "Model file not found.",
    }

    if status["exists"]:
        try:
            stat_info = os.stat(model_path)
            status["size_bytes"] = stat_info.st_size
            status["last_modified"] = stat_info.st_mtime
            status["status"] = "ready"
            status["message"] = "Model is available and ready for use."
        except OSError as e:
            status["status"] = "error"
            status["message"] = f"Error accessing model file: {e}"
    else:
        status["status"] = "missing"
        status["message"] = (
            "Model file is missing. Run download_and_install_model to get it."
        )
    return status


@router.get("/api/model/status")
def api_model_status():
    return get_model_status()


@router.post("/api/model/download")
def api_model_download(
    repo_id: str = DEFAULT_REPO_ID, filename: str = DEFAULT_FILENAME
):
    ok = download_and_install_model(repo_id=repo_id, filename=filename)
    return {"success": ok}


@router.post("/api/model/switch")
def api_model_switch(filename: str):
    # TODO: Implement logic to switch active model (update symlink or config)
    return {"status": "not_implemented"}


# Example of how to use it (for testing or direct execution)
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger.info("Running ModelManager as a script.")

    current_status = get_model_status()
    logger.info(f"Initial model status: {current_status}")

    if not current_status["exists"]:
        logger.info("Model not found, attempting to download and install...")
        success = download_and_install_model()
        if success:
            logger.info("Model download and installation completed successfully.")
        else:
            logger.error("Model download and installation failed.")

    final_status = get_model_status()
    logger.info(f"Final model status: {final_status}")
