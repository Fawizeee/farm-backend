"""
Script to help fix CORS issues by updating .env file
"""
import os
import re

def get_current_origins():
    """Read current CORS origins from .env"""
    env_file = ".env"
    if not os.path.exists(env_file):
        return []
    
    with open(env_file, 'r') as f:
        content = f.read()
        match = re.search(r'CORS_ORIGINS=(.*)', content)
        if match:
            origins_str = match.group(1).strip()
            if origins_str:
                return [o.strip() for o in origins_str.split(",")]
    return []

def add_origin_to_env(origin):
    """Add an origin to CORS_ORIGINS in .env file"""
    env_file = ".env"
    
    # Read current content
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            content = f.read()
    else:
        content = ""
    
    # Get current origins
    current_origins = get_current_origins()
    
    # Add new origin if not already present
    if origin not in current_origins:
        current_origins.append(origin)
    
    # Update or add CORS_ORIGINS line
    if re.search(r'CORS_ORIGINS=', content):
        # Replace existing line
        content = re.sub(
            r'CORS_ORIGINS=.*',
            f'CORS_ORIGINS={",".join(current_origins)}',
            content
        )
    else:
        # Add new line
        if content and not content.endswith('\n'):
            content += '\n'
        content += f'CORS_ORIGINS={",".join(current_origins)}\n'
    
    # Write back
    with open(env_file, 'w') as f:
        f.write(content)
    
    print(f"✅ Added origin: {origin}")
    print(f"Current CORS origins: {', '.join(current_origins)}")

if __name__ == "__main__":
    print("CORS Configuration Helper")
    print("=" * 50)
    
    current = get_current_origins()
    if current:
        print(f"\nCurrent CORS origins:")
        for origin in current:
            print(f"  - {origin}")
    else:
        print("\nNo CORS_ORIGINS found in .env")
    
    print("\nCommon origins to add:")
    print("  1. http://localhost:3000")
    print("  2. http://10.241.122.193:3000")
    print("  3. http://10.241.122.254:3000")
    print("  4. Custom origin")
    
    choice = input("\nEnter choice (1-4) or 'q' to quit: ").strip()
    
    if choice == "1":
        add_origin_to_env("http://localhost:3000")
    elif choice == "2":
        add_origin_to_env("http://10.241.122.193:3000")
    elif choice == "3":
        add_origin_to_env("http://10.241.122.254:3000")
    elif choice == "4":
        origin = input("Enter origin (e.g., http://192.168.1.100:3000): ").strip()
        if origin:
            add_origin_to_env(origin)
    elif choice.lower() == 'q':
        print("Exiting...")
    else:
        print("Invalid choice")


