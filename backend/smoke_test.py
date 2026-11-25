"""Швидкий smoke-тест API (запускати при працюючому сервері)."""

import requests

BASE = "http://127.0.0.1:5000"


def main() -> None:
    print("health:", requests.get(f"{BASE}/health", timeout=10).json())

    ing = requests.get(f"{BASE}/api/ingredients", timeout=10).json()
    print(f"ingredients: {len(ing)} | first: {ing[0]['name']} ({ing[0]['category']})")

    order = requests.post(
        f"{BASE}/api/orders",
        json={
            "telegram_id": 555001,
            "username": "tester",
            "first_name": "Тест",
            "recipe": {
                "name": "Тестова плитка",
                "base": ing[0],
                "fillings": [ing[4]],
                "toppings": [ing[9]],
            },
            "total_price": 105,
        },
        timeout=10,
    ).json()
    print(f"order created: #{order['id']} | {order['totalPrice']} грн | {order['status']}")

    patched = requests.patch(
        f"{BASE}/api/admin/orders/{order['id']}/status",
        json={"status": "preparing"},
        timeout=10,
    ).json()
    print("order patched:", patched)

    stats = requests.get(f"{BASE}/api/admin/stats", timeout=10).json()
    print(f"stats: users={stats['usersCount']} orders={stats['ordersCount']}")

    mine = requests.get(f"{BASE}/api/orders/user/555001", timeout=10).json()
    print(f"user orders: {len(mine)} | status={mine[0]['status']}")

    requests.patch(f"{BASE}/api/admin/ingredients/1", json={"stock": 55}, timeout=10)
    after = requests.get(f"{BASE}/api/admin/ingredients", timeout=10).json()[0]["stock"]
    print(f"ingredient stock updated: {after}")

    for page in ("/app", "/admin", "/"):
        response = requests.get(f"{BASE}{page}", allow_redirects=True, timeout=10)
        print(f"page {page}: {response.status_code} ({len(response.text)} bytes)")


if __name__ == "__main__":
    main()
