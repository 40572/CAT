import streamlit as st
import webbrowser as wb
import pybase64

st.title("Article Viewer")



def displayPDF(file):
    #wb.open_new_tab(f"http://localhost:8501/?text={"my text"}")
    # Opening file from file path
    with open(file, "rb") as f:
        base64_pdf = pybase64.b64encode(f.read()).decode('utf-8')

    # Embedding PDF in HTML
    pdf_display = F'<embed src="data:application/pdf;base64,{base64_pdf}" width="700" height="1000" type="application/pdf">'

    # Displaying File
    st.markdown(pdf_display, unsafe_allow_html=True)



displayPDF(st.query_params["pdffile"])