from appsupport import FileFunctions
from appsupport import AIFunctions
from appsupport import DeepEval
from langchain_core.messages import AIMessage, HumanMessage
from llama_index.core.node_parser import (
    SemanticSplitterNodeParser, SentenceSplitter
)
from llama_index.core import Document
import uuid

# Variables used Globally
path = 'C:\\aiprojects\\CAT\\Document Summary\\Content'  

system_def ="""You are an assitant for extracting requirements from requests for proposal documents. 
Your name is CATrina. A requirement is a sentance in the document that  contains the  words 'must', 'shall', 'will', 'require', 'required', 'requires' or 'ensure'.
If there are no requirements found in the document, simply say 'No requirements found'.
Do not elablorate or enhance the content of the found requirements, simply state the requirement 
as it appears in the source document and do not include other comments or suggestions.
Do not ask for other documents and do not ask for other questions.
Classify each requirement as 'Service', 'Operational', or 'Contractual'"""

process_task = """Find all sentences that contain the words 'must', 'shall', 'will', 'require', 'required', 'requires' or 'ensure'.
"""

ret_k = 280 #set this value to the number of pdf documents in the content diretory to ensure nothing is missed
response_len =4096
model_temp=0
#get all the documents in our index that match this task
results = AIFunctions.ret_documents_azure(ret_k, process_task )

responses =[]

for result in results:
    if result['category'] == 'text':
        doc_title =  result['title']
        print(f"Requirements found in document: {doc_title}")
        response = AIFunctions.get_response_for_doc_text(process_task,  system_def , result['content'] + "\\n")
        response_string = ''.join(map(str, response))
        print(response_string)
        responses.append(response_string)

process_task = """Provie a summary of all operational requirements found in the document. """
doc_texts = ""        
for response in responses:
    doc_texts  += response + "\\n"
#chunk the content in case it is too large for the model to accept
if len(doc_texts) >= (response_len):
            splitter = SentenceSplitter(
            chunk_size=response_len,
            chunk_overlap=0,
            )
            nodes = splitter.get_nodes_from_documents([Document(id=uuid.uuid1(), text=doc_texts)])
            for node in nodes:
                content_chunk = node.get_content()
                response = AIFunctions.get_response_for_doc_text(process_task,  system_def,  content_chunk)
                print("Requirements Summary")
                print(''.join(map(str, response)))
                   

                    



          