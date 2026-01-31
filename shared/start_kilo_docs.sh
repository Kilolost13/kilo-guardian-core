#!/bin/bash
# 1. Navigate to your project
cd /home/brain_ai/Desktop/AI_stuff/old_hacksaw_fingers/

# 2. Connection settings
export OPENAI_API_BASE=http://localhost:8080/v1
export OPENAI_API_KEY=not-needed

# 3. Launch Aider with SPECIFIC files
# Use *.py to add all python files and README.md for context
aider --architect README.md *.py