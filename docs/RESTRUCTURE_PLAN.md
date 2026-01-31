# Kilo AI Project Restructure Plan

**Date:** 2025-12-25
**Purpose:** Clean up project structure before pushing to new GitHub repository

---

## 1. CURRENT DIRECTORY STRUCTURE

### Root Level (`/home/kilo/Desktop/Kilo_Ai_microservice/`)
```
Kilo_Ai_microservice/
├── .git/                       # Parent git repository
├── .github/                    # GitHub Actions workflows (root)
│   ├── workflows/
│   │   ├── automerge-on-ci-success.yml
│   │   ├── ci-failure-reporter.yml
│   │   ├── playwright-e2e.yml
│   │   └── smoke-test.yml
│   └── CODEOWNERS
├── .venv/                      # Python virtual environment
├── .pytest_cache/              # Pytest cache (should be ignored)
├── .claude/                    # Claude Code settings
├── caddy                       # 39M binary ❌ PROBLEM
├── ollama                      # 34M binary ❌ PROBLEM
├── microservice/               # Main code directory (has own .git) ⚠️ NESTED REPO
├── Makefile                    # Build helpers (HAS TYPO)
├── pytest.ini                  # Pytest config
├── README.md                   # Root README
├── GEMINI.md                   # Project overview
├── .gitignore                  # Git ignore rules
└── .gitattributes              # Git LFS configuration
```

### Microservice Directory (`microservice/`)
```
microservice/
├── .git/                       # Nested git repo ⚠️ PROBLEM
│   └── (Separate repository: github.com/Kilolost13/microservice.git)
├── .github/                    # Duplicate GitHub config ❌ DUPLICATE
│   ├── workflows/
│   ├── ISSUE_TEMPLATE/
│   ├── copilot-instructions.md
│   └── PULL_REQUEST_TEMPLATE.md
├── __pycache__/                # Python cache ❌ SHOULD BE IGNORED
├── .pytest_cache/              # Pytest cache ❌ SHOULD BE IGNORED
│
├── SERVICES (The actual microservices):
├── ai_brain/                   # AI Brain service
├── cam/                        # Camera service
├── financial/                  # Financial service
├── gateway/                    # API Gateway
├── habits/                     # Habits tracking
├── library_of_truth/           # Knowledge base
├── meds/                       # Medications
├── ml_engine/                  # ML Engine
├── reminder/                   # Reminders service
│
├── RUNTIME DATA DIRECTORIES (should use Docker volumes):
├── ai_brain_data/              # 4K - Runtime data ⚠️ SHOULD USE VOLUMES
├── financial_data/             # 4K - Runtime data ⚠️
├── habits_data/                # 4K - Runtime data ⚠️
├── library_of_truth_data/      # 4K - Runtime data ⚠️
├── meds_data/                  # 4K - Runtime data ⚠️
├── reminder_data/              # 4K - Runtime data ⚠️
│
├── MISNAMED DIRECTORIES (should be renamed):
├── Data_top/                   # 13M - Should be "data/" ❌ BAD NAME
│   └── large-assets/
├── Docs_top/                   # 364K - Should be "docs/" ❌ BAD NAME
│   ├── (30+ markdown docs)
│   └── docs/                   # Nested docs directory!
├── Diagrams_top/               # 56K - Should be "diagrams/" ❌ BAD NAME
│   ├── diagrams/
│   └── mermaid/
├── Scripts_top/                # 188K - Should be "scripts/" ❌ BAD NAME
│   ├── history-cleanup/
│   ├── scripts/                # Nested scripts directory!
│   └── (various shell scripts)
│
├── DUPLICATE/NESTED DIRECTORIES:
├── microservice/               # 112K - DUPLICATE! ❌ CRITICAL PROBLEM
│   ├── conftest.py
│   ├── financial/              # Duplicate of ../financial/
│   ├── habits/                 # Duplicate of ../habits/
│   ├── integration/            # Duplicate of ../integration/
│   ├── library_of_truth/       # Duplicate of ../library_of_truth/
│   ├── meds/                   # Duplicate of ../meds/
│   ├── models/                 # Duplicate of ../models/
│   └── reminder/               # Duplicate of ../reminder/
│
├── SHARED CODE:
├── models/                     # Shared data models (20K)
│   ├── __init__.py
│   └── README.md
├── integration/                # Integration test Dockerfile
│
├── FRONTEND:
├── frontend/                   # React frontend (540M)
│   ├── kilo-react-frontend/
│   │   ├── src/
│   │   ├── public/
│   │   ├── build/
│   │   ├── node_modules/       # 540M - Properly ignored
│   │   ├── package.json
│   │   └── ...
│   ├── nginx-selfsigned.crt    # SSL cert for frontend
│   └── nginx-selfsigned.key    # SSL key
│
├── CONFIGURATION FILES:
├── docker-compose.yml          # Main orchestration (13 services)
├── docker-compose.test.yml     # Test configuration
├── pytest.ini                  # Pytest config
├── alembic.ini                 # DB migration config
├── .env                        # Environment variables
├── .gitignore                  # Git ignore
├── .gitattributes              # Git LFS config
├── __init__.py                 # Makes it a Python package
├── kilos_memory.db             # SQLite database (empty, 0 bytes)
│
├── DOCUMENTATION:
├── README.md                   # Main README (842 bytes - minimal)
├── CODE_OF_CONDUCT.md
├── CONTRIBUTING.md
└── LICENSE
```

---

## 2. IDENTIFIED PROBLEMS

### 🔴 CRITICAL ISSUES

#### A. Nested Git Repository Configuration
**Problem:** Two separate git repositories in parent/child relationship
- Parent: `/home/kilo/Desktop/Kilo_Ai_microservice/.git`
- Child: `/home/kilo/Desktop/Kilo_Ai_microservice/microservice/.git`
- NO `.gitmodules` file configuring this as a submodule

**Impact:**
- Git commands show confusing status
- Unclear which repo to push/pull from
- Difficult for collaborators to understand structure

**Recommendation:** Choose ONE structure (see options below)

#### B. Duplicate Nested `microservice/microservice/` Directory
**Location:** `microservice/microservice/`
**Size:** 112K
**Contains:** Duplicate copies of 7 service directories
- financial/, habits/, integration/, library_of_truth/, meds/, models/, reminder/

**Impact:**
- Confusion about which code is canonical
- Import path errors
- Wasted disk space
- pytest explicitly excludes it

**Action:** DELETE this entire directory

#### C. Large Binaries in Git Root
**Files:**
- `caddy` (39M) - Web server binary
- `ollama` (34M) - LLM runtime binary

**Problem:**
- Binaries shouldn't be in git
- Repository size bloat
- Not cross-platform compatible
- Difficult to update

**Action:** Remove from git, add to .gitignore, document how to obtain

### ⚠️ MAJOR ISSUES

#### D. Poor Directory Naming Convention
**Problem:** Four directories use `*_top` suffix
- `Data_top/` → should be `data/`
- `Docs_top/` → should be `docs/`
- `Diagrams_top/` → should be `diagrams/`
- `Scripts_top/` → should be `scripts/`

**Impact:**
- Unprofessional naming
- Inconsistent with industry standards
- The `_top` suffix serves no clear purpose

**Action:** Rename all to standard names

#### E. Runtime Data Directories in Source Code
**Problem:** Six `*_data/` directories in source tree
- ai_brain_data/, financial_data/, habits_data/, library_of_truth_data/, meds_data/, reminder_data/

**Impact:**
- Runtime data shouldn't be in source control
- Docker-compose already defines volumes for these
- Currently empty (4K each = just directory overhead)

**Current Docker Compose Config:**
```yaml
volumes:
  ai_brain_data:
  library_data:
  meds_data:
  reminder_data:
  financial_data:
  habits_data:
```

**Action:** DELETE these directories, rely on Docker volumes

#### F. Nested/Duplicate Subdirectories
**Problems:**
1. `Docs_top/docs/` - docs inside docs
2. `Scripts_top/scripts/` - scripts inside scripts
3. `Diagrams_top/diagrams/` AND `Diagrams_top/mermaid/` - unclear organization

**Action:** Flatten these during restructure

#### G. Duplicate .github/ Directories
**Locations:**
- `.github/` in root (4 workflows, CODEOWNERS)
- `microservice/.github/` in microservice (2 workflows, templates, copilot instructions)

**Problem:** Unclear which is authoritative
**Action:** Consolidate into one .github/ directory

### ℹ️ MINOR ISSUES

#### H. Cache Directories in Git
**Directories:**
- `__pycache__/` in microservice/
- `.pytest_cache/` in root and microservice/

**Problem:** Should be gitignored
**Status:** Likely already ignored, may be from pre-.gitignore commits
**Action:** Verify .gitignore covers these

#### I. Makefile Path Typo
**Location:** Line 16
```makefile
build-frontend:
    cd "microservice/front end /kilo-react-frontend" && npm run build --silent
```
**Problem:** Path is `"front end "` (with space), should be `"frontend"`
**Action:** Fix the typo

#### J. Empty Database File
**File:** `microservice/kilos_memory.db` (0 bytes)
**Problem:** Runtime database shouldn't be in source control
**Action:** Add to .gitignore, delete from repo

---

## 3. PROPOSED CORRECT STRUCTURE

### Option A: Monorepo Structure (RECOMMENDED)
**Best for:** Single team, tight integration, easier development

```
kilo-ai-memory-assistant/
├── .git/                           # Single git repository
├── .github/                        # GitHub Actions, templates, CODEOWNERS
│   ├── workflows/
│   │   ├── ci-backend.yml
│   │   ├── ci-frontend.yml
│   │   ├── e2e-tests.yml
│   │   └── docker-compose.yml
│   ├── ISSUE_TEMPLATE/
│   ├── PULL_REQUEST_TEMPLATE.md
│   └── CODEOWNERS
│
├── services/                       # All microservices
│   ├── ai_brain/
│   │   ├── ai_brain/               # Service code
│   │   ├── tests/
│   │   ├── models/
│   │   ├── utils/
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── README.md
│   ├── gateway/
│   │   ├── main.py
│   │   ├── tests/
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   ├── cam/
│   ├── financial/
│   ├── habits/
│   ├── library_of_truth/
│   ├── meds/
│   ├── ml_engine/
│   ├── reminder/
│   ├── voice/
│   └── usb_transfer/
│
├── frontend/                       # React application
│   ├── src/
│   ├── public/
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── package.json
│   └── README.md
│
├── shared/                         # Shared code across services
│   ├── models/                     # Pydantic models
│   │   ├── __init__.py
│   │   └── base.py
│   └── utils/                      # Shared utilities
│
├── docs/                           # All documentation
│   ├── README.md                   # Docs index
│   ├── api/                        # API documentation
│   ├── deployment/
│   │   ├── airgap-setup.md
│   │   ├── docker-compose.md
│   │   └── production.md
│   ├── guides/
│   │   ├── developer-guide.md
│   │   ├── user-guide.md
│   │   └── tablet-setup.md
│   └── architecture/
│       ├── system-overview.md
│       ├── data-flow.md
│       └── diagrams/               # Mermaid diagrams
│
├── scripts/                        # Utility scripts
│   ├── setup/
│   │   ├── install-dependencies.sh
│   │   └── download-models.sh
│   ├── deployment/
│   │   ├── kiosk-mode.sh
│   │   └── tablet-emulator.sh
│   └── dev/
│       └── quality-checks.sh
│
├── data/                           # Static data assets
│   ├── models/                     # Pre-trained model files
│   ├── fixtures/                   # Test fixtures
│   └── examples/                   # Example data
│
├── infra/                          # Infrastructure as code
│   ├── docker/
│   │   ├── docker-compose.yml
│   │   ├── docker-compose.dev.yml
│   │   └── docker-compose.test.yml
│   └── ssl/
│       ├── generate-certs.sh
│       └── .gitkeep
│
├── tests/                          # Integration tests
│   ├── integration/
│   │   ├── test_full_stack.py
│   │   └── test_api_gateway.py
│   └── e2e/
│       └── playwright/
│
├── .gitignore
├── .gitattributes
├── Makefile
├── pytest.ini
├── README.md                       # Main project README
├── LICENSE
├── CODE_OF_CONDUCT.md
├── CONTRIBUTING.md
└── .env.example                    # Example environment variables
```

### Option B: Multi-Repo Structure
**Best for:** Large teams, independent service deployment

Keep separate repositories:
1. `kilo-ai-gateway` - API gateway
2. `kilo-ai-brain` - AI brain service
3. `kilo-ai-frontend` - React frontend
4. `kilo-ai-services` - All other microservices
5. `kilo-ai-shared` - Shared models/utilities
6. `kilo-ai-infra` - Docker compose, deployment scripts

**Not recommended** because:
- Adds complexity for a single-person/small-team project
- Requires managing multiple repos
- More difficult local development

---

## 4. STEP-BY-STEP REORGANIZATION PLAN

### PHASE 0: Pre-Cleanup Safety

#### Step 0.1: Create Backup
```bash
cd /home/kilo/Desktop
tar -czf Kilo_Ai_microservice_backup_$(date +%Y%m%d_%H%M%S).tar.gz Kilo_Ai_microservice/
```

#### Step 0.2: Commit Current State
```bash
cd /home/kilo/Desktop/Kilo_Ai_microservice
git add -A
git commit -m "chore: snapshot before restructure"

cd microservice
git add -A
git commit -m "chore: snapshot before restructure"
```

#### Step 0.3: Create Restructure Branch
```bash
cd /home/kilo/Desktop/Kilo_Ai_microservice
git checkout -b restructure/clean-structure
```

---

### PHASE 1: Remove Problem Files/Directories

#### Step 1.1: Delete Nested Duplicate Directory
```bash
cd /home/kilo/Desktop/Kilo_Ai_microservice/microservice
rm -rf microservice/
git add -A
git commit -m "chore: remove duplicate nested microservice/ directory"
```

#### Step 1.2: Remove Large Binaries from Git
```bash
cd /home/kilo/Desktop/Kilo_Ai_microservice

# Add to gitignore
echo "" >> .gitignore
echo "# Binaries (download separately)" >> .gitignore
echo "caddy" >> .gitignore
echo "ollama" >> .gitignore

# Remove from git but keep locally
git rm --cached caddy ollama
git add .gitignore
git commit -m "chore: remove large binaries from git tracking"
```

#### Step 1.3: Remove Runtime Data Directories
```bash
cd /home/kilo/Desktop/Kilo_Ai_microservice/microservice

# These are managed by Docker volumes
rm -rf ai_brain_data/ financial_data/ habits_data/ library_of_truth_data/ meds_data/ reminder_data/

git add -A
git commit -m "chore: remove runtime data directories (use Docker volumes)"
```

#### Step 1.4: Remove Cache Directories
```bash
cd /home/kilo/Desktop/Kilo_Ai_microservice

# Add to gitignore if not already there
grep -q "__pycache__" .gitignore || echo "__pycache__/" >> .gitignore
grep -q ".pytest_cache" .gitignore || echo ".pytest_cache/" >> .gitignore

# Remove from git
git rm -rf --cached microservice/__pycache__/ microservice/.pytest_cache/ .pytest_cache/
git add .gitignore
git commit -m "chore: remove cache directories from git"
```

#### Step 1.5: Remove Empty Database File
```bash
cd /home/kilo/Desktop/Kilo_Ai_microservice/microservice

# Add to gitignore
echo "*.db" >> .gitignore

# Remove from git
git rm kilos_memory.db
git add .gitignore
git commit -m "chore: remove runtime database file"
```

---

### PHASE 2: Fix Naming Issues

#### Step 2.1: Rename *_top Directories
```bash
cd /home/kilo/Desktop/Kilo_Ai_microservice/microservice

# Rename directories
git mv Data_top data
git mv Docs_top docs
git mv Diagrams_top diagrams
git mv Scripts_top scripts

git commit -m "refactor: rename *_top directories to standard names"
```

#### Step 2.2: Flatten Nested Subdirectories
```bash
cd /home/kilo/Desktop/Kilo_Ai_microservice/microservice

# Flatten docs/docs/ into docs/
if [ -d "docs/docs" ]; then
  mv docs/docs/* docs/
  rmdir docs/docs
fi

# Flatten scripts/scripts/ into scripts/
if [ -d "scripts/scripts" ]; then
  mv scripts/scripts/* scripts/
  rmdir scripts/scripts
fi

# Flatten diagrams/diagrams/ into diagrams/
if [ -d "diagrams/diagrams" ]; then
  mv diagrams/diagrams/* diagrams/
  rmdir diagrams/diagrams
fi

git add -A
git commit -m "refactor: flatten nested subdirectories"
```

#### Step 2.3: Organize Diagrams
```bash
cd /home/kilo/Desktop/Kilo_Ai_microservice/microservice

# Move all diagrams into diagrams/ root or organized subdirs
# Keep mermaid/ as a subdir for source files
# This structure is actually fine, just verify it's organized

git add -A
git commit -m "refactor: organize diagrams directory" --allow-empty
```

---

### PHASE 3: Consolidate Git Repositories

**DECISION REQUIRED:** Choose Option A (Monorepo) or Option B (Multi-repo)

#### Option A: Convert to Monorepo (RECOMMENDED)

```bash
cd /home/kilo/Desktop/Kilo_Ai_microservice

# Remove nested git repository
rm -rf microservice/.git

# Move all microservice contents to root
# Create services/ directory
mkdir -p services

# Move service directories
mv microservice/ai_brain services/
mv microservice/cam services/
mv microservice/financial services/
mv microservice/gateway services/
mv microservice/habits services/
mv microservice/library_of_truth services/
mv microservice/meds services/
mv microservice/ml_engine services/
mv microservice/reminder services/
mv microservice/voice services/
mv microservice/usb_transfer services/

# Move frontend
mv microservice/frontend ./

# Move shared code
mkdir -p shared
mv microservice/models shared/
mv microservice/integration services/integration

# Move infrastructure
mkdir -p infra/docker
mv microservice/docker-compose.yml infra/docker/
mv microservice/docker-compose.test.yml infra/docker/
mv microservice/alembic.ini infra/

# Move docs, scripts, diagrams, data
mv microservice/docs ./
mv microservice/scripts ./
mv microservice/diagrams ./docs/architecture/
mv microservice/data ./

# Move config files to root
mv microservice/pytest.ini ./
mv microservice/.env.example ./  # Rename .env to .env.example
mv microservice/CODE_OF_CONDUCT.md ./
mv microservice/CONTRIBUTING.md ./
mv microservice/LICENSE ./

# Update main README
# (manual step - combine microservice/README.md content into root README.md)

# Remove now-empty microservice directory
rmdir microservice

git add -A
git commit -m "refactor: restructure to monorepo layout

- Moved services to services/ directory
- Moved frontend to frontend/ directory
- Moved shared code to shared/ directory
- Moved infrastructure to infra/ directory
- Consolidated documentation to docs/
- Flattened directory structure
- Removed nested git repository"
```

#### Option B: Keep Multi-Repo (Alternative)
```bash
# If keeping separate repos:
# 1. Keep microservice as a git submodule
# 2. Create .gitmodules file
# 3. Restructure microservice/ internally
# (Not providing detailed steps as Option A is recommended)
```

---

### PHASE 4: Consolidate GitHub Configurations

#### Step 4.1: Merge .github/ Directories
```bash
cd /home/kilo/Desktop/Kilo_Ai_microservice

# Copy useful items from microservice/.github/ to root .github/
cp microservice/.github/copilot-instructions.md .github/
cp -r microservice/.github/ISSUE_TEMPLATE .github/ 2>/dev/null || true
cp microservice/.github/PULL_REQUEST_TEMPLATE.md .github/ 2>/dev/null || true

# Merge workflows (manually review and combine)
# Keep smoke-test.yml, playwright-e2e.yml, etc.
# Add any unique workflows from microservice/.github/workflows/

# Remove microservice .github after copying
rm -rf microservice/.github

git add -A
git commit -m "chore: consolidate GitHub configurations"
```

---

### PHASE 5: Update Configuration Files

#### Step 5.1: Fix Makefile Typo
```bash
cd /home/kilo/Desktop/Kilo_Ai_microservice

# Edit Makefile line 16
sed -i 's|"microservice/front end /kilo-react-frontend"|"frontend/kilo-react-frontend"|' Makefile

git add Makefile
git commit -m "fix: correct frontend path in Makefile"
```

#### Step 5.2: Update Docker Compose Paths
```bash
cd /home/kilo/Desktop/Kilo_Ai_microservice

# Edit infra/docker/docker-compose.yml
# Update all build paths:
#   ./gateway -> ../../services/gateway
#   ./ai_brain -> ../../services/ai_brain
#   ./frontend/kilo-react-frontend -> ../../frontend
# etc.

# This requires manual editing or a script
# Manual edit recommended to ensure correctness

git add infra/docker/docker-compose.yml
git commit -m "fix: update service paths in docker-compose.yml"
```

#### Step 5.3: Update GitHub Actions Workflows
```bash
cd /home/kilo/Desktop/Kilo_Ai_microservice

# Edit .github/workflows/*.yml
# Update working-directory paths:
#   microservice -> infra/docker
#   microservice/frontend/kilo-react-frontend -> frontend
# etc.

git add .github/workflows/
git commit -m "fix: update paths in GitHub Actions workflows"
```

#### Step 5.4: Update pytest Configuration
```bash
cd /home/kilo/Desktop/Kilo_Ai_microservice

# Edit pytest.ini
# Update testpaths to new structure
cat > pytest.ini << 'EOF'
[pytest]
testpaths = services tests
python_files = test_*.py

markers =
    integration: mark tests that require services/docker-compose
addopts = -m "not integration"
EOF

git add pytest.ini
git commit -m "fix: update pytest paths for new structure"
```

#### Step 5.5: Create .env.example
```bash
cd /home/kilo/Desktop/Kilo_Ai_microservice

# Create example environment file
cat > .env.example << 'EOF'
# Kilo AI Memory Assistant Environment Configuration

# Network Security
ALLOW_NETWORK=false  # Set to true to allow external network access

# Service URLs (Docker internal)
MEDS_URL=http://meds:9001
REMINDER_URL=http://reminder:9002
HABITS_URL=http://habits:9003
AI_BRAIN_URL=http://ai_brain:9004
FINANCIAL_URL=http://financial:9005
LIBRARY_OF_TRUTH_URL=http://library_of_truth:9006
CAM_URL=http://cam:9007
ML_ENGINE_URL=http://ml_engine:9008
VOICE_URL=http://voice:9009
USB_TRANSFER_URL=http://usb_transfer:8006
OLLAMA_URL=http://ollama:11434

# LLM Configuration
OLLAMA_MODEL=llama3.1:8b-instruct-q5_K_M
LLM_PROVIDER=ollama

# Voice Services
STT_PROVIDER=whisper
TTS_PROVIDER=piper

# Security
LIBRARY_ADMIN_KEY=your-secret-key-here

# Ollama Performance (Beelink SER7-9)
OLLAMA_NUM_PARALLEL=2
OLLAMA_MAX_LOADED_MODELS=2
OLLAMA_KEEP_ALIVE=5m
EOF

git add .env.example
git commit -m "docs: add environment configuration example"
```

---

### PHASE 6: Update Documentation

#### Step 6.1: Update Main README
```bash
cd /home/kilo/Desktop/Kilo_Ai_microservice

# Manually update README.md to reflect new structure
# Update paths in quick start:
#   cd microservice -> cd infra/docker
#   cd "frontend/kilo-react-frontend" -> cd frontend
# Update architecture diagrams with new paths

git add README.md
git commit -m "docs: update README for new structure"
```

#### Step 6.2: Create BINARIES.md
```bash
cd /home/kilo/Desktop/Kilo_Ai_microservice

cat > docs/BINARIES.md << 'EOF'
# Required Binaries

The following binaries are required but not included in this repository:

## Caddy Web Server (39M)
- **Purpose:** Reverse proxy for frontend
- **Download:** https://caddyserver.com/download
- **Version:** Latest stable
- **Installation:**
  ```bash
  curl -o caddy https://caddyserver.com/api/download?os=linux&arch=amd64
  chmod +x caddy
  ```

## Ollama LLM Runtime (34M)
- **Purpose:** Local LLM runtime for AI brain
- **Download:** https://ollama.ai/download
- **Version:** Latest stable
- **Installation:**
  ```bash
  curl -o ollama https://ollama.ai/download/ollama-linux-amd64
  chmod +x ollama
  ```

## Placement
Place these binaries in the project root directory or in your system PATH.
EOF

git add docs/BINARIES.md
git commit -m "docs: add binary download instructions"
```

#### Step 6.3: Update All Documentation Links
```bash
# Manually review and update all markdown files in docs/
# Update any references to old paths:
#   microservice/ -> services/
#   *_top/ -> standard names
#   etc.

# This is a manual task - use grep to find references
grep -r "microservice/" docs/ | grep -v ".git"

git add docs/
git commit -m "docs: update documentation for new structure"
```

---

### PHASE 7: Verification & Testing

#### Step 7.1: Verify File Structure
```bash
cd /home/kilo/Desktop/Kilo_Ai_microservice

# Expected structure (after monorepo conversion):
ls -la
# Should show: services/, frontend/, shared/, infra/, docs/, scripts/, data/, diagrams/

ls services/
# Should show: ai_brain, cam, financial, gateway, habits, library_of_truth, meds, ml_engine, reminder

ls infra/docker/
# Should show: docker-compose.yml, docker-compose.test.yml
```

#### Step 7.2: Test Docker Compose Build
```bash
cd /home/kilo/Desktop/Kilo_Ai_microservice/infra/docker

# Test build (don't start yet)
docker-compose build --no-cache

# If successful, try starting services
docker-compose up -d

# Check health
docker-compose ps

# Tear down
docker-compose down
```

#### Step 7.3: Test Frontend Build
```bash
cd /home/kilo/Desktop/Kilo_Ai_microservice/frontend

npm install --legacy-peer-deps
npm run build

# Should complete without errors
```

#### Step 7.4: Run Tests
```bash
cd /home/kilo/Desktop/Kilo_Ai_microservice

# Backend tests
pytest

# Frontend tests
cd frontend
npm test -- --watchAll=false
```

#### Step 7.5: Verify Git Status
```bash
cd /home/kilo/Desktop/Kilo_Ai_microservice

git status
# Should show clean working tree

git log --oneline -10
# Review recent commits
```

---

### PHASE 8: Finalize and Prepare for GitHub

#### Step 8.1: Create Comprehensive .gitignore
```bash
cd /home/kilo/Desktop/Kilo_Ai_microservice

cat > .gitignore << 'EOF'
# Operating System
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
.venv/
ENV/
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# Testing
.pytest_cache/
.coverage
.coverage.*
htmlcov/
.tox/
.nox/
coverage.xml
*.cover
.hypothesis/

# Node / Frontend
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*
.pnpm-debug.log*
package-lock.json
yarn.lock
/frontend/build

# IDEs
.vscode/
.idea/
*.swp
*.swo
*~
.sublime-project
.sublime-workspace
*.sublime-*

# Environment
.env
.env.local
.env.*.local
*.local

# Databases
*.db
*.sqlite
*.sqlite3

# Logs
*.log
logs/

# Docker
docker-compose.override.yml

# Binaries (download separately)
caddy
ollama

# Runtime data (use Docker volumes)
*_data/
data/runtime/

# Temporary files
tmp/
temp/
.cache/

# macOS
.AppleDouble
.LSOverride
Icon

# Linux
*~
.directory
.Trash-*

# SSL Certificates (regenerate for your deployment)
*.pem
*.key
*.crt
!.gitkeep

# Model files (too large, download separately)
*.weights
*.h5
*.pb
*.onnx
*.pt
*.pth
EOF

git add .gitignore
git commit -m "chore: comprehensive .gitignore for production repo"
```

#### Step 8.2: Update Git Attributes for LFS
```bash
cd /home/kilo/Desktop/Kilo_Ai_microservice

cat > .gitattributes << 'EOF'
# Git LFS tracking for large files

# Binary files
*.pdf filter=lfs diff=lfs merge=lfs -text
*.zip filter=lfs diff=lfs merge=lfs -text
*.tar.gz filter=lfs diff=lfs merge=lfs -text

# Model files
*.weights filter=lfs diff=lfs merge=lfs -text
*.h5 filter=lfs diff=lfs merge=lfs -text
*.pb filter=lfs diff=lfs merge=lfs -text
*.onnx filter=lfs diff=lfs merge=lfs -text
*.pt filter=lfs diff=lfs merge=lfs -text
*.pth filter=lfs diff=lfs merge=lfs -text

# Media files
*.mp4 filter=lfs diff=lfs merge=lfs -text
*.mov filter=lfs diff=lfs merge=lfs -text
*.avi filter=lfs diff=lfs merge=lfs -text

# Ensure scripts are executable
*.sh text eol=lf
EOF

git add .gitattributes
git commit -m "chore: configure Git LFS for large files"
```

#### Step 8.3: Create Release Checklist
```bash
cd /home/kilo/Desktop/Kilo_Ai_microservice

cat > RELEASE_CHECKLIST.md << 'EOF'
# Pre-Release Checklist

Before pushing to GitHub:

## Code Quality
- [ ] All tests pass (backend and frontend)
- [ ] Docker Compose builds successfully
- [ ] No sensitive data in repository (API keys, passwords, etc.)
- [ ] .env.example contains all required variables
- [ ] No large binaries committed (caddy, ollama)

## Documentation
- [ ] README.md is up to date
- [ ] Installation instructions are clear
- [ ] Architecture diagrams reflect new structure
- [ ] API documentation is complete
- [ ] BINARIES.md explains how to obtain required binaries

## Repository Hygiene
- [ ] .gitignore is comprehensive
- [ ] Git LFS is configured for large files
- [ ] No __pycache__ or .pytest_cache directories
- [ ] No node_modules in git
- [ ] All paths in configs are updated

## GitHub Settings
- [ ] Repository name chosen
- [ ] License file present
- [ ] CODE_OF_CONDUCT.md included
- [ ] CONTRIBUTING.md has clear guidelines
- [ ] Issue templates configured
- [ ] PR template configured

## CI/CD
- [ ] GitHub Actions workflows validated
- [ ] All workflow paths updated for new structure
- [ ] Secrets documented (LIBRARY_ADMIN_KEY, etc.)

## Final Checks
- [ ] Branch is clean (`git status` shows no uncommitted changes)
- [ ] All commits have clear messages
- [ ] Version tag ready (v1.0.0)
EOF

git add RELEASE_CHECKLIST.md
git commit -m "docs: add pre-release checklist"
```

#### Step 8.4: Merge to Main Branch
```bash
cd /home/kilo/Desktop/Kilo_Ai_microservice

# Switch to main/master
git checkout master  # or main

# Merge restructure branch
git merge restructure/clean-structure

# Tag the release
git tag -a v1.0.0 -m "v1.0.0: Clean restructure for public release

- Monorepo structure with services/ directory
- Removed nested git repository
- Fixed naming conventions (*_top -> standard names)
- Removed large binaries from git
- Comprehensive documentation
- Production-ready configuration"

git log --oneline --graph -10
```

---

## 5. POST-RESTRUCTURE TASKS

### Create New GitHub Repository
```bash
# On GitHub.com:
# 1. Create new repository: kilo-ai-memory-assistant
# 2. Do NOT initialize with README (we have one)
# 3. Set visibility (public/private)

# Locally:
cd /home/kilo/Desktop/Kilo_Ai_microservice

git remote add origin https://github.com/YOUR_USERNAME/kilo-ai-memory-assistant.git
git push -u origin master
git push origin v1.0.0
```

### Enable Git LFS
```bash
cd /home/kilo/Desktop/Kilo_Ai_microservice

# Install Git LFS
git lfs install

# Track large files already configured in .gitattributes
git lfs track

# Push LFS objects
git lfs push origin master
```

### Configure GitHub Settings
- Enable GitHub Actions
- Add branch protection rules for master
- Configure required status checks
- Add repository description and topics
- Set up GitHub Pages for documentation (optional)

### Update Repository Links
- Update links in README.md
- Update package.json repository field
- Update documentation references

---

## 6. ROLLBACK PLAN

If something goes wrong during restructure:

```bash
# Restore from backup
cd /home/kilo/Desktop
tar -xzf Kilo_Ai_microservice_backup_YYYYMMDD_HHMMSS.tar.gz

# Or revert git commits
cd /home/kilo/Desktop/Kilo_Ai_microservice
git checkout master
git branch -D restructure/clean-structure
git reset --hard <commit-before-restructure>
```

---

## 7. ESTIMATED TIME

- **Phase 0:** 15 minutes (backup, commit, branch)
- **Phase 1:** 20 minutes (remove problems)
- **Phase 2:** 15 minutes (fix naming)
- **Phase 3:** 45 minutes (restructure to monorepo)
- **Phase 4:** 15 minutes (consolidate GitHub configs)
- **Phase 5:** 30 minutes (update configs)
- **Phase 6:** 30 minutes (update docs)
- **Phase 7:** 30 minutes (verification & testing)
- **Phase 8:** 20 minutes (finalize)

**Total: ~3.5 hours**

---

## 8. QUESTIONS TO ANSWER BEFORE STARTING

1. **Repository Structure:** Monorepo (Option A) or Multi-repo (Option B)?
   - **Recommendation:** Monorepo (Option A)

2. **Keep History:** Rewrite git history to remove large files permanently?
   - **If yes:** Use `git filter-repo` after restructure
   - **If no:** Just remove files going forward

3. **Binary Distribution:** How to distribute caddy and ollama?
   - **Options:**
     - Document download URLs (recommended)
     - Use package managers (apt, brew)
     - Include in GitHub Releases as assets

4. **Branch Name:** Keep as `master` or rename to `main`?
   - **Recommendation:** Use `main` for new repo

5. **Version:** Start at v1.0.0 or v0.1.0?
   - **Recommendation:** v1.0.0 (project is feature-complete)

---

**END OF RESTRUCTURE PLAN**
