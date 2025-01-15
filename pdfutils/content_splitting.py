


import streamlit as st
from streamlit_pdf_viewer import pdf_viewer
import fitz  # PyMuPDF
import os
import pandas as pd

def remove_invalid_filename_characters(filename):
    
    cleaned_filename = filename.translate(str.maketrans('','','–— [<>:"-/\\|?*],'))
     
    return cleaned_filename


def copy_pdf_text(pdf_path, output_dir, primary):
    file_name_no_ext = os.path.splitext(os.path.basename(pdf_path))[0]
    if primary:
        file_name_no_ext = file_name_no_ext + "_p"
    pdf_document = fitz.open(pdf_path)
    text = ""
    for page_num in range(len(pdf_document)):
        page = pdf_document.load_page(page_num)
        text = page.get_text()
        pdf_document_dest = fitz.open()
        txt_page = pdf_document_dest.new_page()
        position = fitz.Point(10, 10)  # (x, y) coordinates in points
        txt_page.insert_text(position, text, fontsize=10)
        file_name = file_name_no_ext + str(page_num) + ".pdf"
        pdf_document_dest.save(os.path.join(output_dir, file_name))
        pdf_document_dest.close()


def split_pdf_by_toc(pdf_path, output_dir, primary, toc_depth=1):
    # Open the PDF file
    pdf_document = fitz.open(pdf_path)
    #print (pdf_document)
    toc = pdf_document.get_toc(simple=True)
    #print (toc)
    #sys.exit()
    # Filter TOC based on the desired depth
    #toc = [entry for entry in toc if entry[0] <= toc_depth]

    for i, entry in enumerate(toc):
        title, page_num = entry[1], entry[2] - 1
        next_page_num = toc[i + 1][2] - 1 if i + 1 < len(toc) else pdf_document.page_count
        # Create a new PDF for each section
        new_pdf = fitz.open()
        new_pdf.insert_pdf(pdf_document, page_num,  next_page_num)
        if primary:
            title = title + "_p"
        output_file = remove_invalid_filename_characters(f"{title}.pdf")
        output_path = os.path.join(output_dir, output_file)
        new_pdf.save(output_path)
        new_pdf.close()

    pdf_document.close()
    

