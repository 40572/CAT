# If necessary, install the openai Python library by running 
# pip install openai


from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
import streamlit as st
from llama_index.core import StorageContext, load_index_from_storage
import os
from azure.core.credentials import AzureKeyCredential
from langchain_openai import AzureChatOpenAI
from azure.core.credentials import AzureKeyCredential
from llama_index.embeddings.azure_openai import AzureOpenAIEmbedding
from azure.search.documents import SearchClient
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.models import VectorizedQuery



azure_search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
azure_search_credential = AzureKeyCredential(os.getenv("AZURE_SEARCH_KEY"))
azure_search_index_name = "cris-mm-rag-alt-pdf"
azure_openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
azure_openai_key = os.getenv("AZURE_OPENAI_API_KEY")
azure_openai_api_version = os.getenv("AZURE_OPENAI_API_VERSION")
azure_openai_model = os.getenv("AZURE_OPENAI_MODEL")
azure_openai_model_name = os.getenv("AZURE_OPENAI_MODEL_NAME")
azure_openai_deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
azure_openai_embedding_endpoint =os.getenv("AZURE_OPENAI_EMBEDDING_ENDPOINT")
azure_openai_embedding_api_key=os.getenv("AZURE_OPENAI_EMBEDDING_API_KEY")
azure_openai_embedding_dimensions = os.getenv("AZURE_OPENAI_EMBEDDING_DIMENSIONS")
azure_openai_embedding_model_name = os.getenv("AZURE_OPENAI_EMBEDDING_MODEL_NAME")
azure_openai_embedding_deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
azure_openai_embedding_api_version = os.getenv("AZURE_OPENAI_EMBEDDING_API_VERSION")
azure_openai_embedding_model_max_size = os.getenv("AZURE_OPENAI_EMBEDDING_MODEL_MAX_SIZE")


def embed_text(content):
    embedding_client = AzureOpenAIEmbedding(
        azure_deployment=azure_openai_embedding_model_name,
        api_version=azure_openai_embedding_api_version,
        azure_endpoint=azure_openai_embedding_endpoint,
        api_key=azure_openai_embedding_api_key,
        credential = AzureKeyCredential(azure_openai_embedding_api_key)
    )
    content_embeddings = embedding_client.get_text_embedding(content)
    return content_embeddings


def ret_documents_azure(k, user_query):
    
    search_client = SearchClient(endpoint=azure_search_endpoint, index_name=azure_search_index_name, credential=azure_search_credential)
    vector_query = VectorizedQuery(vector=embed_text(user_query), k_nearest_neighbors=50, fields="contentVector")
   
    results = search_client.search(  
        search_text=None,  
        vector_queries= [vector_query],
        select=["title", "content", "category", "file_name"],
        top=k
    )  
    
    return results

def get_response2(k, user_query, chat_history, system_msg, max_tokens):
    
    template = """
    {system_msg} Answer the following questions considering the history of the conversation:
    Chat history: {chat_history}
    User question: {user_question}
    Use the following documents when answering questions:
    Documents: {documents}
    """
    prompt = ChatPromptTemplate.from_template(template)
    
    llm = AzureChatOpenAI( 
        azure_deployment=azure_openai_deployment_name,  # or your deployment
        openai_api_type="azure",
        azure_endpoint=azure_openai_endpoint,
        model_name=azure_openai_model_name,
        api_version=azure_openai_api_version,  # or your api version
        temperature=0,
        max_tokens=None,
        timeout=None,
        max_retries=2
        
    )
    

    chain = prompt | llm | StrOutputParser()
 
    image_links = []
    citation_links = []
    doc_texts = ''

    results = ret_documents_azure(k, user_query )
    
        
    for result in results:
        
        if result['category'] == 'image':
            image_links.append(result['file_name']) 
        elif result['category'] == 'text':
            citation_links.append(result['file_name'])
            doc_texts  += result['content'] + "\\n"
    
    return chain.stream({
        "system_msg" :system_msg,
        "chat_history": chat_history,
        "user_question": user_query,
        "documents": doc_texts,
    }), image_links, citation_links, doc_texts
   
       
       
        
