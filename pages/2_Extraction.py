import streamlit as st
import os
from streamlit_extras.stylable_container import stylable_container
from appsupport import FileFunctions as ff
from streamlit.components.v1 import html
from appsupport import AIFunctions
import shutil
import tkinter as tk
from tkinter import filedialog
from pdfutils import content_splitting as cs
from pdfutils import content_embedding as ce
import pandas as pd
from appsupport import FileFunctions as ff

st.header("Summary Extraction")
#controls_container = st.container(border=True)  
azure_openai_embedding_model_max_size = os.getenv("AZURE_OPENAI_EMBEDDING_MODEL_MAX_SIZE") 

def summarize_reqs(req_text):
     #perform summarization on document - if it is too large then it will be split until it will fit and the recusively summarize the requirements  
                document_len = int(ce.est_token_len(req_text))
                summarization_chunks = 2*(document_len//int(azure_openai_embedding_model_max_size) + 1) #ensures that we will always have at least one chunk
                chunk_size = document_len // summarization_chunks
                text_chunks = ce.chunk_on_delimiter(req_text, chunk_size, ".")
                summary_doc = ""
                progress_text = "Summarization in progress. Please wait."
                prog_bar = st.progress(0.0, text=progress_text)
                processed_chunks = 0
                chunks_to_process = len(text_chunks)
                for text_chunk in text_chunks:
                    processed_chunks += 1
                    response = AIFunctions.get_response_for_doc_text(st.session_state.process_task,   st.session_state.system_message , text_chunk ,st.session_state.temperature,  st.session_state.max_response_length)
                    response_list = list(response) #want to get all of the content in the response as it returns a stream
                    response_text = ""
                    for item in response_list:
                        response_text = response_text + item
                    summary_doc = summary_doc + response_text
                    prog_bar.progress(processed_chunks/chunks_to_process, text=progress_text)
                prog_bar.empty()
                return summary_doc

def summarize_extract(ret_k, search_type):
     #perform summarization on document - if it is too large then it will be split until it will fit and the recusively summarize the requirements  
    with st.spinner("Exracting all matching documents from working index."): 
        results = AIFunctions.ret_documents_azure(ret_k,  st.session_state.keywords, st.session_state.working_index, search_type )
        req_list = ""
        progress_text = "Extraction in progress. Please wait."
        prog_bar = st.progress(0.0, text=progress_text)
        processed_documents = 0
        documents_to_process = results.get_count()
        for result in results:
            #st.write(result)
            processed_documents += 1
            req_list = req_list + result['content'] 
            prog_bar.progress(processed_documents/documents_to_process, text=progress_text)
        prog_bar.empty()
        summary_doc = req_list
        #recusively call summarization on all documents until target size is reached
        pass_count = 0
    while True:
        pass_count += 1
        with st.spinner(f"Summarizing Documents Pass {pass_count}"): 
            summary_doc = summarize_reqs(summary_doc)
        if int(ce.est_token_len(summary_doc)) < int(azure_openai_embedding_model_max_size):
            break
                   
    return summary_doc

if "folder_path" not in st.session_state:
    st.session_state.folder_path = None

if "ingest_path" not in st.session_state:
    st.session_state.ingest_path = None

if "working_index" not in st.session_state:
    st.session_state.working_index = None

if "system_message" not in st.session_state:
    st.session_state.system_message = ""

if "process_task" not in st.session_state:
    st.session_state.process_task = ""

if "keywords" not in st.session_state:
    st.session_state.keywords = ""

if "summarize_task" not in st.session_state:
    st.session_state.summarize_task = ""

if "summary_length" not in st.session_state:
    st.session_state.summary_length = 1024

if "max_response_length" not in st.session_state:
    st.session_state.max_response_length = 4096

if "target_index" not in st.session_state:
    st.session_state.target_index = ""

if "temperature" not in st.session_state:
    st.session_state.temperature = 0

if "ret_K" not in st.session_state:
    st.session_state.ret_K = 10

index_list = ce.list_search_indexes()
if st.session_state.working_index == None:
    st.session_state.working_index = st.selectbox(
    "Select an index to use for extraction:",
    index_list,
    )
else:
     st.write("Working Index: " + st.session_state.working_index)



controls_container = st.empty()

st.session_state.system_message ="""You are an assistant that summarizes documents. 
           Summarize only what is found in the document.
            Do not ask for other documents and do not ask for other questions.
           """

with controls_container:
    if st.session_state.working_index != None: 
        tab1, tab2, tab3 = st.tabs(["Customer Summary", "Objective", "Team Profile"])
        with tab1:
            st.markdown("**Customer Summary**")
            st.session_state.process_task = st.text_area("Task",
"""Provide a 100 word or less summary of the government agency that either wrote the document or is receiving the document.  
in the summary, only indicate the state, agency, and department. Do not include other information.  If the document does not include any 
information about an agency, then do not provide any response.""",
                            )
                        
            st.session_state.keywords = st.text_input("Document Keywords", "('state' or 'department'or 'agency') and 'True'")            
            ret_k = st.number_input("Retrival K", min_value=0, max_value=1000, value=10, step=1, label_visibility="visible", key = 'rcs')
            if st.button("Extract Customer Summary"):
                st.write(summarize_extract(ret_k,'vector'))
                     
               
        with tab2:
            st.markdown("**Objective**") 
            
            st.session_state.process_task = st.text_area("Task",
            """Provide a 100 word or less summary of the  objective or purpose as stated in the document.  
            If the document does not include any information about an objective or purpose, then do not provide any response.""",
                            )
                        
            st.session_state.keywords = st.text_input("Document Keywords", "'objective', 'purpose'")            
            ret_k = st.number_input("Retrival K", min_value=0, max_value=1000, value=10, step=1, label_visibility="visible", key = 'docobj')
            if st.button("Extract Objective"):
                st.write(summarize_extract(ret_k,'simple'))
            
        with tab3:
            st.markdown("**Team Profile**") 
            st.session_state.process_task = st.text_area("Task",
            """Provide a 100 word or less summary of each team member, role, or position and qualifications as found in the document.  
            If the document does not include any information about team members or roles, then do not provide any response.""",
                            )
                        
            st.session_state.keywords = st.text_input("Document Keywords", "'team', 'member', 'role', 'qualification'")            
            ret_k = st.number_input("Retrival K", min_value=0, max_value=1000, value=10, step=1, label_visibility="visible", key = 'team')
            if st.button("Extract Profile"):
                st.write(summarize_extract(ret_k,'simple'))


   


 
                
               
           
        
     
     







 

           
