"""Script di test per verificare gli endpoint del server."""
import requests
import json
import time

BASE_URL = "http://localhost:5000"

def test_login():
    """Test dell'endpoint di login mobile."""
    print("\n" + "="*50)
    print("TEST 1: Mobile Login")
    print("="*50)

    url = f"{BASE_URL}/mobile-auth/login"
    payload = {
        "username": "test_user",
        "password": "test123"
    }

    try:
        response = requests.post(url, json=payload)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")

        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ Login successful!")
            print(f"Token: {data['auth_token'][:30]}...")
            return data['auth_token']
        else:
            print(f"\n❌ Login failed!")
            return None

    except Exception as e:
        print(f"\n❌ Error: {e}")
        return None


def test_verify_token(token):
    """Test dell'endpoint di verifica token mobile."""
    print("\n" + "="*50)
    print("TEST 2: Verify Mobile Token")
    print("="*50)

    url = f"{BASE_URL}/mobile-auth/verify"
    payload = {
        "auth_token": token
    }

    try:
        response = requests.post(url, json=payload)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")

        if response.status_code == 200:
            print(f"\n✅ Token is valid!")
        else:
            print(f"\n❌ Token verification failed!")

    except Exception as e:
        print(f"\n❌ Error: {e}")


def test_invalid_token():
    """Test con token invalido."""
    print("\n" + "="*50)
    print("TEST 3: Invalid Mobile Token")
    print("="*50)

    url = f"{BASE_URL}/mobile-auth/verify"
    payload = {
        "auth_token": "invalid_token_12345"
    }

    try:
        response = requests.post(url, json=payload)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")

        if response.status_code == 401:
            print(f"\n✅ Invalid token correctly rejected!")
        else:
            print(f"\n❌ Expected 401 status code!")

    except Exception as e:
        print(f"\n❌ Error: {e}")


def test_logout(token):
    """Test dell'endpoint di logout mobile."""
    print("\n" + "="*50)
    print("TEST 4: Mobile Logout")
    print("="*50)

    url = f"{BASE_URL}/mobile-auth/logout"
    payload = {
        "auth_token": token
    }

    try:
        response = requests.post(url, json=payload)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")

        if response.status_code == 200:
            print(f"\n✅ Logout successful!")
        else:
            print(f"\n❌ Logout failed!")

    except Exception as e:
        print(f"\n❌ Error: {e}")


def test_health_check():
    """Test dell'endpoint di health check."""
    print("\n" + "="*50)
    print("TEST 0: Health Check")
    print("="*50)

    url = f"{BASE_URL}/health"

    try:
        response = requests.get(url)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")

        if response.status_code == 200:
            print(f"\n✅ Server is healthy!")
            return True
        else:
            print(f"\n❌ Health check failed!")
            return False

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nAssicurati che il server sia in esecuzione:")
        print("  python app.py")
        return False


def run_all_tests():
    """Esegui tutti i test."""
    print("\n" + "#"*50)
    print("# Meeting Minute Streamer - Backend API Tests")
    print("#"*50)

    # Test health check
    if not test_health_check():
        print("\n\n⚠️  Server non raggiungibile. Avvia il server con:")
        print("     python app.py")
        return

    # Test login
    token = test_login()
    if not token:
        print("\n\n❌ Login test failed. Stopping tests.")
        return

    # Small delay
    time.sleep(0.5)

    # Test verify token
    test_verify_token(token)
    time.sleep(0.5)

    # Test invalid token
    test_invalid_token()
    time.sleep(0.5)

    # Test logout
    test_logout(token)

    print("\n" + "#"*50)
    print("# Tests Completed!")
    print("#"*50)

    print("\n\n📝 Note:")
    print("- WebSocket testing richiede un client Socket.IO")
    print("- Vedi MOBILE_API_GUIDE.md per esempi completi")
    print("- Usa il file test nell'app React Native per testare WebSocket")


if __name__ == "__main__":
    run_all_tests()
