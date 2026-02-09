import streamlit as st
from groq import Groq
from tavily import TavilyClient
import uuid

# ------------------------------------------------------------------
# 1. PAGE CONFIGURATION
# ------------------------------------------------------------------
st.set_page_config(page_title="Sunny's Pro AI", page_icon="🧠", layout="wide")

# Custom CSS for a cleaner look
st.markdown("""
<style>
    .stChatInput {position: fixed; bottom: 20px;}
    .stChatMessage {padding: 1rem; border-radius: 10px; margin-bottom: 1rem;}
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------
# 2. SESSION STATE (Memory)
# ------------------------------------------------------------------
if "all_chats" not in st.session_state:
    st.session_state.all_chats = {} 
if "active_chat_id" not in st.session_state:
    new_id = str(uuid.uuid4())
    st.session_state.all_chats[new_id] = {"title": "New Chat", "messages": []}
    st.session_state.active_chat_id = new_id

# ------------------------------------------------------------------
# 3. SIDEBAR (Navigation)
# ------------------------------------------------------------------
with st.sidebar:
    st.title("🧠 Brain Control")
    
    if st.button("➕ New Discussion", use_container_width=True, type="primary"):
        new_id = str(uuid.uuid4())
        st.session_state.all_chats[new_id] = {"title": "New Chat", "messages": []}
        st.session_state.active_chat_id = new_id
        st.rerun()

    st.divider()
    
    # History List
    for chat_id in reversed(list(st.session_state.all_chats.keys())):
        chat = st.session_state.all_chats[chat_id]
        is_active = (chat_id == st.session_state.active_chat_id)
        
        col1, col2 = st.columns([0.85, 0.15]) 
        with col1:
            if st.button(f"📄 {chat['title']}", key=f"btn_{chat_id}", use_container_width=True, type="primary" if is_active else "secondary"):
                st.session_state.active_chat_id = chat_id
                st.rerun()
        with col2:
            if st.button("❌", key=f"del_{chat_id}"):
                del st.session_state.all_chats[chat_id]
                if chat_id == st.session_state.active_chat_id:
                    new_id = str(uuid.uuid4())
                    st.session_state.all_chats[new_id] = {"title": "New Chat", "messages": []}
                    st.session_state.active_chat_id = new_id
                st.rerun()

# ------------------------------------------------------------------
# 4. API KEYS
# ------------------------------------------------------------------
try:
    groq_client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    tavily_client = TavilyClient(api_key=st.secrets["TAVILY_API_KEY"])
except Exception:
    st.error("🚨 API Keys missing! Check Streamlit Settings.")
    st.stop()

# ------------------------------------------------------------------
# 5. SMART LOGIC (The Upgrade)
# ------------------------------------------------------------------

def search_web(query):
    try:
        # UPGRADE 1: Fetch 6 results instead of 3 (More Brain Food)
        response = tavily_client.search(query, max_results=6)
        results = response.get("results", [])
        
        # Create a rich context for the AI
        context_text = ""
        for i, result in enumerate(results):
            context_text += f"SOURCE {i+1}: {result['title']} | URL: {result['url']} | CONTENT: {result['content']}\n\n"
            
        return context_text, results
    except:
        return "", []

def stream_ai_answer(messages, search_context):
    # UPGRADE 2: The "Super Prompt"
    # We tell it exactly HOW to be smart.
    system_prompt = {
        "role": "system",
        "content": (
            "You are an expert research assistant. Your goal is to provide comprehensive, professional, and well-structured answers."
            "\n\nGUIDELINES:"
            "\n1. **Deep Analysis**: Do not just summarize. Explain 'why' and 'how'."
            "\n2. **Structure**: Use **Bold Headers**, bullet points, and clear paragraphs."
            "\n3. **Citations**: Always cite your sources using [1], [2], etc."
            "\n4. **Objectivity**: If sources disagree, present both sides."
            "\n5. **Directness**: Start with a direct answer to the user's question, then expand."
            f"\n\nSEARCH CONTEXT:\n{search_context}"
        )
    }
    
    clean_history = [{"role": m["role"], "content": m["content"]} for m in messages]
    
    try:
        # UPGRADE 3: Hardcoded to the Smartest Model (70b)
        stream = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile", # The PhD Model
            messages=[system_prompt] + clean_history,
            temperature=0.5, # Lower temperature = More factual/smart, less random
            stream=True,
        )
        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    except Exception as e:
        yield f"❌ Error: {e}"

# ------------------------------------------------------------------
# 6. MAIN UI
# ------------------------------------------------------------------
if st.session_state.active_chat_id not in st.session_state.all_chats:
    new_id = str(uuid.uuid4())
    st.session_state.all_chats[new_id] = {"title": "New Chat", "messages": []}
    st.session_state.active_chat_id = new_id

active_id = st.session_state.active_chat_id
active_chat = st.session_state.all_chats[active_id]

st.title(f"{active_chat['title']}")

# Display History
for message in active_chat["messages"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "sources" in message and message["sources"]:
            with st.expander(f"📚 {len(message['sources'])} Sources Cited"):
                for source in message["sources"]:
                    st.markdown(f"- [{source['title']}]({source['url']})")

# Input Handling
if prompt := st.chat_input("Ask a complex question..."):
    
    # 1. Show User Message
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.all_chats[active_id]["messages"].append({"role": "user", "content": prompt})
    
    # 2. Rename Chat (Silently)
    if len(active_chat["messages"]) == 1:
        new_title = " ".join(prompt.split()[:5]) + "..." # Taking 5 words for better titles
        st.session_state.all_chats[active_id]["title"] = new_title
    
    # 3. Generate Answer
    with st.chat_message("assistant"):
        # We show a status container that updates as it works
        with st.status("🧠 researching deeply...", expanded=True) as status:
            st.write("🔎 Searching the web (6 sources)...")
            search_context, sources = search_web(prompt)
            st.write("🤔 Analyzing & Cross-referencing...")
            status.update(label="✅ Research Complete", state="complete", expanded=False)
        
        full_response = st.write_stream(
            stream_ai_answer(st.session_state.all_chats[active_id]["messages"], search_context)
        )
        
        if sources:
            with st.expander("📚 Sources Used"):
                for source in sources:
                    st.markdown(f"- [{source['title']}]({source['url']})")
    
    # 4. Save Answer
    st.session_state.all_chats[active_id]["messages"].append({
        "role": "assistant", 
        "content": full_response,
        "sources": sources
    })
    
    # 5. Refresh Sidebar (Only on first message)
    if len(active_chat["messages"]) == 2:
        st.rerun()
