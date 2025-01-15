
import streamlit as st
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
from llama_index.core.node_parser import (
    SemanticSplitterNodeParser, SentenceSplitter
)
from llama_index.core import Document
import uuid
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from llama_index.core import StorageContext, load_index_from_storage
import os



# Variables used Globally
path = 'C:\\aiprojects\\CAT\\Document Summary\\Content'  

system_def ="""You are an assitant for extracting services from requests for proposal documents. 
Your name is CATrina.A service is any work or activity the bidder must perform .
If there are no services found in the document, simply say 'No services'.
Do not elablorate or enhance the content of the found services, simply state the service 
as it appears in the source document and do not include other comments or suggestions.
Do not ask for other documents and do not ask for other questions.
"""

process_task = """Find all services in the documents to be provided by the bidder.
"""
keywords = """'service', 'services', 'activity', 'monitor', 'report', 'manage'"""

summarize_task = """Provie a summary of all services bidders must perform found in the document. """

serv_summary_index = 'cat-serv-summary'

temp_name = "Child Support Modernization PMO RFP # 437004-M23-0001963"


#configure streamlit for the ap
st.set_page_config(page_title="CATrina Services Extract and Summary", page_icon = "👩‍🔧")

#st.session_state.system_message = system_def - set in sidebar, used for altering system message (system_def) during the session
if "system_message" not in st.session_state:
    st.session_state.system_message = system_def

if "process_task" not in st.session_state:
    st.session_state.process_task = process_task

if "keywords" not in st.session_state:
    st.session_state.keywords = keywords

if "summarize_task" not in st.session_state:
    st.session_state.summarize_task = summarize_task

if "summary_length" not in st.session_state:
    st.session_state.summary_length = 1024

if "max_response_length" not in st.session_state:
    st.session_state.max_response_length = 4096

if "source_index" not in st.session_state:
    st.session_state.source_index = ""

if "target_index" not in st.session_state:
    st.session_state.target_index = ""

if "temperature" not in st.session_state:
    st.session_state.temperature = 0

if "title" not in st.session_state:
    st.session_state.title = temp_name

if "type" not in st.session_state:
    st.session_state.type = "RFI/RFP"

 

st.title("Services Extraction and Summarization")

st.header("Source Document Information")
st.session_state.title = st.text_input("Document Title", temp_name)

st.session_state.type = st.selectbox(
        "Document Type",
        ('RFI/RFP', 'Proposal'),
    
    )
      
st.header("System Settings")
st.subheader("AI Behavior")
# AI Settings
st.session_state.system_message = st.text_area(
    "System Message", value=system_def
)
    
    #Document Settings
  
st.session_state.ret_K = st.number_input(
    "Document Retreival K", min_value=1, max_value=400, step=1,value=280
)
    
# Model Settings
st.subheader("Model Parameters")

st.session_state.max_response_length = st.number_input(
    "Max Response Length", value=4096
)
st.session_state.temperature = st.number_input(
    "Model Temperature", min_value=0.0, max_value=1.0, step=0.1,value=0.0
)
#Query Azure to get the list of indexs available, rebuild or create new

st.subheader("Source Documents Index")

results = AIFunctions.ret_search_indexes()
doc_index = st.selectbox(
    "Select Source Index",
    (results),
)
st.session_state.source_index = doc_index

st.subheader("Target Services Index")
sel_column, new_column  = st.columns([4,4])

with sel_column:
    results = AIFunctions.ret_search_indexes()
    target_index = st.selectbox(
        "Select Target Services Index",
        (results),
    
    )
    
    st.session_state.target_index = target_index

with new_column:
    index_name = st.text_input("New Index Name")
    if st.button("Create New Index"):
        target_index = AIFunctions.create_search_index(index_name)
        st.write(f"Index {target_index} has been created")
        st.session_state.target_index = target_index

st.text(f"Target Requirments Index: {target_index}")

st.session_state.process_task = st.text_area(
    "Process Task", value=process_task
)

st.session_state.keywords = st.text_area(
    "Keywords", value=keywords
)

st.session_state.summarize_task = st.text_area(
    "Summarize Task", value=summarize_task
)

st.session_state.summary_length = st.number_input(
    "Summary Length", value=1024
)


if st.button("Start Services Extraction"):
   with st.spinner('Getting Documents'):
    target_client = AIFunctions.create_search_client(target_index)
    #get all text that contains our keywords
   
    results = AIFunctions.ret_documents_azure(st.session_state.ret_K, keywords, st.session_state.source_index,'simple' )
    responses =[]
    progress_text = "Services Extraction in progress. Please wait."
    docs_processed = 0.0
    prog_bar = st.progress(docs_processed, text=progress_text)
    doc_count = results.get_count()
    doc_increment = 1/doc_count
    
    for result in results:
        docs_processed += doc_increment
        
        prog_bar.progress(docs_processed, text=progress_text)
        if result['category'] == 'text':
            content = ''.join(map(str, response))
            response = AIFunctions.get_response_for_doc_text(process_task,  system_def , result['content'] + "\\n",st.session_state.temperature,  st.session_state.max_response_length)
            content_vector =  AIFunctions.embed_text(content)
            #copying the extracted requirements to our target requirements search index for future use
            target_doc = {'id': str(uuid.uuid1()), 'content': content, 'contentVector':content_vector}
            result = target_client.upload_documents(target_doc)
            responses.append(content)
    target_client.close()
    #summarize the requirements so that we can run comparisons in the future
    doc_texts = ""        
    for response in responses:
        doc_texts  += response + "\\n"
    #all CAT documents share the same requirements summary index
    summary_index =AIFunctions.create_req_summary_index(serv_summary_index)

    summary_client = AIFunctions.create_search_client(serv_summary_index)
    #chunk the content in case it is too large for the model to accept
    if len(doc_texts) >= (st.session_state.max_response_length):
                splitter = SentenceSplitter(
                    chunk_size=st.session_state.max_response_length,
                    chunk_overlap=0,
                    )
                nodes = splitter.get_nodes_from_documents([Document(id=uuid.uuid1(), text=doc_texts)])
                for node in nodes:
                    content_chunk = node.get_content()
                    response = AIFunctions.get_response_for_doc_text(summarize_task,  system_def,  content_chunk, st.session_state.temperature, st.session_state.summary_length)
                    #load summaries into our proposal requirments summary index used for all documents
                    content = ''.join(map(str, response))
                    content_vector =  AIFunctions.embed_text(content)
                    title = st.session_state.title
                    type = st.session_state.type
                    summary_doc = {'id': str(uuid.uuid1()), 'title': title,  'content': content, 'contentVector':content_vector}
                    result = summary_client.upload_documents(summary_doc)
    summary_client.close()
    prog_bar.empty()
    st.write ("Services Processing Complete")


                

