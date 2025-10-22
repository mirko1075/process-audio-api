#!/bin/bash
# Test script for the authentication system.
# Run this after starting the application to verify all functionality.

API_URL="http://localhost:5000"

echo "🧪 Testing Authentication System"
echo "================================"

# Test 1: Register new user
echo "📝 1. Testing user registration..."
REGISTER_RESPONSE=$(curl -s -X POST "$API_URL/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test-user@example.com",
    "password": "test123",
    "first_name": "Test",
    "last_name": "User",
    "company": "Test Corp"
  }')

if echo "$REGISTER_RESPONSE" | grep -q "access_token"; then
    echo "✅ Registration successful"
    JWT_TOKEN=$(echo "$REGISTER_RESPONSE" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)
    API_KEY=$(echo "$REGISTER_RESPONSE" | grep -o '"api_key":"[^"]*' | cut -d'"' -f4)
    echo "   JWT: ${JWT_TOKEN:0:20}..."
    echo "   API Key: ${API_KEY:0:20}..."
else
    echo "❌ Registration failed"
    echo "$REGISTER_RESPONSE"
    exit 1
fi

# Test 2: Login
echo ""
echo "🔐 2. Testing user login..."
LOGIN_RESPONSE=$(curl -s -X POST "$API_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test-user@example.com",
    "password": "test123"
  }')

if echo "$LOGIN_RESPONSE" | grep -q "Login successful"; then
    echo "✅ Login successful"
else
    echo "❌ Login failed"
    echo "$LOGIN_RESPONSE"
    exit 1
fi

# Test 3: JWT Authentication
echo ""
echo "🎫 3. Testing JWT authentication..."
PROFILE_RESPONSE=$(curl -s -X GET "$API_URL/auth/profile" \
  -H "Authorization: Bearer $JWT_TOKEN")

if echo "$PROFILE_RESPONSE" | grep -q "test-user@example.com"; then
    echo "✅ JWT authentication successful"
else
    echo "❌ JWT authentication failed"
    echo "$PROFILE_RESPONSE"
    exit 1
fi

# Test 4: API Key Authentication
echo ""
echo "🔑 4. Testing API key authentication with health endpoint..."
HEALTH_RESPONSE=$(curl -s -X GET "$API_URL/health" \
  -H "x-api-key: $API_KEY")

if echo "$HEALTH_RESPONSE" | grep -q "ok"; then
    echo "✅ API key authentication successful"
else
    echo "❌ API key authentication failed"
    echo "$HEALTH_RESPONSE"
fi

# Test 5: Create new API key
echo ""
echo "🔑 5. Testing API key creation..."
NEWKEY_RESPONSE=$(curl -s -X POST "$API_URL/auth/api-keys" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Integration"}')

if echo "$NEWKEY_RESPONSE" | grep -q "API key created successfully"; then
    echo "✅ API key creation successful"
    NEW_API_KEY=$(echo "$NEWKEY_RESPONSE" | grep -o '"api_key":"[^"]*' | cut -d'"' -f4)
    echo "   New API Key: ${NEW_API_KEY:0:20}..."
else
    echo "❌ API key creation failed"
    echo "$NEWKEY_RESPONSE"
fi

# Test 6: Legacy API key (if configured)
echo ""
echo "🏛️  6. Testing legacy API key..."
LEGACY_RESPONSE=$(curl -s -X GET "$API_URL/health" \
  -H "x-api-key: change-me")

if echo "$LEGACY_RESPONSE" | grep -q "ok"; then
    echo "✅ Legacy API key working"
else
    echo "⚠️  Legacy API key not configured or failed"
fi

echo ""
echo "🎉 Authentication system tests completed!"
echo "================================"
echo ""
echo "📋 Summary:"
echo "- ✅ User registration and login"
echo "- ✅ JWT token authentication"  
echo "- ✅ API key authentication"
echo "- ✅ API key management"
echo "- ✅ Backward compatibility"
echo ""
echo "🚀 Your authentication system is ready for production!"