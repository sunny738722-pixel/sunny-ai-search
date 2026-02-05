import streamlit as st
from groq import Groq
from tavily import TavilyClient

# 1. LOAD KEYS
GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
TAVILY_API_KEY = st.secrets["TAVILY_API_KEY"]

# 2. PAGE SETUP (Standard Mode)
st.set_page_config(page_title="Sunny's AI", page_icon="🤖")

# 3. APP LOGIC
if "messages" not in st.session_state:
    st.session_state.messages = []

try:
    groq_client = Groq(api_key=GROQ_API_KEY)
    tavily_client = TavilyClient(api_key=TAVILY_API_KEY)
except Exception as e:
    st.error(f"❌ Connection Error: {e}")

def search_web(query):
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
    system_prompt = {
        "role": "system",
        "content": (
            "You are a helpful assistant. Answer based on the SEARCH RESULTS provided."
            f"\n\nSEARCH RESULTS:\n{search_context}"
        )
    }
    clean_history = [{"role": m["role"], "content": m["content"]} for m in messages]
    
    stream = groq_client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[system_prompt] + clean_history,
        temperature=0.7,
        stream=True,
    )
    for chunk in stream:
        if chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content

# 4. MAIN INTERFACE
st.title("🤖 Sunny's AI")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "sources" in message:
            with st.expander("📚 Sources"):
                for source in message["sources"]:
                    st.markdown(f"- [{source['title']}]({source['url']})")

# --- THIS IS THE PART THAT WAS LIKELY MISSING ---
if prompt := st.chat_input("Ask me anything..."):
    
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    with st.chat_message("assistant"):
        with st.spinner("🔎 Searching..."):
            search_context, sources = search_web(prompt)
        
        full_response = st.write_stream(stream_ai_answer(st.session_state.messages, search_context))
        
        if sources:
            with st.expander("📚 Sources Used"):
                for source in sources:
                    st.markdown(f"- [{source['title']}]({source['url']})")
    
    st.session_state.messages.append({
        "role": "assistant", 
        "content": full_response,
        "sources": sources
    })
