# compare_files.py

def load_lines(path):
    # reads all lines stripped of \n
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return [line.rstrip("\n") for line in f]

def main(file1, file2, out_file):
    lines1 = load_lines(file1)
    lines2 = set(load_lines(file2))  # set for fast lookup

    unique_from_file1 = [line for line in lines1 if line not in lines2]

    with open(out_file, "w", encoding="utf-8") as f:
        for line in unique_from_file1:
            f.write(line + "\n")

    print(f"Saved {len(unique_from_file1)} unique lines to {out_file}")

if __name__ == "__main__":
    # change these or pass via sys.argv if you like
    file1 = "output.txt"
    file2 = "uniquecredentials.txt"
    out_file = "222.txt"
    main(file1, file2, out_file)
