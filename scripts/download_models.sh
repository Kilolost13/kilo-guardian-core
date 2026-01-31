#!/bin/bash

# Model Pre-download Script for Kilo AI
# Run this on an internet-connected machine to download all models
# Then transfer the models.tar.gz to your Beelink for offline deployment

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODELS_DIR="$SCRIPT_DIR/models_offline"
OLLAMA_MODELS_DIR="$MODELS_DIR/ollama"

echo "=================================================="
echo "  Kilo AI - Model Download Script"
echo "=================================================="
echo ""
echo "This script downloads all AI models needed for"
echo "offline deployment on the Beelink SER7-9."
echo ""
echo "Download location: $MODELS_DIR"
echo "Estimated download size: ~8GB"
echo "Estimated time: 10-30 minutes (depends on connection)"
echo ""

# Create directories
mkdir -p "$MODELS_DIR"
mkdir -p "$OLLAMA_MODELS_DIR"
mkdir -p "$MODELS_DIR/sentence_transformers"
mkdir -p "$MODELS_DIR/tesseract"

echo "=================================================="
echo "Step 1: Downloading Llama 3.1 8B Model"
echo "=================================================="
echo "Size: ~5GB"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Pull Ollama image
echo "Pulling Ollama Docker image..."
docker pull ollama/ollama:latest

# Run Ollama container temporarily
echo "Starting temporary Ollama container..."
OLLAMA_CONTAINER=$(docker run -d --name ollama-download -v "$OLLAMA_MODELS_DIR:/root/.ollama" ollama/ollama:latest)

# Wait for Ollama to start
echo "Waiting for Ollama to initialize..."
sleep 10

# Pull Llama 3.1 8B model
echo "Downloading Llama 3.1 8B (Q5_K_M quantization)..."
docker exec ollama-download ollama pull llama3.1:8b-instruct-q5_K_M

# Stop and remove container
echo "Stopping Ollama container..."
docker stop ollama-download
docker rm ollama-download

echo "✅ Llama 3.1 8B downloaded successfully"
echo ""

echo "=================================================="
echo "Step 2: Downloading Sentence Transformers Model"
echo "=================================================="
echo "Model: all-MiniLM-L6-v2"
echo "Size: ~80MB"
echo ""

# Download sentence transformers using Python
python3 << 'PYTHON_SCRIPT'
import os
import sys

try:
    from sentence_transformers import SentenceTransformer

    models_dir = os.environ.get('MODELS_DIR', './models_offline')
    cache_dir = os.path.join(models_dir, 'sentence_transformers')

    print(f"Downloading to: {cache_dir}")

    # Download the model
    model = SentenceTransformer('all-MiniLM-L6-v2', cache_folder=cache_dir)

    # Test it
    test_embedding = model.encode("Test sentence")
    print(f"✅ Model downloaded and tested successfully")
    print(f"   Embedding dimension: {len(test_embedding)}")

except ImportError:
    print("❌ sentence-transformers not installed")
    print("   Installing now...")
    import subprocess
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'sentence-transformers'])
    print("   Please run this script again")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
PYTHON_SCRIPT

echo ""

echo "=================================================="
echo "Step 3: Downloading Tesseract Language Data"
echo "=================================================="
echo "Language: English (eng.traineddata)"
echo "Size: ~15MB"
echo ""

# Download Tesseract English trained data
TESS_URL="https://github.com/tesseract-ocr/tessdata/raw/main/eng.traineddata"
wget -O "$MODELS_DIR/tesseract/eng.traineddata" "$TESS_URL"

if [ -f "$MODELS_DIR/tesseract/eng.traineddata" ]; then
    echo "✅ Tesseract language data downloaded"
else
    echo "❌ Failed to download Tesseract data"
fi

echo ""

echo "=================================================="
echo "Step 4: Optional - Whisper Model for Voice"
echo "=================================================="
echo "Model: whisper-small"
echo "Size: ~244MB"
echo ""

read -p "Download Whisper model for voice features? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    mkdir -p "$MODELS_DIR/whisper"

    python3 << 'PYTHON_SCRIPT'
import os
import sys

try:
    # Try importing faster-whisper
    try:
        from faster_whisper import WhisperModel

        models_dir = os.environ.get('MODELS_DIR', './models_offline')
        cache_dir = os.path.join(models_dir, 'whisper')

        print(f"Downloading Whisper to: {cache_dir}")

        # Download the model
        model = WhisperModel("small", device="cpu", compute_type="int8", download_root=cache_dir)

        print(f"✅ Whisper model downloaded successfully")

    except ImportError:
        print("faster-whisper not installed, trying whisper...")
        import whisper

        models_dir = os.environ.get('MODELS_DIR', './models_offline')

        # Download model
        model = whisper.load_model("small", download_root=models_dir)

        print(f"✅ Whisper model downloaded successfully")

except ImportError:
    print("❌ Whisper not installed. Skipping.")
    print("   Install with: pip install faster-whisper")
except Exception as e:
    print(f"⚠️  Error downloading Whisper: {e}")
    print("   Continuing without Whisper model")
PYTHON_SCRIPT
else
    echo "Skipping Whisper model"
fi

echo ""

echo "=================================================="
echo "Step 5: Creating Transfer Package"
echo "=================================================="
echo ""

echo "Calculating total size..."
TOTAL_SIZE=$(du -sh "$MODELS_DIR" | cut -f1)
echo "Total downloaded: $TOTAL_SIZE"
echo ""

echo "Creating compressed archive..."
cd "$SCRIPT_DIR"
tar -czf models.tar.gz -C models_offline .

if [ -f "models.tar.gz" ]; then
    ARCHIVE_SIZE=$(du -sh models.tar.gz | cut -f1)
    echo "✅ Archive created: models.tar.gz ($ARCHIVE_SIZE)"
else
    echo "❌ Failed to create archive"
    exit 1
fi

echo ""
echo "=================================================="
echo "  Download Complete!"
echo "=================================================="
echo ""
echo "📦 Package: $SCRIPT_DIR/models.tar.gz"
echo "📏 Size: $ARCHIVE_SIZE"
echo ""
echo "Next steps:"
echo "1. Transfer models.tar.gz to your Beelink SER7-9"
echo "2. Extract: tar -xzf models.tar.gz -C /path/to/microservice/"
echo "3. Models will be available for offline use"
echo ""
echo "Transfer methods:"
echo "  - USB drive"
echo "  - SCP: scp models.tar.gz kilo@192.168.1.100:~/"
echo "  - Local network share"
echo ""
echo "After transfer, run on Beelink:"
echo "  cd /path/to/microservice"
echo "  tar -xzf ~/models.tar.gz"
echo "  docker-compose up -d"
echo ""
echo "=================================================="

# Create extraction script
cat > extract_models.sh << 'EOF'
#!/bin/bash

# Extract models on Beelink (offline)

echo "Extracting Kilo AI models..."

# Extract main archive
tar -xzf models.tar.gz

# Copy Ollama models to volume
echo "Setting up Ollama models..."
docker volume create microservice_ollama_models
docker run --rm -v microservice_ollama_models:/dest -v $(pwd)/ollama:/src alpine sh -c "cp -r /src/* /dest/"

# Copy sentence transformers
echo "Setting up sentence transformers..."
mkdir -p ./ai_brain/models
cp -r sentence_transformers/* ./ai_brain/models/

# Copy Tesseract data
echo "Setting up Tesseract..."
mkdir -p ./meds/tessdata
cp tesseract/eng.traineddata ./meds/tessdata/

echo "✅ Models extracted and ready!"
echo ""
echo "Start services with: docker-compose up -d"
EOF

chmod +x extract_models.sh

echo "✅ Extraction script created: extract_models.sh"
echo ""
echo "Happy deploying! 🚀"
