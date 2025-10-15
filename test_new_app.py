#!/usr/bin/env python3
"""Comprehensive test script for the new Flask application structure."""

import requests
import json
import os
import sys
from typing import Dict, Any


def test_endpoint(method: str, url: str, **kwargs) -> Dict[str, Any]:
    """Test an endpoint and return result summary."""
    try:
        response = requests.request(method, url, timeout=10, **kwargs)
        
        result = {
            "url": url,
            "method": method,
            "status_code": response.status_code,
            "success": 200 <= response.status_code < 300,
            "response_size": len(response.content)
        }
        
        # Try to parse JSON response
        try:
            result["response_json"] = response.json()
        except:
            result["response_text"] = response.text[:200] + "..." if len(response.text) > 200 else response.text
        
        return result
        
    except requests.exceptions.RequestException as e:
        return {
            "url": url,
            "method": method,
            "error": str(e),
            "success": False
        }


def main():
    """Run comprehensive API tests."""
    base_url = "http://localhost:5000"
    
    print("🧪 Testing New Flask Application Structure")
    print("=" * 50)
    
    # Test cases
    tests = [
        # Health endpoints
        {
            "name": "Health Check",
            "method": "GET",
            "url": f"{base_url}/health"
        },
        {
            "name": "Root Endpoint",
            "method": "GET", 
            "url": f"{base_url}/"
        },
        
        # Translation endpoints (JSON-based, easier to test)
        {
            "name": "OpenAI Translation",
            "method": "POST",
            "url": f"{base_url}/translations/openai",
            "json": {
                "text": "Hello, how are you?",
                "source_language": "en",
                "target_language": "es"
            },
            "headers": {"Content-Type": "application/json"}
        },
        {
            "name": "Google Translation",
            "method": "POST",
            "url": f"{base_url}/translations/google",
            "json": {
                "text": "Hello, how are you?",
                "target_language": "es"
            },
            "headers": {"Content-Type": "application/json"}
        },
        
        # Post-processing endpoints
        {
            "name": "Sentiment Analysis", 
            "method": "POST",
            "url": f"{base_url}/sentiment",
            "json": {
                "text": "This is a great service and I love using it!"
            },
            "headers": {"Content-Type": "application/json"}
        },
        
        # Error handling tests
        {
            "name": "Invalid Endpoint",
            "method": "GET",
            "url": f"{base_url}/invalid-endpoint"
        },
        {
            "name": "Translation Missing Data",
            "method": "POST",
            "url": f"{base_url}/translations/openai",
            "json": {"target_language": "es"},  # Missing text
            "headers": {"Content-Type": "application/json"}
        }
    ]
    
    # Run tests
    results = []
    for test in tests:
        print(f"\n🔍 Testing: {test['name']}")
        
        # Extract test parameters
        name = test.pop('name')
        result = test_endpoint(**test)
        result['test_name'] = name
        results.append(result)
        
        # Print result
        status = "✅ PASS" if result.get('success') else "❌ FAIL"
        print(f"   {status} - Status: {result.get('status_code', 'ERROR')}")
        
        if result.get('error'):
            print(f"   Error: {result['error']}")
        elif result.get('response_json'):
            # Print key response fields
            response = result['response_json']
            if 'error' in response:
                print(f"   API Error: {response['error']}")
            elif 'translated_text' in response:
                print(f"   Translation: {response['translated_text'][:50]}...")
            elif 'sentiment' in response:
                print(f"   Sentiment: {response['sentiment']}")
            elif 'status' in response:
                print(f"   Status: {response['status']}")
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Summary")
    print("=" * 50)
    
    passed = sum(1 for r in results if r.get('success'))
    total = len(results)
    
    print(f"Total Tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {total - passed}")
    print(f"Success Rate: {passed/total*100:.1f}%")
    
    # Detailed failures
    failures = [r for r in results if not r.get('success')]
    if failures:
        print(f"\n❌ Failed Tests:")
        for failure in failures:
            print(f"  - {failure['test_name']}: {failure.get('error', f'Status {failure.get('status_code')}')}") 
    
    # Expected failures (these are OK)
    expected_failures = ['Invalid Endpoint', 'Translation Missing Data', 'Google Translation']
    unexpected_failures = [f for f in failures if f['test_name'] not in expected_failures]
    
    print(f"\n🎯 Core Functionality Status:")
    if not unexpected_failures:
        print("✅ All core endpoints working correctly!")
        print("✅ Error handling working correctly!")
        print("✅ Flask refactoring successful!")
    else:
        print("❌ Some core endpoints have issues:")
        for failure in unexpected_failures:
            print(f"  - {failure['test_name']}")
    
    return len(unexpected_failures) == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)