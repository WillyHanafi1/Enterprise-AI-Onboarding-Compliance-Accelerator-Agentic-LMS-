import asyncio
import time
import uuid
from httpx import AsyncClient, ASGITransport
from src.api.server import create_app
from src.api.dependencies import init_graph, shutdown_graph

async def simulate_user(client: AsyncClient, name, role):
    print(f"[{name}] Starting onboarding...")
    
    # 1. Create Session
    resp = await client.post("/api/v1/sessions", json={
        "employee_name": name,
        "employee_role": role
    })
    if resp.status_code != 200:
        print(f"[{name}] FAILED to create session: {resp.text}")
        return False
    
    session_id = resp.json()["session_id"]
    print(f"[{name}] Session created: {session_id}")
    
    # 2. Chat: Learn
    resp = await client.post(f"/api/v1/sessions/{session_id}/chat/sync", json={
        "message": f"Hello, I am {name}. Tell me about the first topic."
    })
    if resp.status_code != 200:
        print(f"[{name}] FAILED chat: {resp.text}")
        return False
    print(f"[{name}] Learn response received.")
    
    # 3. Get Status
    resp = await client.get(f"/api/v1/sessions/{session_id}/status")
    if resp.status_code != 200:
        print(f"[{name}] FAILED status: {resp.text}")
        return False
    print(f"[{name}] Current topic: {resp.json()['current_topic']}")
    
    return True

async def main():
    print("=== STARTING API STRESS TEST ===")
    app = create_app()
    
    # Manually trigger lifespan events
    await init_graph()
    
    # We use ASGITransport to test the app in-process without a real server
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        users = [
            ("Alice", "Software Engineer"),
            ("Bob", "Product Manager"),
            ("Charlie", "HR Specialist"),
            ("David", "Security Analyst"),
            ("Eve", "DevOps Engineer")
        ]
        
        results = []
        # Run sequentially for stability in this test script
        for name, role in users:
            success = await simulate_user(client, name, role)
            results.append(success)
        
        print("\n=== STRESS TEST RESULTS ===")
        print(f"Total Users: {len(users)}")
        print(f"Success: {sum(results)}")
        print(f"Failed: {len(users) - sum(results)}")
        
    await shutdown_graph()

if __name__ == "__main__":
    import sys
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
