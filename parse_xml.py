import os
import re
import sqlite3
import xml.etree.ElementTree as ET


def clean_xml_text(element):
    """Recursively extracts text from an element while cleaning up sub-tags."""
    text_pieces = []
    if element.text:
        text_pieces.append(element.text)

    for child in element:
        if child.tag == "lb":
            text_pieces.append(" ")
        elif child.tag == "emph":
            if child.text:
                text_pieces.append(f" {child.text} ")
        elif child.tag == "hi" and child.get("rend") == "sup":
            if child.text:
                text_pieces.append(child.text)
        else:
            text_pieces.append(clean_xml_text(child))

        if child.tail:
            text_pieces.append(child.tail)

    return "".join(text_pieces)


def build_database_from_xml():
    print("Initializing Pre-Cleaned XML Database Compiler...")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    xml_path = os.path.join(script_dir, "schmidt_lexicon.xml")
    db_path = os.path.join(script_dir, "lexicon_app.db")

    if not os.path.exists(xml_path):
        print(f"Error: Could not locate XML asset at '{xml_path}'")
        return

    # Read the raw text file first to strip out custom structural entity macros safely
    print("Reading raw file for entity safety filtering...")
    with open(xml_path, "r", encoding="utf-8") as f:
        raw_content = f.read()

    # UNIVERSAL ENTITY SHIELD: Find any &entity; pattern that isn't a standard built-in XML entity
    # (like &amp;, &lt;, &gt;, &quot;, &apos;) and strip the raw markers so it parses safely as plain text.
    print("Sanitizing historical XML entity definitions...")

    def safe_entity_replacer(match):
        entity_name = match.group(1)
        # Keep built-in system items intact
        if entity_name in ["amp", "lt", "gt", "quot", "apos"]:
            return match.group(0)
        # Convert custom ones to raw strings (e.g., &responsibility; becomes responsibility)
        return entity_name

    sanitized_content = re.sub(r"&([^;\s]+);", safe_entity_replacer, raw_content)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS entries")
    cursor.execute(
        """
        CREATE TABLE entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word TEXT,
            definition TEXT
        )
    """
    )

    print("Parsing sanitized XML tree structures...")

    try:
        # Load directly from the cleaned memory string
        root = ET.fromstring(sanitized_content)
    except ET.ParseError as e:
        print(f"\nXML Syntax Error during compile: {e}")
        conn.close()
        return

    print("Extracting clean database entries...")
    compiled_count = 0

    for entry in root.findall(".//entryFree"):
        raw_key = entry.get("key")
        if not raw_key:
            continue

        clean_word = re.sub(r"\d+$", "", raw_key).strip().lower()
        raw_def = clean_xml_text(entry)

        orth_element = entry.find("orth")
        if orth_element is not None and orth_element.text:
            orth_text = orth_element.text.strip()
            if raw_def.startswith(orth_text):
                raw_def = raw_def[len(orth_text) :].strip()

        clean_def = re.sub(r"\s+", " ", raw_def).strip()
        clean_def = re.sub(r"—\s+", "—", clean_def)
        clean_def = re.sub(r"\s+——\s+", " — ", clean_def)

        if clean_word and clean_def:
            cursor.execute(
                "INSERT INTO entries (word, definition) VALUES (?, ?)",
                (clean_word, clean_def),
            )
            compiled_count += 1

    conn.commit()
    print(f"\nSuccess! Perfect structured database compiled at: {db_path}")
    print(f"Total entries securely compiled: {compiled_count}")
    conn.close()


if __name__ == "__main__":
    build_database_from_xml()