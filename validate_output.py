import sys
import os
import re

def validate_markdown_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    errors = []
    if not re.search(r'^# ', content, re.MULTILINE):
        errors.append("Missing title")
    if "Summary:" not in content:
        errors.append("Missing summary section")
    return errors

def validate_directory(output_dir):
    failed = False
    for fname in os.listdir(output_dir):
        if fname.endswith('.md'):
            errors = validate_markdown_file(os.path.join(output_dir, fname))
            if errors:
                failed = True
                print(f"{os.path.join(output_dir, fname)}:")
                for err in errors:
                    print(f"  - {err}")
    return failed

def main():
    base_dir = sys.argv[1] if len(sys.argv) > 1 else "../web-languages"
    failed = False
    if os.path.isdir(base_dir):
        # Validate all subdirectories
        for subdir in os.listdir(base_dir):
            full_path = os.path.join(base_dir, subdir)
            if os.path.isdir(full_path):
                if validate_directory(full_path):
                    failed = True
    else:
        print(f"Error: Directory '{base_dir}' does not exist.")
        sys.exit(1)
    if failed:
        sys.exit(1)

if __name__ == "__main__":
    main()