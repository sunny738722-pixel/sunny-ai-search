import streamlit as st
from groq import Groq
from tavily import TavilyClient
import uuid

# 1. PAGE CONFIGURATION
st.set_page_config(page_title="Sunny's AI", page_icon="🤖", layout="wide")

# 2. SESSION STATE (Memory)
if "all_chats" not in st.session_state:
    st.session_state.all_chats = {} 
if "active_chat_id" not in st.session_state:
    new_id = str(uuid.uuid4())
    st.session_state.all_chats[new_id] = {"title": "New Chat", "messages": []}
    st.session_state.active_chat_id = new_id

# 3. SIDEBAR (Navigation)
with st.sidebar:
    st.title("💬 Your Chats")
    
    # New Chat Button
    if st.button("➕ New Chat", use_container_width=True, type="primary"):
        new_id = str(uuid.uuid4())
        st.session_state.all_chats[new_id] = {"title": "New Chat", "messages": []}
        st.session_state.active_chat_id = new_id
        st.rerun()

    st.divider()
    
    # List all chats
    # We use reversed() so the newest chat is at the top
    for chat_id in reversed(list(st.session_state.all_chats.keys())):
        chat = st.session_state.all_chats[chat_id]
        
        col1, col2 = st.columns([0.85, 0.15]) 
        
        with col1:
            # Highlight active chat
            is_active = (chat_id == st.session_state.active_chat_id)
            if st.button(f"📝 {chat['title']}", key=f"btn_{chat_id}", use_container_width=True, type="primary" if is_active else "secondary"):
                st.session_state.active_chat_id = chat_id
                st.rerun()
                
        with col2:
            # Delete button
            if st.button("❌", key=f"del_{chat_id}"):
                del st.session_state.all_chats[chat_id]
                # If deleted active chat, create new one
                if chat_id == st.session_state.active_chat_id:
                    new_id = str(uuid.uuid4())
                    st.session_state.all_chats[new_id] = {"title": "New Chat", "messages": []}
                    st.session_state.active_chat_id = new_id
                st.rerun()

    st.divider()
    
    st.header("⚙️ Settings")
    selected_model = st.selectbox(
        "AI Model:",
        options=["llama-3.1-8b-instant", "llama-3.3-70b-versatile"],
        index=0
    )

# 4. API KEYS
try:
    groq_client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    tavily_client = TavilyClient(api_key=st.secrets["TAVILY_API_KEY"])
except Exception:
    st.error("🚨 API Keys missing! Check Streamlit Settings.")
    st.stop()

# 5. LOGIC FUNCTIONS
def search_web(query):
    # --- THIS WAS THE FIX ---
    # We must return TWO things: (context_text, results)
    try:
        response = tavily_client.search(query, max_results=3)
        results = response.get("results", [])
        
        # Create the text blob for the AI to read
        context_text = ""
        for i, result in enumerate(results):
            context_text += f"SOURCE {i+1}: {result['title']} | URL: {result['url']} | CONTENT: {result['content']}\n\n"
            
        return context_text, results # <--- Returning 2 items now!
    except:
        return "", []

def stream_ai_answer(messages, search_context, model_name):
    system_prompt = {
        "role": "system",
        "content": (
            "You are a helpful assistant. Answer based on the SEARCH RESULTS provided."
            f"\n\nSEARCH RESULTS:\n{search_context}"
        )
    }
    clean_history = [{"role": m["role"], "content": m["content"]} for m in messages]
    
    try:
        stream = groq_client.chat.completions.create(
            model=model_name,
            messages=[system_prompt] + clean_history,
            temperature=0.7,
            stream=True,
        )
        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    except Exception as e:
        yield f"❌ Error: {e}"

# 6. MAIN CHAT UI
# Safety check: Ensure active_chat_id exists (in case of weird delete errors)
if st.session_state.active_chat_id not in st.session_state.all_chats:
    new_id = str(uuid.uuid4())
    st.session_state.all_chats[new_id] = {"title": "New Chat", "messages": []}
    st.session_state.active_chat_id = new_id

active_id = st.session_state.active_chat_id
active_chat = st.session_state.all_chats[active_id]

st.title(f"🤖 {active_chat['title']}")

# Display History
for message in active_chat["messages"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "sources" in message and message["sources"]:
            with st.expander("📚 Sources"):
                for source in message["sources"]:
                    st.markdown(f"- [{source['title']}]({source['url']})")

# Input Handling
if prompt := st.chat_input("Ask me anything..."):
    
    # 1. Show User Message
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.all_chats[active_id]["messages"].append({"role": "user", "content": prompt})
    
    # 2. Rename Chat (Silently)
    if len(active_chat["messages"]) == 1:
        new_title = " ".join(prompt.split()[:4]) + "..."
        st.session_state.all_chats[active_id]["title"] = new_title
    
    # 3. Generate Answer
    with st.chat_message("assistant"):
        with st.spinner("🔎 Searching..."):
            # Now this line works because search_web returns 2 items!
            search_context, sources = search_web(prompt)
        
        full_response = st.write_stream(
            stream_ai_answer(st.session_state.all_chats[active_id]["messages"], search_context, selected_model)
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
