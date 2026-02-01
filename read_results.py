with open("final_results.txt", "r", encoding="utf-8", errors="ignore") as f:
    lines = f.readlines()
    for line in lines[:100]:
        print(line.strip())
