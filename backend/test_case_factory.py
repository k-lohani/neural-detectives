import asyncio
import os
import sys

from dotenv import load_dotenv
load_dotenv()

from agents.case_factory import build_new_case_workflow

async def main():
    print("Testing Case Generation Workflow - Easy Difficulty")
    try:
        case = await build_new_case_workflow("easy")
        import json
        print(json.dumps(case, indent=2))
        print("Done.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
