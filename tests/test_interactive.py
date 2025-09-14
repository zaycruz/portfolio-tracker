#!/usr/bin/env python3

import subprocess
import time
import sys

def test_interactive_mode():
    """Test the interactive mode functionality"""
    print("🧪 Testing Portfolio Tracker Interactive Mode")
    print("=" * 50)
    
    # Test 1: Check if interactive command exists
    try:
        result = subprocess.run([
            'python', 'portfolio_tracker.py', 'interactive', '--help'
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("✅ Interactive command exists and shows help")
        else:
            print("❌ Interactive command failed")
            print("Error:", result.stderr)
            return False
    except Exception as e:
        print(f"❌ Error testing interactive command: {e}")
        return False
    
    # Test 2: Test that main command shows interactive as available
    try:
        result = subprocess.run([
            'python', 'portfolio_tracker.py', '--help'
        ], capture_output=True, text=True, timeout=10)
        
        if 'interactive' in result.stdout:
            print("✅ Interactive mode listed in main help")
        else:
            print("❌ Interactive mode not found in help")
            return False
    except Exception as e:
        print(f"❌ Error testing main help: {e}")
        return False
    
    print("\n🎉 All interactive mode tests passed!")
    print("\nTo test interactively, run:")
    print("   python portfolio_tracker.py")
    print("   # or")
    print("   python portfolio_tracker.py interactive")
    
    return True

if __name__ == "__main__":
    test_interactive_mode()