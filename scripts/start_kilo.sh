#!/bin/bash
# 1. Navigate to your project
cd /home/brain_ai/Desktop/AI_stuff/old_hacksaw_fingers/

# 2. Tell the system to talk to your local Beelink server
export OPENAI_API_BASE=http://localhost:8080/v1
export OPENAI_API_KEY=not-needed

# 3. Launch Aider
# We use --architect mode because it's better for planning big code changes
aider --architect