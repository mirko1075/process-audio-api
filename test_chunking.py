#!/usr/bin/env python3
"""
Test script to demonstrate the Whisper chunking functionality.
This script creates a test scenario to show how chunking would work.
"""

import tempfile
from pathlib import Path
from pydub import AudioSegment
from pydub.generators import Sine
import math

def create_test_audio(duration_minutes=25, sample_rate=44100):
    """Create a test audio file of specified duration."""
    print(f"Creating test audio file ({duration_minutes} minutes)...")
    
    # Generate a sine wave for testing
    duration_ms = duration_minutes * 60 * 1000
    tone = Sine(440).to_audio_segment(duration=duration_ms)  # 440Hz tone
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
        temp_path = Path(temp_file.name)
    
    # Export audio
    tone.export(str(temp_path), format="wav")
    
    file_size = temp_path.stat().st_size
    print(f"✅ Created test file: {temp_path}")
    print(f"   - Duration: {duration_minutes} minutes")
    print(f"   - File size: {file_size:,} bytes ({file_size / (1024*1024):.1f} MB)")
    
    return temp_path

def simulate_chunking(file_path, chunk_duration_minutes=5, max_size_mb=20):
    """Simulate the enhanced chunking process with compression and dynamic sizing."""
    print(f"\n🔧 Simulating enhanced chunking process...")
    
    # Load audio
    audio = AudioSegment.from_file(str(file_path))
    
    # Calculate parameters
    original_duration_ms = len(audio)
    original_file_size = file_path.stat().st_size
    max_size_bytes = max_size_mb * 1024 * 1024
    
    print(f"📊 Analysis:")
    print(f"   - Total duration: {original_duration_ms / (60 * 1000):.1f} minutes")
    print(f"   - Original file size: {original_file_size / (1024*1024):.1f} MB")
    print(f"   - Chunking needed: {'YES' if original_file_size > max_size_bytes else 'NO'}")
    
    if original_file_size <= max_size_bytes:
        print("✅ File is small enough for direct processing")
        return ["Single file transcription"]
    
    # Simulate compression (mono + 16kHz reduces size significantly)
    print(f"\n🎵 Applying compression (mono + 16kHz)...")
    compressed_audio = audio.set_channels(1).set_frame_rate(16000)
    
    # Calculate dynamic chunk duration
    duration_minutes = original_duration_ms / (60 * 1000)
    mb_per_minute = (original_file_size / (1024 * 1024)) / duration_minutes
    
    # Estimate compressed size (typically 75% reduction)
    compression_factor = 0.25
    estimated_mb_per_minute_compressed = mb_per_minute * compression_factor
    
    # Calculate optimal chunk duration
    target_chunk_size_mb = 15  # Target with buffer
    optimal_chunk_duration = target_chunk_size_mb / estimated_mb_per_minute_compressed
    optimal_chunk_duration = max(2, min(8, optimal_chunk_duration))  # Clamp between 2-8 minutes
    
    chunk_length_ms = int(optimal_chunk_duration * 60 * 1000)
    total_chunks = math.ceil(original_duration_ms / chunk_length_ms)
    
    print(f"   - Original: {mb_per_minute:.1f} MB/minute")
    print(f"   - Compressed: {estimated_mb_per_minute_compressed:.1f} MB/minute")
    print(f"   - Optimal chunk duration: {optimal_chunk_duration:.1f} minutes")
    print(f"   - Number of chunks: {total_chunks}")
    
    print(f"\n📁 Chunks that would be created:")
    chunks_info = []
    
    for i in range(total_chunks):
        start_time = i * chunk_length_ms
        end_time = min(start_time + chunk_length_ms, original_duration_ms)
        
        # Create compressed chunk
        chunk = compressed_audio[start_time:end_time]
        
        # Estimate chunk size by creating temporary file
        with tempfile.NamedTemporaryFile(suffix=".wav") as temp_chunk:
            chunk.export(temp_chunk.name, format="wav", parameters=["-ar", "16000", "-ac", "1", "-b:a", "128k"])
            chunk_size = Path(temp_chunk.name).stat().st_size
        
        chunks_info.append({
            'chunk_num': i + 1,
            'start_minutes': start_time / (60 * 1000),
            'end_minutes': end_time / (60 * 1000),
            'size_mb': chunk_size / (1024 * 1024)
        })
        
        status = "✅" if chunk_size < max_size_bytes else "⚠️ (needs further compression)"
        print(f"   Chunk {i+1}: {start_time/(60*1000):.1f}-{end_time/(60*1000):.1f} min "
              f"({chunk_size/(1024*1024):.1f} MB) {status}")
    
    return chunks_info

def main():
    print("🎵 Enhanced Whisper Chunking Test Simulation")
    print("=" * 60)
    
    # Test with a large file that would require chunking
    test_file = create_test_audio(duration_minutes=55)  # Similar to your 54-minute file
    
    try:
        chunks = simulate_chunking(test_file)
        
        print(f"\n✅ Enhanced chunking simulation complete!")
        if len(chunks) == 1:
            print(f"   - File small enough for direct processing")
        else:
            print(f"   - Would process {len(chunks)} optimally-sized chunks")
            print(f"   - Each chunk compressed and under 20MB limit")
            print(f"   - Dynamic chunk sizing based on audio properties")
        print(f"   - Results would be combined into single transcript")
        
        # Simulate the response format
        print(f"\n📤 Expected API Response Format:")
        if len(chunks) == 1:
            print('{"transcript": "Your transcribed text here"}')
        else:
            chunk_duration = chunks[0]['end_minutes'] - chunks[0]['start_minutes'] if chunks else 5
            print(f'{{')
            print(f'  "transcript": "Combined transcript from all {len(chunks)} optimized chunks",')
            print(f'  "chunks_processed": {len(chunks)},')
            print(f'  "total_chunks": {len(chunks)},')
            print(f'  "chunk_duration_minutes": {chunk_duration:.1f}')
            print(f'}}')
        
    finally:
        # Clean up
        if test_file.exists():
            test_file.unlink()
            print(f"\n🧹 Cleaned up test file")

if __name__ == "__main__":
    main()