#!/usr/bin/env python3
"""Test script for translation service text chunking functionality."""

import sys
import os
import logging
from typing import Dict, Any

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath('.'))

from core.translation.openai_service import get_openai_translator
from utils.config import get_app_config


# Sample long medical text for testing
LONG_MEDICAL_TEXT = """
The patient, a 45-year-old male, presented to the emergency department with acute onset of severe chest pain radiating to the left arm and jaw. 
The pain began approximately 2 hours prior to arrival and was described as crushing and substernal. Associated symptoms included diaphoresis, 
nausea, and shortness of breath. Past medical history is significant for hypertension, hyperlipidemia, and a 20-pack-year smoking history. 
Current medications include lisinopril 10mg daily and atorvastatin 40mg daily. Physical examination revealed a diaphoretic, anxious-appearing male 
in moderate distress. Vital signs showed blood pressure 160/95 mmHg, heart rate 110 bpm, respiratory rate 22 breaths per minute, 
and oxygen saturation 94% on room air. Cardiovascular examination revealed regular rate and rhythm with no murmurs, rubs, or gallops. 
Pulmonary examination showed clear breath sounds bilaterally with mild tachypnea. The remainder of the physical examination was unremarkable. 
Initial diagnostic workup included a 12-lead electrocardiogram which showed ST-elevation in leads II, III, and aVF consistent with an 
inferior wall myocardial infarction. Laboratory studies revealed elevated troponin I levels at 15.2 ng/mL, confirming myocardial injury. 
Complete blood count and basic metabolic panel were within normal limits. Chest X-ray showed no acute cardiopulmonary abnormalities. 
The patient was immediately started on dual antiplatelet therapy with aspirin 325mg and clopidogrel 600mg loading dose, 
along with atorvastatin 80mg and metoprolol 25mg twice daily. Heparin anticoagulation was initiated with a bolus followed by 
continuous infusion. Given the presentation consistent with ST-elevation myocardial infarction, the interventional cardiology team 
was consulted for emergent cardiac catheterization. The patient was taken to the cardiac catheterization laboratory where coronary 
angiography revealed a 100% occlusion of the right coronary artery in the mid-vessel segment. Percutaneous coronary intervention 
was performed with balloon angioplasty followed by placement of a drug-eluting stent, resulting in restoration of TIMI 3 flow. 
Post-procedure, the patient was transferred to the cardiac care unit for monitoring. Serial electrocardiograms showed resolution 
of ST-elevation, and repeat troponin levels demonstrated an appropriate downtrend. The patient's clinical condition improved 
significantly with resolution of chest pain and normalization of vital signs. Echocardiography performed on hospital day 2 
revealed an ejection fraction of 50% with mild hypokinesis of the inferior wall. The patient was continued on optimal medical 
therapy including aspirin, clopidogrel, metoprolol, lisinopril, and high-intensity statin therapy. Patient education was provided 
regarding lifestyle modifications including smoking cessation, dietary changes, and regular exercise. The patient was discharged 
on hospital day 3 in stable condition with follow-up appointments scheduled with cardiology and primary care within one week. 
Discharge medications included aspirin 81mg daily, clopidogrel 75mg daily for 12 months, metoprolol succinate 50mg daily, 
lisinopril 10mg daily, and atorvastatin 80mg daily. The patient was advised to seek immediate medical attention for any 
recurrence of chest pain or associated symptoms and was provided with sublingual nitroglycerin for emergency use.
"""

# Shorter text for comparison
SHORT_MEDICAL_TEXT = """
Patient presents with acute chest pain and elevated troponin levels. 
ECG shows ST-elevation consistent with myocardial infarction. 
Emergency cardiac catheterization and stent placement performed successfully.
"""


def setup_logging():
    """Setup logging for the test."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def test_token_counting():
    """Test the token counting functionality."""
    print("\n=== Testing Token Counting ===")
    
    try:
        translator = get_openai_translator()
        
        # Test with short text
        short_tokens = translator._count_tokens(SHORT_MEDICAL_TEXT)
        print(f"Short text tokens: {short_tokens} (chars: {len(SHORT_MEDICAL_TEXT)})")
        
        # Test with long text
        long_tokens = translator._count_tokens(LONG_MEDICAL_TEXT)
        print(f"Long text tokens: {long_tokens} (chars: {len(LONG_MEDICAL_TEXT)})")
        
        print(f"Model: {translator._model}, Max tokens: {translator._max_tokens}")
        
        return True
        
    except Exception as e:
        print(f"Token counting test failed: {e}")
        return False


def test_text_chunking():
    """Test the text chunking functionality."""
    print("\n=== Testing Text Chunking ===")
    
    try:
        translator = get_openai_translator()
        
        # Test chunking with different token limits
        test_limits = [100, 200, 500]
        
        for limit in test_limits:
            chunks = translator._split_text_into_chunks(LONG_MEDICAL_TEXT, limit)
            print(f"\nToken limit {limit}:")
            print(f"  Number of chunks: {len(chunks)}")
            
            total_chars = 0
            for i, chunk in enumerate(chunks):
                chunk_tokens = translator._count_tokens(chunk)
                total_chars += len(chunk)
                print(f"  Chunk {i+1}: {chunk_tokens} tokens, {len(chunk)} chars")
                
                if chunk_tokens > limit:
                    print(f"    WARNING: Chunk exceeds token limit!")
            
            print(f"  Total characters: {total_chars} (original: {len(LONG_MEDICAL_TEXT)})")
        
        return True
        
    except Exception as e:
        print(f"Text chunking test failed: {e}")
        return False


def test_short_translation():
    """Test translation with short text (single request)."""
    print("\n=== Testing Short Text Translation ===")
    
    try:
        translator = get_openai_translator()
        
        result = translator.translate(
            text=SHORT_MEDICAL_TEXT,
            source_language="English",
            target_language="Spanish"
        )
        
        print(f"Original text ({len(SHORT_MEDICAL_TEXT)} chars):")
        print(f"  {SHORT_MEDICAL_TEXT[:100]}...")
        print(f"\nTranslated text ({len(result['translated_text'])} chars):")
        print(f"  {result['translated_text'][:100]}...")
        print(f"\nMetadata:")
        print(f"  Model: {result['model_used']}")
        print(f"  Source: {result['source_language']}")
        print(f"  Target: {result['target_language']}")
        
        if "chunks_processed" in result:
            print(f"  Chunks processed: {result['chunks_processed']}")
        
        return True
        
    except Exception as e:
        print(f"Short translation test failed: {e}")
        return False


def test_long_translation():
    """Test translation with long text (chunked requests)."""
    print("\n=== Testing Long Text Translation ===")
    
    try:
        translator = get_openai_translator()
        
        # Count tokens to verify chunking will be used
        tokens = translator._count_tokens(LONG_MEDICAL_TEXT)
        print(f"Input text: {tokens} tokens, {len(LONG_MEDICAL_TEXT)} chars")
        
        result = translator.translate(
            text=LONG_MEDICAL_TEXT,
            source_language="English", 
            target_language="Spanish"
        )
        
        print(f"\nTranslation completed:")
        print(f"  Output length: {len(result['translated_text'])} chars")
        print(f"  Model: {result['model_used']}")
        
        if "chunks_processed" in result:
            print(f"  Chunks processed: {result['chunks_processed']}")
            print(f"  Total chunks: {result['total_chunks']}")
        
        # Show first and last part of translation
        translated = result['translated_text']
        print(f"\nFirst 200 chars: {translated[:200]}...")
        print(f"Last 200 chars: ...{translated[-200:]}")
        
        return True
        
    except Exception as e:
        print(f"Long translation test failed: {e}")
        print(f"This might be expected if OpenAI API key is not configured")
        return False


def main():
    """Run all tests."""
    print("Translation Chunking Test Suite")
    print("=" * 50)
    
    # Check configuration
    try:
        config = get_app_config()
        if not config.openai.api_key:
            print("WARNING: OpenAI API key not configured")
            print("Some tests will fail - this is expected for token counting tests")
        else:
            print("OpenAI API key configured ✓")
    except Exception as e:
        print(f"Configuration error: {e}")
        return
    
    setup_logging()
    
    # Run tests
    tests = [
        ("Token Counting", test_token_counting),
        ("Text Chunking", test_text_chunking),
        ("Short Translation", test_short_translation),
        ("Long Translation", test_long_translation),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            success = test_func()
            results[test_name] = success
        except Exception as e:
            print(f"\nTest '{test_name}' crashed: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "=" * 50)
    print("Test Results Summary:")
    for test_name, success in results.items():
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"  {test_name}: {status}")
    
    passed = sum(results.values())
    total = len(results)
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
    else:
        print("⚠️  Some tests failed - check configuration and logs")


if __name__ == "__main__":
    main()