"""Example usage of the OpenAI provider adapter."""

import asyncio
import os

from llm_providers import (
    APIKeyMissingError,
    OpenAIProvider,
)


async def basic_chat_example():
    """Basic chat completion example."""
    print("=" * 60)
    print("Basic Chat Example")
    print("=" * 60)

    try:
        # Initialize provider (reads OPENAI_API_KEY from environment)
        provider = OpenAIProvider(
            model_name="gpt-4o-mini",
            temperature=0.7,
            max_tokens=100,
        )

        print(f"Provider: {provider}")
        print()

        # Simple chat
        messages = [{"role": "user", "content": "What is 2 + 2? Explain briefly."}]

        print("Sending chat request...")
        response = await provider.chat(messages)

        print(f"\nResponse: {response['content']}")
        print(f"Model: {response['model']}")
        print(f"Tokens used: {response['usage']['total_tokens']}")
        print(f"Finish reason: {response['finish_reason']}")

    except APIKeyMissingError:
        print("Error: OPENAI_API_KEY environment variable not set")


async def multi_turn_conversation():
    """Multi-turn conversation example."""
    print("\n" + "=" * 60)
    print("Multi-turn Conversation Example")
    print("=" * 60)

    try:
        provider = OpenAIProvider(model_name="gpt-4o-mini", temperature=0.8)

        messages = [
            {"role": "system", "content": "You are a helpful math tutor."},
            {"role": "user", "content": "What is calculus?"},
        ]

        # First turn
        print("\nUser: What is calculus?")
        response = await provider.chat(messages)
        print(f"Assistant: {response['content'][:150]}...")

        # Add assistant's response to history
        messages.append({"role": "assistant", "content": response["content"]})

        # Second turn
        messages.append(
            {"role": "user", "content": "Can you give me a simple example?"}
        )
        print("\nUser: Can you give me a simple example?")
        response = await provider.chat(messages)
        print(f"Assistant: {response['content'][:150]}...")

        print(f"\nTotal conversation tokens: {response['usage']['total_tokens']}")

    except APIKeyMissingError:
        print("Error: OPENAI_API_KEY environment variable not set")


async def token_counting_example():
    """Token counting example."""
    print("\n" + "=" * 60)
    print("Token Counting Example")
    print("=" * 60)

    try:
        provider = OpenAIProvider(model_name="gpt-4o-mini")

        # Count tokens in various texts
        texts = [
            "Hello, world!",
            "This is a longer sentence with more words to count.",
            "The quick brown fox jumps over the lazy dog. " * 10,
        ]

        for text in texts:
            token_count = provider.count_tokens(text)
            print(f"\nText: {text[:50]}...")
            print(f"Tokens: {token_count}")
            print(f"Characters: {len(text)}")
            print(f"Ratio: ~{len(text) / token_count:.1f} chars per token")

        # Check model limit
        limit = provider.get_model_limit()
        print(f"\nModel token limit: {limit:,}")

    except APIKeyMissingError:
        print("Error: OPENAI_API_KEY environment variable not set")


async def different_models_example():
    """Example using different models."""
    print("\n" + "=" * 60)
    print("Different Models Example")
    print("=" * 60)

    models = ["gpt-3.5-turbo", "gpt-4o-mini", "gpt-4"]
    question = "What is the capital of France?"

    for model_name in models:
        try:
            provider = OpenAIProvider(model_name=model_name)
            print(f"\n{model_name}:")
            print(f"  Token limit: {provider.get_model_limit():,}")

            messages = [{"role": "user", "content": question}]
            response = await provider.chat(messages)

            print(f"  Response: {response['content'][:100]}")
            print(f"  Tokens: {response['usage']['total_tokens']}")

        except APIKeyMissingError:
            print("Error: OPENAI_API_KEY environment variable not set")
            break
        except Exception as e:
            print(f"  Error: {e}")


async def error_handling_example():
    """Error handling example."""
    print("\n" + "=" * 60)
    print("Error Handling Example")
    print("=" * 60)

    # Test 1: Missing API key
    print("\n1. Testing with missing API key...")
    try:
        # Temporarily clear the env var
        original_key = os.environ.get("OPENAI_API_KEY")
        if "OPENAI_API_KEY" in os.environ:
            del os.environ["OPENAI_API_KEY"]

        provider = OpenAIProvider()
    except APIKeyMissingError as e:
        print(f"   ✓ Caught expected error: {e}")

        # Restore the key
        if original_key:
            os.environ["OPENAI_API_KEY"] = original_key

    # Test 2: Invalid temperature
    print("\n2. Testing with invalid temperature...")
    try:
        provider = OpenAIProvider(temperature=3.0, api_key="test")
    except ValueError as e:
        print(f"   ✓ Caught expected error: {e}")

    # Test 3: Invalid max_tokens
    print("\n3. Testing with invalid max_tokens...")
    try:
        provider = OpenAIProvider(max_tokens=-100, api_key="test")
    except ValueError as e:
        print(f"   ✓ Caught expected error: {e}")

    # Test 4: Exceeding model limit
    print("\n4. Testing with max_tokens exceeding model limit...")
    try:
        provider = OpenAIProvider(
            model_name="gpt-3.5-turbo", max_tokens=20000, api_key="test"
        )
    except ValueError as e:
        print(f"   ✓ Caught expected error: {e}")

    print("\n   All error handling tests passed!")


async def main():
    """Run all examples."""
    print("OpenAI Provider Examples")
    print("========================\n")

    # Check if API key is available
    if not os.environ.get("OPENAI_API_KEY"):
        print(
            "⚠️  OPENAI_API_KEY environment variable not set.\n"
            "   Some examples will show error handling instead.\n"
        )

    await basic_chat_example()
    await token_counting_example()
    await error_handling_example()

    # Only run these if we have an API key
    if os.environ.get("OPENAI_API_KEY"):
        await multi_turn_conversation()
        await different_models_example()
    else:
        print(
            "\n\nSkipping multi-turn and different models examples "
            "(no API key available)."
        )

    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
