import os
import re
import sqlite3
import streamlit as st

# Configure the browser window layout
st.set_page_config(page_title="Shakespeare Lexicon", layout="wide")

# Custom CSS targeting clean typography and dark/light mode compatibility
st.markdown(
    """
    <style>
    .stApp { max-width: 100vw; }
    
    /* Beautiful, adaptive typography for the headword */
    .word-title { 
        font-size: 2.5rem; 
        font-weight: 700; 
        margin-bottom: 0.5rem; 
        text-transform: capitalize;
    }
    
    /* Global layout adjustments for the reading pane */
    .definition-body {
        font-size: 1.15rem;
        line-height: 1.6;
    }
    
    /* Style for the greyed-out play act/scene/line numbers */
    .citation {
        color: #748094;
        font-size: 0.95rem;
        font-weight: 400;
    }
    
    /* Style for sense block structural numbers pushing to a new line */
    .sense-number {
        font-weight: 700;
        color: #0F172A;
        display: inline-block;
        margin-top: 0.6rem;
    }
    
    /* Style for first sense block to keep alignment clean */
    .sense-number-first {
        font-weight: 700;
        color: #0F172A;
        display: inline-block;
    }
    
    /* Clean divider for merging duplicate structural records */
    .entry-separator {
        margin: 2rem 0;
        border: 0;
        border-top: 2px dashed #CBD5E1;
    }
    
    /* Dynamic color adjustments when Mac OS transitions to Dark Mode */
    @media (prefers-color-scheme: dark) {
        .citation { color: #94A3B8; }
        .sense-number, .sense-number-first { color: #F1F5F9; }
    }
    </style>
""",
    unsafe_allow_html=True,
)


def format_definition(text):
    """Applies clean typographic rules to the raw XML text payload."""
    if not text:
        return ""

    # 1. BOLD & UNDERLINE PLAY TITLES
    play_title_rx = r"\b([A-Z][A-Za-z0-9.]+)\b(?=\s+[I|V|X|L|C|0-9])|\b([A-Z][A-Za-z0-9.]+)\b(?=\s+\d)"

    def play_replacer(match):
        title = match.group(1) if match.group(1) else match.group(2)
        if title in ["Passages", "Metaphorically", "In"]:
            return title
        return f'<strong style="text-decoration: underline;">{title}</strong>'

    text = re.sub(play_title_rx, play_replacer, text)

    # 2. Format numerical play citations (e.g., 'III, 2, 42' or '4, 5')
    citation_rx = r"\b([I|V|X|L|C]+,\s+\d+,\s+\d+|\b[I|V|X|L|C]+,\s+\d+|\b\d+,\s+\d+)"
    text = re.sub(citation_rx, r'<span class="citation">\1</span>', text)

    # 3. Add linebreaks and custom style wrappers for dictionary sense numbers
    text = re.sub(
        r"\b1\)", r'<span class="sense-number-first">1)</span>', text
    )
    text = re.sub(
        r"\b([2-9]\))", r'<br/><span class="sense-number">\1</span>', text
    )

    # 4. Convert raw markdown formatting artifacts to structured HTML components
    text = text.replace(" — ", " &mdash; ")
    text = text.replace(" —— ", " &mdash;&mdash; ")

    return text


@st.cache_resource
def get_db_connection():
    """Establish a persistent, cached connection to the SQLite database."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(script_dir, "lexicon_app.db")
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, check_same_thread=False)
    return conn


conn = get_db_connection()
cursor = conn.cursor()

# --- APPLICATION HEADER ---
st.title("📖 Alexander Schmidt's Shakespeare Lexicon")

# --- DUAL COLUMN DESKTOP LAYOUT ---
col1, col2 = st.columns([1, 2])

with col1:
    search_query = st.text_input(
        "Search Headwords:", placeholder="Type a word..."
    )

    # Check database path visibility
    if search_query.strip():
        cursor.execute(
            "SELECT DISTINCT word FROM entries WHERE word LIKE ? ORDER BY word ASC LIMIT 100",
            (f"{search_query.strip().lower()}%",),
        )
    else:
        # Fallback view: explicitly search for words starting with 'a' to force default visibility
        cursor.execute(
            "SELECT DISTINCT word FROM entries WHERE word LIKE 'a%' ORDER BY word ASC LIMIT 100"
        )

    matching_words = [row[0] for row in cursor.fetchall()]

    if matching_words:
        selected_word = st.radio(
            f"Matching Entries ({len(matching_words)}):",
            matching_words,
            label_visibility="collapsed",
        )
    else:
        st.info("No matching headwords found. Type another word prefix above.")
        selected_word = None

with col2:
    if selected_word:
        cursor.execute(
            "SELECT definition FROM entries WHERE word = ? ORDER BY id ASC",
            (selected_word,),
        )
        definitions = [row[0] for row in cursor.fetchall()]

        st.markdown(
            f'<div class="word-title">{selected_word}</div>',
            unsafe_allow_html=True,
        )

        with st.container(border=True):
            formatted_defs = [format_definition(d) for d in definitions]
            full_display_text = f' <hr class="entry-separator"> '.join(
                formatted_defs
            )

            st.markdown(
                f'<div class="definition-body">{full_display_text}</div>',
                unsafe_allow_html=True,
            )
    else:
        with st.container(border=True):
            st.markdown(
                '<div style="color: #64748B; text-align: center; padding: 2rem;">Select a word from the left list to read its complete definition and play citations.</div>',
                unsafe_allow_html=True,
            )