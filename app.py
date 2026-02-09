import streamlit as st
from groq import Groq
from tavily import TavilyClient

# ------------------------------------------------------------------
# 1. PAGE CONFIGURATION
# ------------------------------------------------------------------
st.set_page_config(
    page_title="Sunny's AI",
    page_icon="🤖",
    layout="centered" # Changed to centered for a cleaner "Chat" look
)

# Custom CSS to make it look cleaner
st.markdown("""
<style>
    .st-emotion-cache-1y4p8pa {padding-top: 2rem;} /* Less whitespace at top */
    .stChatInput {position: fixed; bottom: 30px;} /* Fix input to bottom */
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------
# 2. SIDEBAR
# ------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Settings")
    
    # Model Selector
    selected_model = st.selectbox(
        "AI Model:",
        options=["llama-3.1-8b-instant", "llama-3.3-70b-versatile"],
        index=0,
        format_func=lambda x: "Fast (8b)" if "8b" in x else "Smart (70b)"
    )
    
    st.divider()
    
    # Clear Button
    if st.button("🗑️ Reset Conversation", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    st.divider()
    st.markdown("### ℹ️ About")
    st.caption("A private AI search engine powered by Groq & Tavily.\n\nBuilt by Sunny.")

# ------------------------------------------------------------------
# 3. SETUP & KEYS
# ------------------------------------------------------------------
try:
    groq_client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    tavily_client = TavilyClient(api_key=st.secrets["TAVILY_API_KEY"])
except Exception:
    st.error("🚨 API Keys missing! Check Streamlit Settings.")
    st.stop()

if "messages" not in st.session_state:
    st.session_state.messages = []

# ------------------------------------------------------------------
# 4. LOGIC
# ------------------------------------------------------------------
def search_web(query):
    try:
        response = tavily_client.search(query, max_results=5) # Increased to 5 sources
        return response.get("results", [])
    except:
        return []

def stream_ai_answer(messages, search_results, model_name):
    # Format sources for the AI
    context = "\n".join([
        f"Source {i+1}: {r['title']} ({r['url']})\nSummary: {r['content']}" 
        for i, r in enumerate(search_results)
    ])
    
    system_prompt = {
        "role": "system",
        "content": (
            "You are a helpful research assistant. "
            "Answer the user's question based ONLY on the provided Search Results. "
            "Cite sources using [1], [2], etc. "
            f"\n\nSEARCH RESULTS:\n{context}"
        )
    }
    
    clean_history = [{"role": m["role"], "content": m["content"]} for m in messages]
    
    stream = groq_client.chat.completions.create(
        model=model_name,
        messages=[system_prompt] + clean_history,
        temperature=0.7,
        stream=True,
    )
    for chunk in stream:
        if chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content

# ------------------------------------------------------------------
# 5. UI: DRAW CHAT
# ------------------------------------------------------------------
st.title("🤖 Sunny's AI")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        
        # If this message has source data attached, show it
        if "results" in msg and msg["results"]:
            with st.expander(f"📚 {len(msg['results'])} Sources Cited"):
                for r in msg["results"]:
                    st.markdown(f"**[{r['title']}]({r['url']})**")
                    st.caption(r['content'][:150] + "...")

# ------------------------------------------------------------------
# 6. UI: HANDLE INPUT
# ------------------------------------------------------------------
if prompt := st.chat_input("What do you want to know?"):
    
    # 1. Show User Message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # 2. Process
    with st.chat_message("assistant"):
        
        # A. Search Phase
        status = st.status("🔎 Searching the web...", expanded=True)
        results = search_web(prompt)
        
        if results:
            status.write("✅ Found relevant information")
            status.update(label="📚 Knowledge Gathered", state="complete", expanded=False)
        else:
            status.update(label="❌ No results found", state="error")
            
        # B. Answer Phase
        full_response = st.write_stream(stream_ai_answer(st.session_state.messages, results, selected_model))
        
        # C. Append Sources (Cleanly)
        if results:
            with st.expander(f"📚 Sources ({len(results)})"):
                for r in results:
                    st.markdown(f"- [{r['title']}]({r['url']})")

    # 3. Save to History
    st.session_state.messages.append({
        "role": "assistant", 
        "content": full_response,
        "results": results # Save sources so they persist!
    })
