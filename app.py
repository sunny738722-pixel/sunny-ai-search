import streamlit as st
from groq import Groq
from tavily import TavilyClient

# ==============================================================================
# 🔐 PASTE YOUR KEYS HERE
# ==============================================================================
GROQ_API_KEY = "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"      # <--- Paste Groq Key
TAVILY_API_KEY = "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"   # <--- Paste Tavily Key
# ==============================================================================

st.set_page_config(page_title="My Perplexity", page_icon="🧠", layout="wide")

if "messages" not in st.session_state:
    st.session_state.messages = []

try:
    groq_client = Groq(api_key=GROQ_API_KEY)
    tavily_client = TavilyClient(api_key=TAVILY_API_KEY)
except Exception as e:
    st.error(f"❌ Key Error: {e}")

def search_web(query):
    """Searches Tavily and returns results + formatted context"""
    try:
        response = tavily_client.search(query, max_results=3)
        results = response.get("results", [])
        context_text = ""
        for i, result in enumerate(results):
            context_text += f"SOURCE {i+1}: {result['title']} | URL: {result['url']} | CONTENT: {result['content']}\n\n"
        return context_text, results
    except Exception:
        return "", []

def stream_ai_answer(messages, search_context):
    """
    GENERATOR FUNCTION: Yields text chunks instead of returning one big string.
    This is what makes the 'typing' effect work.
    """
    system_prompt = {
        "role": "system",
        "content": (
            "You are a helpful assistant. "
            "Use the provided SEARCH RESULTS to answer the user's last question. "
            f"\n\nSEARCH RESULTS:\n{search_context}"
        )
    }
    
    # Clean history (remove 'sources' key to please Groq)
    clean_history = [{"role": m["role"], "content": m["content"]} for m in messages]
    
    # ⚡ ENABLE STREAMING HERE
    stream = groq_client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[system_prompt] + clean_history,
        temperature=0.7,
        stream=True,  # <--- The Magic Switch
    )
    
    # Yield each word as it arrives
    for chunk in stream:
        if chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content

# --- MAIN UI ---
st.title("🧠 Local Perplexity")

# Draw History
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "sources" in message:
            with st.expander("📚 Sources Used"):
                for source in message["sources"]:
                    st.markdown(f"- [{source['title']}]({source['url']})")

# User Input
if prompt := st.chat_input("Ask a question..."):
    
    # 1. Show User Message
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # 2. AI Processing
    with st.chat_message("assistant"):
        # Search first (show a spinner only for the search part)
        with st.spinner("🔎 Searching..."):
            search_context, sources = search_web(prompt)
        
        # 3. Stream the Answer (The Typing Effect)
        # st.write_stream automatically handles the generator function
        full_response = st.write_stream(stream_ai_answer(st.session_state.messages, search_context))
        
        # 4. Show Sources below the answer
        if sources:
            with st.expander("📚 Sources Used"):
                for source in sources:
                    st.markdown(f"- [{source['title']}]({source['url']})")
    
    # Save to history
    st.session_state.messages.append({
        "role": "assistant", 
        "content": full_response,
        "sources": sources
    })