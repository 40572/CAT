#Content Embedding ingests files that have been decomposed by embedding the content and creating an search index

#PDF Processing Spec

#filename will be:
#   source document file for text extraction
#   image filename for extracted images
#   table html file name for extracted tables


from pdfutils import text_analysis as ta
import os
import fitz
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
#import pymupdf4llm
import tiktoken
from typing import List, Tuple, Optional


azure_search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT") 
azure_search_credential = AzureKeyCredential(os.getenv("AZURE_SEARCH_KEY")) 
azure_search_api_version = os.getenv("AZURE_SEARCH_API_KEY")
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

def est_token_len(text_to_tokenize):
    encoding = tiktoken.encoding_for_model(azure_openai_model)
    return len(encoding.encode(text_to_tokenize))

def create_embedding_client():
    embedding_client = AzureOpenAIEmbedding(
        azure_deployment=azure_openai_embedding_model_name,
        api_version=azure_openai_embedding_api_version,
        azure_endpoint=azure_openai_embedding_endpoint,
        api_key=azure_openai_embedding_api_key,
        credential = AzureKeyCredential(azure_openai_embedding_api_key)
        )
    return embedding_client

def embed_text(content, embedding_client):
    
    content_embeddings = embedding_client.get_text_embedding(content)
    return content_embeddings

def delete_search_index(azure_search_index_name):
    try:
        client = SearchIndexClient(azure_search_endpoint,azure_search_credential)
        client.delete_index(azure_search_index_name)
        return True
    except:
        return False
    
def list_search_indexes():
    client = SearchIndexClient(azure_search_endpoint,azure_search_credential)
    return client.list_index_names()
    
    
def create_search_index(azure_search_index_name):
    # Create a search index
    index_client = SearchIndexClient(
        endpoint=azure_search_endpoint, credential=azure_search_credential)
    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True, sortable=True, filterable=True, facetable=True),
        SimpleField(name="file_name", type=SearchFieldDataType.String),
        SearchableField(name="primary", type=SearchFieldDataType.String),
        SearchableField(name="title", type=SearchFieldDataType.String),
        SearchableField(name="content", type=SearchFieldDataType.String),
        SearchableField(name="category", type=SearchFieldDataType.String,
                        filterable=True),
        SearchField(name="titleVector", type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                    searchable=True, vector_search_dimensions=azure_openai_embedding_dimensions, vector_search_profile_name="myHnswProfile"),
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
            title_field=SemanticField(field_name="title"),
            keywords_fields=[SemanticField(field_name="category")],
            content_fields=[SemanticField(field_name="content")]
        )
    )
    # Create the semantic settings with the configuration
    semantic_search = SemanticSearch(configurations=[semantic_config])
    # Create the search index with the semantic settings
    index = SearchIndex(name=azure_search_index_name, fields=fields,
                        vector_search=vector_search, semantic_search=semantic_search)
    result = index_client.create_or_update_index(index)
    return result

def tokenize(text: str) -> List[str]:
    encoding = tiktoken.encoding_for_model(azure_openai_model)
    return encoding.encode(text)


# This function chunks a text into smaller pieces based on a maximum token count and a delimiter.
def chunk_on_delimiter(input_string: str, max_tokens: int, delimiter: str):
    chunks = input_string.split(delimiter)
    combined_chunks, _, dropped_chunk_count = combine_chunks_with_no_minimum(
        chunks, max_tokens, chunk_delimiter=delimiter, add_ellipsis_for_overflow=True
    )
    if dropped_chunk_count > 0:
        print(f"warning: {dropped_chunk_count} chunks were dropped due to overflow")
    combined_chunks = [f"{chunk}{delimiter}" for chunk in combined_chunks]
    return combined_chunks


# This function combines text chunks into larger blocks without exceeding a specified token count. It returns the combined text blocks, their original indices, and the count of chunks dropped due to overflow.
def combine_chunks_with_no_minimum(chunks: List[str], max_tokens: int, chunk_delimiter="\n\n", header: Optional[str] = None, add_ellipsis_for_overflow=False,) -> Tuple[List[str], List[int]]:
    dropped_chunk_count = 0
    output = []  # list to hold the final combined chunks
    output_indices = []  # list to hold the indices of the final combined chunks
    candidate = (
        [] if header is None else [header]
    )  # list to hold the current combined chunk candidate
    candidate_indices = []
    for chunk_i, chunk in enumerate(chunks):
        chunk_with_header = [chunk] if header is None else [header, chunk]
        if len(tokenize(chunk_delimiter.join(chunk_with_header))) > max_tokens:
            print(f"warning: chunk overflow")
            if (
                    add_ellipsis_for_overflow
                    and len(tokenize(chunk_delimiter.join(candidate + ["..."]))) <= max_tokens
            ):
                candidate.append("...")
                dropped_chunk_count += 1
            continue  # this case would break downstream assumptions
        # estimate token count with the current chunk added
        extended_candidate_token_count = len(tokenize(chunk_delimiter.join(candidate + [chunk])))
        # If the token count exceeds max_tokens, add the current candidate to output and start a new candidate
        if extended_candidate_token_count > max_tokens:
            output.append(chunk_delimiter.join(candidate))
            output_indices.append(candidate_indices)
            candidate = chunk_with_header  # re-initialize candidate
            candidate_indices = [chunk_i]
        # otherwise keep extending the candidate
        else:
            candidate.append(chunk)
            candidate_indices.append(chunk_i)
    # add the remaining candidate to output if it's not empty
    if (header is not None and len(candidate) > 1) or (header is None and len(candidate) > 0):
        output.append(chunk_delimiter.join(candidate))
        output_indices.append(candidate_indices)
    return output, output_indices, dropped_chunk_count

    
def create_content_and_index(dir_file, source_dir, content_dir, azure_search_index_name, embedding_client):
    #this function extracts tables and images from the source documents and populates the multi-media
    #content directory with the extracts as well as populating the search index with
    #all text. For multimedia content, these elements are represented in the search index using
    #the text that is in the source document (which during decomp results in documents of one subject)
    #as subject documents can still be too large for the model to process additional text splitting occurs:

    #1) Any text that exists between headers in the document are considered to be sub-topics and are split out 
    #   as separate documents. If no headers can be discerned, then whole document is used.
    #2) after the sub document splits are attempted, the next step is to use a semantic text split model
    #   so that sentences that appear to be related to the same idea are kept together
    #3) if after the first 2 splits are completed and the resulting text is still too large then final split
    #   is simple sentence chunking with an overlap

  
    documents = []
    source_file = os.path.join(source_dir, dir_file )
    if "_p." in dir_file or  "_P." in dir_file:
        primary = "True"
    else:
        primary = "False"

    doc = fitz.open(source_file)
    font_counts, styles = ta.fonts(doc,False)
    size_tag = ta.font_tags(font_counts, styles)
    tagged_doc_text = ta.headers_para(doc, size_tag, content_dir, source_file)
    
    doc_title = os.path.splitext(dir_file)[0]
    article_extract_elements = ta.article_extraction(tagged_doc_text, doc_title)

    

    if len(article_extract_elements) !=0: #able to extact article base on headers
        doc_text = ta.format_elements(article_extract_elements,False)
        content_file =ta.extract_2_pdf(source_file, article_extract_elements, content_dir, dir_file)#returns location of the content file
    else: #not able to extact article so will process entire file as content
        doc_text = ta.format_elements(tagged_doc_text,False)

        content_file =ta.extract_2_pdf(source_file, tagged_doc_text, content_dir, dir_file)#returns location of the content file 
    
    titleVector = embed_text(doc_title, embedding_client)
    file_name = source_file
    splitter = SemanticSplitterNodeParser(
        buffer_size=1, breakpoint_percentile_threshold=95, embed_model=embedding_client
        )
    nodes = splitter.get_nodes_from_documents([Document(id=uuid.uuid1(), text=doc_text)])
    
    embedding_text = ""
    for node in nodes:
        #sometimes semantic split can still be too large so it is necessary to check and resort to absolute chunks
        
        if int(est_token_len(node.get_content()))>= int(azure_openai_embedding_model_max_size):
            sub_splitter = SentenceSplitter(
            chunk_size=azure_openai_embedding_model_max_size/2,
            chunk_overlap=20,
            )
            sub_nodes = sub_splitter.get_nodes_from_documents([Document(id=uuid.uuid1(), text=node.get_content())])
            for sub_node in sub_nodes:
                try:
                    contentVector = embed_text(sub_node.get_content(), embedding_client)
                    text_doc = {'id': str(uuid.uuid1()), 'file_name':content_file, 'primary':primary, 'title':doc_title, 'content': sub_node.get_content(), 'category':'text', 'titleVector':titleVector,  'contentVector':contentVector}
                    documents.append(text_doc)
                    embedding_text = sub_nodes[0].get_content()   
                except: 
                    print(sub_node.get_content())

        else:
            if node.get_content() != "":
                contentVector = embed_text(node.get_content(), embedding_client)
                text_doc = {'id': str(uuid.uuid1()), 'file_name':content_file, 'primary':primary, 'title':doc_title, 'content': node.get_content(), 'category':'text', 'titleVector':titleVector,  'contentVector':contentVector}
                documents.append(text_doc)
                embedding_text = nodes[0].get_content()

    #review the elements extracted for the article for images and if present, index and save them
    for element in article_extract_elements:
        if element[0] == 'image':
            titleVector = embed_text("image from: " + doc_title, embedding_client)
            contentVector = embed_text("image from: " + embedding_text, embedding_client)
            image_doc = {'id': str(uuid.uuid1()), 'file_name':element[3], 'primary':primary, 'title':"image from: " + doc_title, 'content': "", 'category':'image', 'titleVector':titleVector,  'contentVector':contentVector}
            documents.append(image_doc)

    tables = ta.table_extraction(doc, content_dir, source_file)

    if len(documents) != 0:
        search_client = SearchClient(endpoint=azure_search_endpoint, index_name=azure_search_index_name, credential=azure_search_credential)
        result = search_client.upload_documents(documents)
        search_client.close()
    
