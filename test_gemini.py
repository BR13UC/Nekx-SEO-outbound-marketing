#!/usr/bin/env python3
"""
Test script for Gemini AI integration

Usage:
    python test_gemini.py
"""
import os
import sys

#Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gemini_service import GeminiEmailGenerator


def test_email_generation():
    """Test email generation with Gemini"""
    print("\nEMAIL GENERATION TEST\n")
    print("=" * 60)
    
    try:
        generator = GeminiEmailGenerator()
        
        #Test data
        test_data = {
            "company": "Restaurant De Drie Gezusters",
            "website": "https://dedrie.nl",
            "industry": "restaurant",
            "seo_issues": [
                "Missing meta description on homepage",
                "Page load time: 4.2 seconds (slow)",
                "No structured data (schema.org) detected"
            ],
            "messaging_angle": "local visibility",
            "email_format": "short"
        }
        
        print("Test data:")
        for key, value in test_data.items():
            if key == "seo_issues":
                print(f"  {key}:")
                for issue in value:
                    print(f"    - {issue}")
            else:
                print(f"  {key}: {value}")
        
        print("\nGenerating with Gemini...\n")
        
        subject, body = generator.generate_email(**test_data)
        
        print("=" * 60)
        print(f"SUBJECT: {subject}")
        print("=" * 60)
        print("\nBODY:\n")
        print(body)
        print("\n" + "=" * 60)
        
        print(f"\nSUCCESS: Email generated!")
        print(f"   Subject length: {len(subject)} characters")
        print(f"   Body length: {len(body)} characters")
        print(f"   Word count: {len(body.split())} words")
        
    except ValueError as e:
        print(f"ERROR: {e}")
        print("\nConfigure your Google Gemini API key:")
        print("   export GOOGLE_API_KEY='your-key-here'")
    except Exception as e:
        print(f"ERROR during generation: {e}")


if __name__ == "__main__":
    test_email_generation()