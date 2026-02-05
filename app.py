import streamlit as st
import os

# 1. TEST IF APP IS ALIVE
st.set_page_config(page_title="Sunny's AI", page_icon="🤖")
st.title("🤖 Sunny's AI")

# 2. SAFETY CHECK FOR KEYS
# We wrap this in a try-block so the app doesn't crash if keys are missing
try:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
    TAVILY_API_KEY = st.secrets["TAVILY_API_KEY"]
    st.success("✅ API Keys loaded successfully!") # This will show if keys work
except Exception as e:
    st.error("❌ CRITICAL ERROR: API Keys are missing!")
    st.info(f"Streamlit says: {e}")
    st.stop() # Stop the app here so it doesn't crash later

# 3. LOAD TOOLS
try:
    from groq import Groq
    from tavily import TavilyClient
    
    groq_client = Groq(api_key=GROQ_API_KEY)
    tavily_client = TavilyClient(api_key=TAVILY_API_KEY)
except Exception as e:
    st.error(f"❌ Tool Error: {e}")
    st.stop()

# 4. MEMORY SETUP
if "messages" not in st.session_state:
    st.session_state.messages = []

# 5. FUNCTIONS
def search_web(query):
    try:
        response = tavily_client.search(query, max_results=3)
        results = response.get("results", [])
        context_text = ""
        for i, result in enumerate(results):
            context_text += f"SOURCE {i+1}: {result['title']} | URL: {result['url']} | CONTENT: {result['content']}\n\n"
        return context_text, results
    except Exception as e:
        st.error(f"Search failed: {e}")
        return "", []

def stream_ai_answer(messages, search_context):
    try:
        system_prompt = {
            "role": "system",
            "content": f"You are a helpful assistant. Answer based on:\n{search_context}"
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
    except Exception as e:
        yield f"❌ AI Error: {e}"

# 6. DRAW CHAT HISTORY
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "sources" in message:
            with st.expander("📚 Sources"):
                for source in message["sources"]:
                    st.markdown(f"- [{source['title']}]({source['url']})")

# 7. INPUT BOX (The part that was missing)
if prompt := st.chat_input("Ask me anything..."):
    
    # User message
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Assistant message
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
