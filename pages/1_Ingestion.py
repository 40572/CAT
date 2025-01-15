import streamlit as st
import os
from streamlit_extras.stylable_container import stylable_container
from appsupport import FileFunctions as ff
from streamlit.components.v1 import html
import shutil
import tkinter as tk
from tkinter import filedialog
from pdfutils import content_splitting as cs
from pdfutils import content_embedding as ce
import pandas as pd
from appsupport import FileFunctions as ff
from pathlib import Path

@st.dialog("PDF File Viewer")
def file_win(pdfdoc, mode = 'PDF'):
    st.session_state['dialog_open'] = True
    if mode == 'PDF':
        st.write(pdfdoc)
        cs.pdf_viewer(pdfdoc)
        if st.button("Close", key='closepdf'):
            st.rerun()
   
def select_folder():
   root = tk.Tk()
   root.withdraw()
   folder_path = filedialog.askdirectory(master=root)
   #root.destroy()
   return folder_path

def file_selector(folder_path='.'):
    filenames = os.listdir(folder_path)
    selected_filename = st.selectbox('Select a file', filenames)
    return os.path.join(folder_path, selected_filename)

def show_files(path):
    files_df = pd.DataFrame(columns=["file_name"])
    for i, file in enumerate(os.listdir(path)):
        new_row=pd.DataFrame([file], columns=files_df.columns)
        files_df = pd.concat([new_row, files_df], ignore_index=True)
    return files_df

def in_df_on_change(my_key, input_data_dir):
    state = st.session_state[my_key]
    for index, updates in state["edited_rows"].items():
        st.session_state["findf"].loc[st.session_state["findf"].index == index, "Reviewed"] = True
        if 'tool' in updates:
            if updates['tool'] == "Table of Contents":
                curr_level = st.session_state["findf"].loc[st.session_state["findf"].index == index, "level"]
                if curr_level[index] == "N/A":
                    st.session_state["findf"].loc[st.session_state["findf"].index == index, "level"] = "1"
            if updates['tool'] == "Direct Copy" or updates['tool'] == "Text Only":
                curr_level = st.session_state["findf"].loc[st.session_state["findf"].index == index, "level"]
                st.session_state["findf"].loc[st.session_state["findf"].index == index, "level"] = "N/A"
        if 'preview' in updates:
            if updates['preview'] == True:
                preview_file_df = st.session_state["findf"].loc[st.session_state["findf"].index == index, "file_name"]
                updates['preview'] = False
                preview_file = preview_file_df.loc[index]
                file_win(os.path.join(input_data_dir, preview_file))
                
        for key, value in updates.items():
            st.session_state["findf"].loc[st.session_state["findf"].index == index, key] = value
    for row in state["added_rows"]:
        st.warning("Use 'Upload' to add files")
                
    for row in state["deleted_rows"]:
        file =  st.session_state["findf"].loc[st.session_state["findf"].index == row, "file_name"]
        st.session_state["findf"] = st.session_state["findf"].drop(row)
        source_file = os.path.join(input_data_dir, file[row])
        os.remove(source_file)
 
def file_input_edit_frame(df, my_key, input_data_dir):
    if "findf" not in st.session_state:
        st.session_state["findf"] = df
    df['tool']="Direct Copy"
    df['level']="N/A"
    df['preview']=False
    df['primary']=False

    edf = st.data_editor(st.session_state["findf"], num_rows="dynamic",  on_change=in_df_on_change, args=[my_key, input_data_dir],column_config={
            "file_name": st.column_config.TextColumn("File Name", default ='', disabled = True),
            "tool": st.column_config.SelectboxColumn("Tool", options=["Direct Copy", 
                                                                        "Table of Contents", 
                                                                        "Text Only",
                                                                        "Do Not Process"], default= "Direct Copy"),
             "level": st.column_config.SelectboxColumn("Level", options=["N/A", 
                                                                        "1", 
                                                                        "2",
                                                                        "3"], default= "N/A"),

            "preview": st.column_config.CheckboxColumn("Preview",  default = False),
            "primary": st.column_config.CheckboxColumn("Primary",  default = False)
        },
        key= my_key,
        hide_index=True
        )
    return edf

def ing_df_on_change( my_key, ingest_data_dir):
    state = st.session_state[my_key]
    for index, updates in state["edited_rows"].items():
        st.session_state["fingdf"].loc[st.session_state["fingdf"].index == index, "Reviewed"] = True
        if 'preview' in updates:
            if updates['preview'] == True:
                preview_file_df = st.session_state["fingdf"].loc[st.session_state["fingdf"].index == index, "file_name"]
                updates['preview'] = False
                preview_file = preview_file_df.loc[index]
                file_win(os.path.join(ingest_data_dir, preview_file))
                
        for key, value in updates.items():
            st.session_state["fingdf"].loc[st.session_state["fingdf"].index == index, key] = value
    for row in state["added_rows"]:
        st.warning("Use 'Upload' to add files")
    for row in state["deleted_rows"]:
        file =  st.session_state["fingdf"].loc[st.session_state["fingdf"].index == row, "file_name"]
        st.session_state["fingdf"] = st.session_state["fingdf"].drop(row)
        source_file = os.path.join(ingest_data_dir, file[row])
        os.remove(source_file)

def file_ingest_edit_frame(df, my_key, ingest_data_dir):
    if "fingdf" not in st.session_state:
        st.session_state["fingdf"] = df
    df['preview']=False

    edf = st.data_editor(st.session_state["fingdf"], num_rows="dynamic", on_change=ing_df_on_change, args=[my_key, ingest_data_dir], column_config={
            "file_name": st.column_config.TextColumn("File Name", default ='', disabled = True),
            "preview": st.column_config.CheckboxColumn("Preview",  default = False)
        },
        key=my_key,
        hide_index=True
        )
    return edf

def process_files(files,actions, levels, primary, input_data_dir, ingest_data_dir):
    for i, file in enumerate(files):
        if file != '': #do nothing if no file name specified
            if primary[i]:
                filename_root =  os.path.splitext(file)[0]
                filename_ext = os.path.splitext(file)[1]
                target_name = filename_root + '_p' + filename_ext
            else:
                target_name = file
            source_file = os.path.join(input_data_dir, file)
            if actions[i] == 'Direct Copy':
                target_file = os.path.join(ingest_data_dir, target_name)
                shutil.copyfile(source_file,target_file)
            elif actions[i] == 'Table of Contents':
                TOC_level = 1
                if levels[i] != "N/A":
                    TOC_level = int(levels[i])
                cs.split_pdf_by_toc(source_file, ingest_data_dir,primary[i], TOC_level)
            elif actions[i] == 'Text Only':
                cs.copy_pdf_text(source_file, ingest_data_dir, primary[i])
            #if do not process selected then no action is taken by default
   
    st.success("Processing Complete")

def  decomp_controls(input_data_dir, ingest_data_dir):
    col1A, col1B = st.columns([1,2])
    with col1A:
        if st.button("Upload"):
            file_win("", "File")
    with col1B:       
        if st.button("Process Files"):
            files = st.session_state["findf"]['file_name']
            actions = st.session_state["findf"]['tool']
            levels = st.session_state["findf"]['level']
            primary = st.session_state["findf"]['primary']
            process_files(files, actions, levels, primary, input_data_dir, ingest_data_dir)
    files_in= file_input_edit_frame(show_files(input_data_dir),"file_in_df",input_data_dir)

def  ingest_grid_controls( ingest_data_dir, input_data_dir):
    if st.button("Ingest Files"):
        embedding_client = ce.create_embedding_client()
        #will name the search index based on the source folder name
        source_folder_name = (os.path.basename(input_data_dir).split('/')[-1]).strip()
        search_index_name =  source_folder_name.replace(" ", "-")
        search_index_name = "cat-"+ search_index_name.lower()
        st.write("Index Name: " + search_index_name)
        ce.delete_search_index(search_index_name) #removes prior index and all documents if exists
        if (ce.create_search_index(search_index_name) != None) : #index creation was successful
            st.session_state.working_index = search_index_name
            content_dir = os.getenv("CATRINA_CONTENT_DIR") 
            files_to_process = ff.count_files(ingest_data_dir)
            progress_text = "Operation in progress. Please wait."
            prog_bar = st.progress(0.0, text=progress_text)
            processed_files = 0
            for dir_file in os.listdir(ingest_data_dir):
                
                ce.create_content_and_index(dir_file, ingest_data_dir, content_dir, search_index_name, embedding_client)
                processed_files += 1
                prog_bar.progress(processed_files/files_to_process, text=progress_text)
            prog_bar.empty()

    files_ingest= file_ingest_edit_frame(show_files( ingest_data_dir),"file_ingest_df",  ingest_data_dir)

st.header("Document Ingestion")

controls_container = st.empty()

if "working_index" not in st.session_state:
    st.session_state.working_index = None

if "folder_path" not in st.session_state:
    st.session_state.folder_path = None

if "ingest_path" not in st.session_state:
    st.session_state.ingest_path = None



controls_container.empty()
with controls_container:
    
    tab1, tab2, tab3, tab4 = st.tabs(["Document Preparation", "Folder Selection", "Subject Decompostion", "AI Ingestion"])
    with tab1:
        st.markdown("**Document Preparation Instructions**") 
        st.markdown("""
                    The CATrina 'Ingestion' functions allow the AI to 'read' complex, multi-part documents (either RFP, RFI or MMS Proposals) and store
                    them internally for later use for template generation, quality checking and offer evaluation. Note: the resume creation features
                    can be accessed using the 'Resume' functions.

                    Prior to using these functions, it is necessary to first save each document to PDF format. As not all PDF documents are 
                    faithful the PDF specificaiton, it is best to only use Adobe Acrobat Tools to create the PDF documents for ingestion. If 
                    a PDF is received from a potential client and it is not clear wich tool was used, it is OK to attempt ingestion and if the 
                    results are not satisfactory, use Acrobat to load and save the PDF and that will generally fix reading issues.

                    1) For documents that are more than a few pages, it is best to first create a table of contents that separates the document by
                        subjects if it does not currently have one. Using the MS Word table of contents feature is the best tool found so far for
                        creating them.
                    
                    2) Once word documents have TOC created, save the document using only the Adobe PDF option. Do NOT use the MS Word
                        'Save As" feature as the resulting PDF may not be readable by the AI.
                    
                    3) Put all of the documents that will be read into the AI into an unique folder for set. For example, if RFP received contains a 
                        main document, exhibits and attachments then all of these should be in the same folder for reading. Do not include 
                        documents from other RFP into the folder as the AI expects only related documents in the same folder.
                    
                    Once documents are prepped and ready proceed to the 'Folder Selection' screen to continue with ingestion.
                    
                    Note: The AI can only read PDF files, do not include other file types as these may create issues with processing.""")
                    

    with tab2:
        st.header("Select Document Folder")
        
        button_column, note_col  = st.columns([2, 8])
        with button_column:
            if st.button("Select Folder"):
                selected_folder_path = select_folder()
                st.session_state.folder_path = selected_folder_path
        with note_col:
            st.write("Note: It may be necessary to minimize your browser after selecting the 'Select Folder' button.")

        if st.session_state.folder_path != None:
            st.write(st.session_state.folder_path + " has been set as the working folder.")
            if st.session_state.folder_path != None:
                st.session_state.ingest_path = os.path.join(st.session_state.folder_path, "Ingestion")
                if not os.path.exists(st.session_state.ingest_path):
                    os.mkdir(st.session_state.ingest_path)
            else:
                st.session_state.ingest_path = None

    with tab3:
        if st.session_state.folder_path != None:
            st.markdown("**RFP/RFI Source Files Subject Decomposition**") 
            #page layout starts here
            if st.session_state.folder_path != None:
                decomp_controls(st.session_state.folder_path, st.session_state.ingest_path)
        else:
            st.markdown("Please select a folder before performing subject decomposition.")

    with tab4:
        if st.session_state.folder_path != None and ff.count_files(st.session_state.ingest_path) > 0:
            #st.write(ff.count_files(st.session_state.ingest_path))
            st.markdown("**Processed Files for AI Ingestion**") 
            ingest_grid_controls(st.session_state.ingest_path, st.session_state.folder_path)
        else:
            st.markdown("Complete decomposition to create files for AI ingestion.")





 
                
               
           
        
     
     







 

           
