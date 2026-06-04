import os
import glob

count = 0
for f in glob.glob('**/*.py', recursive=True):
    try:
        with open(f, 'r', encoding='utf-8') as file:
            content = file.read()
        
        new_content = content.replace('sys.path.insert(0, str(Path(__file__).resolve().parent.parent))', 'sys.path.insert(0, str(Path(__file__).resolve().parent.parent))')
        new_content = new_content.replace('sys.path.insert(0, str(Path(__file__).resolve().parent))', 'sys.path.insert(0, str(Path(__file__).resolve().parent))')
        new_content = new_content.replace('sys.path.insert(0, "d:/NEXUS")', 'sys.path.insert(0, "d:/NEXUS")')
        new_content = new_content.replace('sys.path.append(\'d:/NEXUS\')', 'sys.path.insert(0, \'d:/NEXUS\')')
        new_content = new_content.replace('sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))', 'sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))')
        new_content = new_content.replace('sys.path.insert(0, os.getcwd())', 'sys.path.insert(0, os.getcwd())')
        
        if content != new_content:
            with open(f, 'w', encoding='utf-8') as file:
                file.write(new_content)
            count += 1
            print(f"Fixed {f}")
    except Exception as e:
        print(f"Error processing {f}: {e}")

print(f"Total files fixed: {count}")
