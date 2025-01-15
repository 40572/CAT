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
from azure.search.documents.indexes import SearchIndexClient
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.models import VectorizedQuery
import os

#from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from azure.core.credentials import AzureKeyCredential
import os
from llama_index.embeddings.azure_openai import AzureOpenAIEmbedding
from llama_index.llms.azure_openai import AzureOpenAI
from llama_index.vector_stores.azureaisearch import AzureAISearchVectorStore, IndexManagement, MetadataIndexFieldType
from llama_index.core import StorageContext, VectorStoreIndex, SimpleDirectoryReader
from llama_index.core import Settings
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents import SearchClient
from llama_index.core import Document
from llama_index.core.node_parser import (
    SemanticSplitterNodeParser, SentenceSplitter
)

from azure.search.documents.indexes.models import (
    SimpleField,
    SearchFieldDataType,
    SearchableField,
    SearchField,
    VectorSearch,
    HnswAlgorithmConfiguration,
    VectorSearchProfile,
    SemanticConfiguration,
    SemanticPrioritizedFields,
    SemanticField,
    SemanticSearch,
    SearchIndex,
    AzureOpenAIVectorizer,
    AzureOpenAIVectorizerParameters
)
from azure.search.documents import SearchIndexingBufferedSender
import uuid
import sys


azure_search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
azure_search_credential = AzureKeyCredential(os.getenv("AZURE_SEARCH_KEY"))
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

def ret_search_indexes():
    results=[]
    index_client = SearchIndexClient(endpoint=azure_search_endpoint,  credential=azure_search_credential)
    results_paged=index_client.list_index_names()
    for  r in results_paged:
        results.append(r)
    return results

def create_req_summary_index(index_name):
    # Create a search index
    index_client = SearchIndexClient(
        endpoint=azure_search_endpoint, credential=azure_search_credential)

    fields = [
            SimpleField(name="id", type=SearchFieldDataType.String, key=True, sortable=True, filterable=True, facetable=True),
            SearchableField(name="title", type=SearchFieldDataType.String),
            SearchableField(name="type", type=SearchFieldDataType.String),
            SearchableField(name="content", type=SearchFieldDataType.String),
            SearchField(name="contentVector", type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                        searchable=True, vector_search_dimensions=azure_openai_embedding_dimensions, vector_search_profile_name="myHnswProfile"),
        ]

    # Configure the vector search configuration  
    vector_search = VectorSearch(
        algorithms=[
            HnswAlgorithmConfiguration(
                name="myHnsw"
            )
        ],
        profiles=[
            VectorSearchProfile(
                name="myHnswProfile",
                algorithm_configuration_name="myHnsw",
                vectorizer_name="myVectorizer"
            )
        ],
        vectorizers=[
            AzureOpenAIVectorizer(
                vectorizer_name="myVectorizer",
                parameters=AzureOpenAIVectorizerParameters(
                    resource_url=azure_openai_embedding_endpoint,
                    deployment_name=azure_openai_embedding_deployment,
                    model_name=azure_openai_embedding_model_name,
                    api_key=azure_openai_key
                )
            )
        ]
    )
    
    semantic_config = SemanticConfiguration(
        name="my-semantic-config",
        prioritized_fields=SemanticPrioritizedFields(
            content_fields=[SemanticField(field_name="content")]
        )
    )

    # Create the semantic settings with the configuration
    semantic_search = SemanticSearch(configurations=[semantic_config])

    # Create the search index with the semantic settings
    index = SearchIndex(name=index_name, fields=fields,
                        vector_search=vector_search, semantic_search=semantic_search)
    result = index_client.create_or_update_index(index)
    return result.name


def create_search_index(index_name):
    # Create a search index
    index_client = SearchIndexClient(
        endpoint=azure_search_endpoint, credential=azure_search_credential)

    fields = [
            SimpleField(name="id", type=SearchFieldDataType.String, key=True, sortable=True, filterable=True, facetable=True),
            SearchableField(name="content", type=SearchFieldDataType.String),
            SearchField(name="contentVector", type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                        searchable=True, vector_search_dimensions=azure_openai_embedding_dimensions, vector_search_profile_name="myHnswProfile"),
        ]

    # Configure the vector search configuration  
    vector_search = VectorSearch(
        algorithms=[
            HnswAlgorithmConfiguration(
                name="myHnsw"
            )
        ],
        profiles=[
            VectorSearchProfile(
                name="myHnswProfile",
                algorithm_configuration_name="myHnsw",
                vectorizer_name="myVectorizer"
            )
        ],
        vectorizers=[
            AzureOpenAIVectorizer(
                vectorizer_name="myVectorizer",
                parameters=AzureOpenAIVectorizerParameters(
                    resource_url=azure_openai_embedding_endpoint,
                    deployment_name=azure_openai_embedding_deployment,
                    model_name=azure_openai_embedding_model_name,
                    api_key=azure_openai_key
                )
            )
        ]
    )
    
    semantic_config = SemanticConfiguration(
        name="my-semantic-config",
        prioritized_fields=SemanticPrioritizedFields(
            content_fields=[SemanticField(field_name="content")]
        )
    )

    # Create the semantic settings with the configuration
    semantic_search = SemanticSearch(configurations=[semantic_config])

    # Create the search index with the semantic settings
    index = SearchIndex(name=index_name, fields=fields,
                        vector_search=vector_search, semantic_search=semantic_search)
    result = index_client.create_or_update_index(index)
    return result.name


def ret_documents_azure(k, user_query, search_index_name,search_mode='simple'):
    
    search_client = SearchClient(endpoint=azure_search_endpoint, index_name=search_index_name, credential=azure_search_credential)
    if search_mode == 'vector':
        vector_query = VectorizedQuery(vector=embed_text(user_query), k_nearest_neighbors=50, fields="contentVector")
        results = search_client.search(  
            search_text=None,  
            vector_queries= [vector_query],
            select=["title", "content", "category", "file_name"],
            top=k,
            include_total_count=True,
        )  
    else :
        results = search_client.search(  
            search_text=user_query,  
            query_type='simple',
            search_mode='any',
            select=["title", "content", "category", "file_name"],
            include_total_count=True,
            #top=k
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
   
def get_response_for_doc_text( user_query, system_msg, doc_text, temperature, max_tokens):
    
    template = """
    {system_msg} Answer the following questions:
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
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=None,
        max_retries=2
        
    )
    

    chain = prompt | llm | StrOutputParser()
 
    return chain.stream({
        "system_msg" :system_msg,
        "user_question": user_query,
        "documents": doc_text,
    })
def create_search_client(index_name):
    search_client = SearchClient(endpoint=azure_search_endpoint, index_name=index_name, credential=azure_search_credential)
    return search_client
