import streamlit as st
import os
from streamlit_extras.stylable_container import stylable_container
from appsupport import FileFunctions


#configure streamlit for the ap
st.set_page_config(page_title="CATrina", page_icon = "👩‍🔧")

st.title("CATrina")


logo_column, what_am_I_column, save_conv  = st.columns([1, 8,1])

#with logo_column:
   # image = Image.open(os.path.join(path,'CRIStine.png'))
    #st.image(image, caption='Logo goes here')
    
with what_am_I_column:
    st.markdown(f"*CATrina is a proprosal generation assistant that uses the chatgpt4-o Large Language Model to analyze an RFP/RFI document and  auto-generate elements of an offer*")

           


    


    





    




