#!/usr/bin/env python3
"""Simple test for translation chunking without API calls."""

import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath('.'))

from core.translation.openai_service import get_openai_translator


# Very long medical text to force chunking
VERY_LONG_TEXT = """
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
""" * 10  # Repeat 10 times to make it very long


def main():
    print("Translation Chunking Demo")
    print("=" * 40)
    
    try:
        translator = get_openai_translator()
        
        # Calculate text stats
        char_count = len(VERY_LONG_TEXT)
        token_count = translator._count_tokens(VERY_LONG_TEXT)
        
        print(f"Input text: {char_count:,} characters, {token_count:,} tokens")
        print(f"Model: {translator._model}")
        print(f"Max tokens per request: {translator._max_tokens:,}")
        
        # Test chunking with a small limit to force chunking
        test_limit = 500  # Small limit to demonstrate chunking
        
        print(f"\nTesting chunking with {test_limit} token limit:")
        chunks = translator._split_text_into_chunks(VERY_LONG_TEXT, test_limit)
        
        print(f"Number of chunks created: {len(chunks)}")
        
        total_chars = 0
        max_tokens = 0
        
        for i, chunk in enumerate(chunks, 1):
            chunk_tokens = translator._count_tokens(chunk)
            chunk_chars = len(chunk)
            total_chars += chunk_chars
            max_tokens = max(max_tokens, chunk_tokens)
            
            print(f"  Chunk {i:2d}: {chunk_tokens:3d} tokens, {chunk_chars:4d} chars")
            
            # Show first 100 chars of each chunk
            preview = chunk[:100].replace('\n', ' ').strip()
            print(f"            Preview: {preview}...")
        
        print(f"\nSummary:")
        print(f"  Total chunks: {len(chunks)}")
        print(f"  Total characters: {total_chars:,} (original: {char_count:,})")
        print(f"  Character preservation: {total_chars/char_count*100:.1f}%")
        print(f"  Largest chunk: {max_tokens} tokens (limit: {test_limit})")
        
        if max_tokens <= test_limit:
            print("  ✓ All chunks within token limit!")
        else:
            print("  ⚠ Some chunks exceed limit (might need word-level splitting)")
        
        # Test would-be chunking decision
        print(f"\nChunking decision for actual translation:")
        prompt_tokens = translator._count_tokens("You are an expert medical translator...")
        available_tokens = translator._max_tokens - prompt_tokens - 1000
        
        if token_count <= available_tokens:
            print(f"  Text would be translated in SINGLE request")
            print(f"  ({token_count:,} tokens available, {available_tokens:,} needed)")
        else:
            print(f"  Text would be CHUNKED for translation")
            print(f"  ({token_count:,} tokens needed, {available_tokens:,} available)")
            estimated_chunks = (token_count // available_tokens) + 1
            print(f"  Estimated chunks needed: {estimated_chunks}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()