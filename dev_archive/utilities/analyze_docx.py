import docx
import json

def analyze_docx(filename):
    doc = docx.Document(filename)
    results = []
    current_section = "General"
    
    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue
            
        # Try to identify sections based on keywords
        keywords = [
            "How to include authors", "Online module materials", "Forum messages",
            "Books", "Chapter in edited book", "Journal articles", "Newspaper articles",
            "Web pages", "Online images"
        ]
        
        found_section = False
        for kw in keywords:
            if kw.lower() in text.lower() and len(text) < 50:
                current_section = kw
                found_section = True
                break
        
        if not found_section:
            results.append({
                "section": current_section,
                "text": text
            })
            
    with open("analysis_data.json", "w") as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    analyze_docx("Perfect_harvard_style_references.docx")
