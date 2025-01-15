
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

def search_index_by_keywords(ret_K, working_index, keywords):
  

