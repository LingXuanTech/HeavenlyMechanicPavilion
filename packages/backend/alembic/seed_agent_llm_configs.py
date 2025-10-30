"""Seed default agent LLM configurations.

This script creates default LLM configurations for existing agents.
All agents will initially use OpenAI gpt-4 as the default provider.
"""

import asyncio
import sys
from pathlib import Path

# Add the parent directory to the path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.db.models.agent_config import AgentConfig
from app.db.models.agent_llm_config import AgentLLMConfig
from app.config.settings import settings


async def seed_agent_llm_configs():
    """Create default LLM configurations for all existing agents."""
    
    # Create async engine
    engine = create_async_engine(settings.database_url, echo=True)
    
    # Create async session
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        # Get all existing agents
        result = await session.execute(select(AgentConfig))
        agents = result.scalars().all()
        
        print(f"\nFound {len(agents)} agents to configure...")
        
        for agent in agents:
            # Check if agent already has an LLM config
            existing_config = await session.execute(
                select(AgentLLMConfig).where(AgentLLMConfig.agent_id == agent.id)
            )
            if existing_config.scalars().first():
                print(f"  ⏭️  Agent '{agent.name}' already has LLM config, skipping")
                continue
            
            # Create default LLM config
            llm_config = AgentLLMConfig(
                agent_id=agent.id,
                provider="openai",
                model_name="gpt-4",
                temperature=0.7,
                max_tokens=2000,
                enabled=True,
            )
            session.add(llm_config)
            print(f"  ✅ Created default LLM config for agent '{agent.name}'")
        
        # Commit all changes
        await session.commit()
        print(f"\n✨ Seed data created successfully!")
    
    await engine.dispose()


async def main():
    """Main entry point."""
    try:
        await seed_agent_llm_configs()
    except Exception as e:
        print(f"\n❌ Error seeding agent LLM configs: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
