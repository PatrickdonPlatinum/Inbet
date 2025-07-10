def clean_line(line):
    # Split by spaces and process parts with colons
    parts = line.split()
    for part in parts:
        colon_count = part.count(':')
        if colon_count == 0:
            continue
        subparts = part.split(':')
        if colon_count == 1 and len(subparts) == 2 and subparts[0] and subparts[1]:
            return f"{subparts[0]}:{subparts[1]}"
        elif colon_count > 1:
            last_part = subparts[-1]
            is_url = 'http' in last_part or 'www' in last_part
            if is_url and len(subparts) >= 3:
                return f"{subparts[0]}:{subparts[1]}"
            else:
                before_last = subparts[-2]
                if ' ' in before_last:
                    before_last = before_last.split()[-1]
                return f"{before_last}:{subparts[-1]}"
    # If no valid part found, process the whole line
    parts = line.split(':')
    num_colons = len(parts) - 1
    if num_colons == 0:
        return None
    elif num_colons == 1:
        if len(parts) == 2 and parts[0] and parts[1]:
            return f"{parts[0].strip()}:{parts[1].strip()}"
    else:
        last_part = parts[-1].strip()
        is_url = 'http' in last_part or 'www' in last_part
        if is_url and len(parts) >= 3:
            return f"{parts[0].strip()}:{parts[1].strip()}"
        else:
            before_last = parts[-2].strip()
            if ' ' in before_last:
                before_last = before_last.split()[-1]
            return f"{before_last}:{parts[-1].strip()}"

def process_file(input_file, output_file):
    try:
        # Open the input file with UTF-8 encoding
        with open(input_file, 'r', encoding='utf-8') as infile, open(output_file, 'w', encoding='utf-8') as outfile:
            for line in infile:
                # Assuming clean_line() is a function you defined
                cleaned_line = clean_line(line)
                if cleaned_line:  # Only write non-empty lines
                    outfile.write(cleaned_line + '\n')
        print(f"File has been processed. Output saved to {output_file}")
    except FileNotFoundError:
        print(f"Error: Input file '{input_file}' not found")
    except UnicodeDecodeError as e:
        print(f"Encoding error: {str(e)}")
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        
# Example usage
input_filename = "input.txt"
output_filename = "output.txt"
process_file(input_filename, output_filename)