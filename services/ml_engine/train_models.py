#!/usr/bin/env python3
"""
Nightly Training Script for Kilo AI ML Engine
Runs overnight to train ML models on collected habit data.
"""

import os
import sys
import datetime
import logging
from pathlib import Path
import httpx

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Service URLs
HABITS_URL = os.getenv("HABITS_URL", "http://habits:9003")
ML_ENGINE_URL = os.getenv("ML_ENGINE_URL", "http://ml_engine:9008")

async def fetch_all_habits():
    """Fetch all habits from the Habits service."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{HABITS_URL}/habits")
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.error(f"Failed to fetch habits: {e}")
        return []

async def train_habit_model(habit_id: int, habit_name: str):
    """Train ML model for a specific habit."""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            logger.info(f"Training model for habit {habit_id}: {habit_name}")
            response = await client.post(
                f"{ML_ENGINE_URL}/train/habit_completion",
                json={"habit_id": habit_id}
            )
            response.raise_for_status()
            result = response.json()
            logger.info(f"✅ Trained habit {habit_id}: {result.get('message', 'Success')}")
            return True
    except Exception as e:
        logger.error(f"❌ Failed to train habit {habit_id}: {e}")
        return False

async def main():
    """Main training loop - runs nightly to train all habit models."""
    logger.info("="*60)
    logger.info("🧠 Kilo AI Nightly Training Session")
    logger.info(f"⏰ Started at: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*60)

    # Fetch all habits
    logger.info("📊 Fetching all habits...")
    habits = await fetch_all_habits()

    if not habits:
        logger.warning("⚠️  No habits found to train. Exiting.")
        return

    logger.info(f"Found {len(habits)} habits to train")

    # Train each habit
    success_count = 0
    failed_count = 0

    for habit in habits:
        habit_id = habit.get("id")
        habit_name = habit.get("name", "Unknown")

        if habit_id is None:
            logger.warning(f"Skipping habit with no ID: {habit_name}")
            continue

        success = await train_habit_model(habit_id, habit_name)
        if success:
            success_count += 1
        else:
            failed_count += 1

    # Summary
    logger.info("="*60)
    logger.info("📈 Training Session Complete")
    logger.info(f"✅ Successfully trained: {success_count} models")
    logger.info(f"❌ Failed to train: {failed_count} models")
    logger.info(f"⏰ Completed at: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*60)

    # Exit with appropriate code
    if failed_count > 0 and success_count == 0:
        sys.exit(1)  # All failed
    else:
        sys.exit(0)  # At least some succeeded

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
