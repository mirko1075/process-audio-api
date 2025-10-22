"""
Test script to demonstrate the dual authentication system.
Shows both JWT and API key authentication flows.
"""

import requests
import json
import os

# Base URL for the API
BASE_URL = "http://localhost:5000"

def test_user_registration():
    """Test user registration."""
    print("🔐 Testing user registration...")
    
    data = {
        "email": "test@example.com",
        "password": "password123",
        "first_name": "Test",
        "last_name": "User",
        "company": "Test Company",
        "plan": "pro"
    }
    
    response = requests.post(f"{BASE_URL}/auth/register", json=data)
    
    if response.status_code == 201:
        result = response.json()
        print("✅ Registration successful!")
        print(f"   User: {result['user']['email']}")
        print(f"   JWT Token: {result['access_token'][:50]}...")
        print(f"   API Key: {result['api_key'][:20]}...")
        return result['access_token'], result['api_key']
    else:
        print(f"❌ Registration failed: {response.text}")
        return None, None


def test_jwt_authentication(jwt_token):
    """Test JWT authentication on transcription test endpoint."""
    print("\n📱 Testing JWT authentication...")
    
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Content-Type": "application/json"
    }
    
    response = requests.get(f"{BASE_URL}/transcriptions/test-auth", headers=headers)
    
    if response.status_code == 200:
        result = response.json()
        print("✅ JWT authentication successful!")
        print(f"   User: {result['user']['email']}")
        print(f"   Auth method: {result['authentication']['method']}")
        print(f"   Configured providers: {result['providers_configured']}")
        return True
    else:
        print(f"❌ JWT authentication failed: {response.text}")
        return False


def test_api_key_authentication(api_key):
    """Test API key authentication on transcription test endpoint."""
    print("\n🔑 Testing API key authentication...")
    
    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json"
    }
    
    response = requests.get(f"{BASE_URL}/transcriptions/test-auth", headers=headers)
    
    if response.status_code == 200:
        result = response.json()
        print("✅ API key authentication successful!")
        print(f"   User: {result['user']['email']}")
        print(f"   Auth method: {result['authentication']['method']}")
        print(f"   Configured providers: {result['providers_configured']}")
        return True
    else:
        print(f"❌ API key authentication failed: {response.text}")
        return False


def test_provider_configuration(jwt_token):
    """Test configuring a provider (OpenAI) using JWT."""
    print("\n⚙️ Testing provider configuration...")
    
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Content-Type": "application/json"
    }
    
    # First, get available providers
    response = requests.get(f"{BASE_URL}/user-config/providers", headers=headers)
    
    if response.status_code == 200:
        providers = response.json()['providers']
        print(f"✅ Found {len(providers)} available providers")
        
        openai_provider = next((p for p in providers if p['name'] == 'OpenAI'), None)
        if openai_provider:
            print(f"   OpenAI provider ID: {openai_provider['id']}")
            
            # Configure OpenAI with a test API key
            config_data = {
                "provider_id": openai_provider['id'],
                "api_key": "sk-test123456789abcdef",  # Test API key
                "default_model_id": openai_provider['models'][0]['id'] if openai_provider['models'] else None
            }
            
            config_response = requests.post(
                f"{BASE_URL}/user-config/provider-configs",
                json=config_data,
                headers=headers
            )
            
            if config_response.status_code == 201:
                result = config_response.json()
                print("✅ OpenAI provider configured!")
                print(f"   Preview: {result['configuration']['api_key_preview']}")
                return True
            else:
                print(f"❌ Provider configuration failed: {config_response.text}")
                return False
        else:
            print("❌ OpenAI provider not found")
            return False
    else:
        print(f"❌ Failed to get providers: {response.text}")
        return False


def test_transcription_without_config(api_key):
    """Test transcription without provider configuration (should fail)."""
    print("\n🚫 Testing transcription without provider config...")
    
    headers = {
        "x-api-key": api_key
    }
    
    # Try to use Deepgram without configuration
    response = requests.post(
        f"{BASE_URL}/transcriptions/providers/test/deepgram",
        headers=headers
    )
    
    if response.status_code == 400:
        result = response.json()
        if "not configured" in result.get('error', ''):
            print("✅ Correctly blocked transcription without provider config!")
            print(f"   Error: {result['error']}")
            return True
    
    print(f"❌ Expected error but got: {response.status_code} - {response.text}")
    return False


def main():
    """Run all authentication tests."""
    print("🧪 Testing Dual Authentication System")
    print("=" * 50)
    
    # Test registration
    jwt_token, api_key = test_user_registration()
    if not jwt_token or not api_key:
        print("❌ Cannot continue without valid credentials")
        return
    
    # Test JWT authentication
    jwt_success = test_jwt_authentication(jwt_token)
    
    # Test API key authentication
    api_key_success = test_api_key_authentication(api_key)
    
    # Test provider configuration
    config_success = test_provider_configuration(jwt_token)
    
    # Test transcription without config (should fail)
    no_config_success = test_transcription_without_config(api_key)
    
    # Summary
    print("\n📊 Test Summary")
    print("=" * 30)
    print(f"Registration: {'✅' if jwt_token else '❌'}")
    print(f"JWT Authentication: {'✅' if jwt_success else '❌'}")
    print(f"API Key Authentication: {'✅' if api_key_success else '❌'}")
    print(f"Provider Configuration: {'✅' if config_success else '❌'}")
    print(f"SaaS Enforcement: {'✅' if no_config_success else '❌'}")
    
    all_passed = all([jwt_token, jwt_success, api_key_success, config_success, no_config_success])
    print(f"\n🎯 Overall Result: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")


if __name__ == "__main__":
    main()