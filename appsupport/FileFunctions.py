# Application Functions
# File Loader
import streamlit as st
import os
import streamlit.components.v1 as components

@st.dialog("Upload a File")
def upload_file(path):
    uploaded_file = st.file_uploader("Choose a file")
    if uploaded_file is not None:
        file_details = {"FileName":uploaded_file.name,"FileType":uploaded_file.type}
        st.write(file_details)
        with open(os.path.join(path,uploaded_file.name),"wb") as f: 
           f.write(uploaded_file.getbuffer())         
           st.success("Saved File")

# File Delete
@st.dialog("Delete a File")
def delete_file(path):
    # List all files in directory and subdirectories as buttons
    for root, dirs, file_names in os.walk(path):
        for file_name in file_names:
            if st.button(file_name):
                os.remove(os.path.join(path,file_name))
                st.success("Removed File")
                st.rerun()
       
# File View
@st.dialog("Files used by AI")
def view_file(path):
    # List all files in directory and subdirectories
    files = []
    for root, dirs, file_names in os.walk(path):
        for file_name in file_names:
            files.append(file_name)
    st.write(files)
    if st.button("Close"):
       st.rerun()

# File Save function


def save_conv(conv):
    js = (
        """
    <button type="button" id="picker">Download</button>
    <script>
    async function run() {
        console.log("Running")
    const handle = await showSaveFilePicker({
      suggestedName: 'CRIStine_Conv.txt',
      types: [{
          description: 'Text Data',
          accept: {'text/plain': ['.txt']},
      }],
  });
"""
    + f"const blob = new Blob([`{conv}`]);"
    + """
    const writableStream = await handle.createWritable();
    await writableStream.write(blob);
    await writableStream.close();
    }
    document.getElementById("picker").onclick = run
    console.log("Done")
    </script>

    """
    )

    components.html(js, height=30)



