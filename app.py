import streamlit as st
import os
from streamlit_extras.stylable_container import stylable_container
from PIL import Image
from appsupport import FileFunctions
from appsupport import AIFunctions
from appsupport import DeepEval
from langchain_core.messages import AIMessage, HumanMessage
from pathlib import Path
import socket
import streamlit.components.v1 as components
import pybase64



# Variables used Globally
path = 'C:\\aidata\\CRIStine'  

system_def ="""You are a friendly assistant for question-answering tasks. 
Your name is CRIStine.
When you know the answer, please provide as much detail as possible.
If you don't know the answer, just say that you don't know."""


#configure streamlit for the ap
st.set_page_config(page_title="CRIStine", page_icon = "👩‍🔧")

#st.session_state.system_message = system_def - set in sidebar, used for altering system message (system_def) during the session
if "system_message" not in st.session_state:
    st.session_state.system_message = system_def

#st.session_state.starter_message - set in sidebar, the default message for welcoming user
if "starter_message" not in st.session_state:
    st.session_state.starter_message = "Hello, there! How can I help you today?"

#st.session_state.ret_K - set in sidebar, used to tune the K nearest neighbors for document (KB) search
#st.session_state.chunk_size - set in sidebar, used to tune sentance chunk size when creating KB
#st.session_state.chunk_overlap - set in sidebar, used to tune sentance chunk overlap when creating KB
#st.session_state.max_response_length - set in sidebar, governs the message size coming back from our model
if "max_response_length" not in st.session_state:
    st.session_state.max_response_length = 256
#st.session_state.temperature - set in sidebar, sets model creative temperature (0-strict, 1 - freeform)
#st.session_state.avatars['assistant'] - set in sidebar, the emoji to represent the bot in chat dislay
#st.session_state.avatars['user'] - set in sidebar, the emoji to represent user in chat display
if "avatars" not in st.session_state:
    st.session_state.avatars = {'user': None, 'assistant': None}
    

#reset_history = semiphore to reset the chat history
#user_text = stores the users entry into the chatbot
#st.session_state.chat_history - the current chat history
#st.session_state.doc_retriever - the knowledge base of documents
#st.session_state.deepeval - boolean to include deep eval results (or not!)



if 'user_text' not in st.session_state:
    st.session_state.user_text = None






st.title("Interactive CRIS Assistant")


logo_column, what_am_I_column, save_conv  = st.columns([1, 8,1])

with logo_column:
    image = Image.open(os.path.join(path,'CRIStine.png'))
    st.image(image, caption='Logo goes here')
    
with what_am_I_column:
    st.markdown(f"*CRIStine is a chatbot that uses AI to guide and train users on the CRIS application and the Uniform Guidance (2 CFR 200). It uses the chatgpt4-o Large Language Model long with public & private data to answer questions.*")

with save_conv:
    if st.button("🗄️ Save",  key='save_conversation'):
            FileFunctions.save_conv(st.session_state.chat_history)
           

# Sidebar for settings
with st.sidebar:
    st.header("System Settings")

    st.subheader("AI Behavior")
    # AI Settings
    st.session_state.system_message = st.text_area(
        "System Message", value=system_def
    )
    st.session_state.starter_message = st.text_area(
        'First AI Message', value="Hello, there! How can I help you today?"
    )
    #Document Settings
  

    st.session_state.ret_K = st.number_input(
        "Retreival K", min_value=1, max_value=10, step=1,value=2
    )
    
    
    # Model Settings
    st.subheader("Model Parameters")

    st.session_state.max_response_length = st.number_input(
        "Max Response Length", value=1024
    )
    st.session_state.temperature = st.number_input(
        "Model Temperature", min_value=0.0, max_value=1.0, step=0.1,value=0.1
    )
    
    # Deep Eval Setting
    st.session_state.deepeval = st.checkbox("Enable DeepEval Metrics")

    # Avatar Selection
    st.markdown("*Select Avatars:*")
    col1, col2 = st.columns(2)
    with col1:
        st.session_state.avatars['assistant'] = st.selectbox(
            "AI Avatar", options=["👩‍🔧","🤗", "💬", "🤖"], index=0
        )
    with col2:
        st.session_state.avatars['user'] = st.selectbox(
            "User Avatar", options=["👤", "👱‍♂️", "👨🏾", "👩", "👧🏾"], index=0
        )
    # Reset Chat History
    reset_history = st.button("Reset Chat History")

 
##Chat Code Starts Here
# Chat interface eval_pane=st.container(border=True)


chat_interface = st.container(border=True)

eval_interface = st.container(border=True)
with eval_interface:
    eval_container = st.container()

with chat_interface:
    output_container = st.container()
    st.session_state.user_text = st.chat_input(placeholder="Type your question here...")
# Display chat messages
with output_container:
    
    # session state
    if "chat_history" not in st.session_state or reset_history:
        st.session_state.chat_history = [
            AIMessage(content=st.session_state.starter_message),
        ]
    # conversation
    
    for message in st.session_state.chat_history :
        if isinstance(message, AIMessage):
            with st.chat_message("AI", avatar=st.session_state.avatars['assistant']):
                st.markdown(message.content)
        elif isinstance(message, HumanMessage):
            with st.chat_message("Human",avatar=st.session_state.avatars['user']):
                st.markdown(message.content)
    
    # user input
    
    if st.session_state.user_text is not None and st.session_state.user_text != "":
        st.session_state.chat_history.append(HumanMessage(content=st.session_state.user_text))

        with st.chat_message("Human",avatar=st.session_state.avatars['user']):
            st.markdown(st.session_state.user_text)

        with st.spinner("Thinking..."):
            with st.chat_message("AI", avatar=st.session_state.avatars['assistant']):
                #st.session_state.response = AIFunctions.get_response(st.session_state.doc_retriever,st.session_state.user_text, st.session_state.chat_history,model_id[1], st.session_state.system_message,st.session_state.max_response_length)
                st.session_state.response = AIFunctions.get_response2(st.session_state.ret_K,st.session_state.user_text, st.session_state.chat_history, st.session_state.system_message,st.session_state.max_response_length)
                response = st.write_stream(st.session_state.response[0])
                imagelinks = st.session_state.response[1]
                citationlinks = st.session_state.response[2]

                if len(imagelinks) != 0: #non zero indicates images were found
                    st.write(f"The following Image(s) may be helpful: ")
                    for imagelink in imagelinks:
                        st.image(imagelink)
                if len(citationlinks) != 0: #non zero indicates source articles were found
                    st.write(f"The following Article(s) may be helpful: ")
                    citation_count = 0
                    for citationlink in citationlinks:
                        citation_count += 1
                        st.link_button(
                            url=f'./articleviewer/?pdffile={citationlink}',
                            label=f'Article {citation_count}'
                        )
                        
                st.session_state.response = response
                


        st.session_state.chat_history.append(AIMessage(content=response))
        with eval_container:
            # Deep Eval Scoring
            if st.session_state.deepeval:
                #DeepEval.set_key()
                st.subheader("Deep Eval Scoring")
                with st.spinner("Determing Bias..."):
                    eval_results = DeepEval.deep_eval_bias(st.session_state.user_text, st.session_state.response)
                    st.markdown(f"**Bias Score:** {eval_results[0]}   **Reason: ** {eval_results[1]}")
                with st.spinner("Determing Correctness..."):
                    eval_results = DeepEval.deep_eval_correctness(st.session_state.user_text, st.session_state.response,st.session_state.response[3])
                    st.markdown(f"**Correctness Score:** {eval_results[0]}   **Reason: ** {eval_results[1]}")
                with st.spinner("Evalutating Summarization..."):
                    eval_results = DeepEval.deep_eval_summary(st.session_state.user_text, st.session_state.response)
                    st.markdown(f"**Summarization Score:** {eval_results[0]}   **Reason: ** {eval_results[1]}")
                with st.spinner("Determing Relevancy..."):
                    eval_results = DeepEval.deep_eval_relevancy(st.session_state.user_text, st.session_state.response)
                    st.markdown(f"**Relevancy Score:** {eval_results[0]}   **Reason: ** {eval_results[1]}")
                with st.spinner("Determing Faithfulness..."):
                    eval_results = DeepEval.deep_eval_faithfulness(st.session_state.user_text, st.session_state.response,st.session_state.response[3])
                    st.markdown(f"**Faithfulness Score:** {eval_results[0]}   **Reason: ** {eval_results[1]}")
                with st.spinner("Determing Hallicination..."):
                    eval_results = DeepEval.deep_eval_hallucination(st.session_state.user_text, st.session_state.response,st.session_state.response[3])
                    st.markdown(f"**Hallucination Score:** {eval_results[0]}   **Reason: ** {eval_results[1]}")
                with st.spinner("Determing Toxicity..."):
                    eval_results = DeepEval.deep_eval_toxicity(st.session_state.user_text, st.session_state.response)
                    st.markdown(f"**Toxicity Score:** {eval_results[0]}   **Reason: ** {eval_results[1]}")
    


    





    




